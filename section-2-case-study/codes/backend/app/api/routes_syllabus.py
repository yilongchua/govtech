from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterator, Optional

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, HttpUrl

from backend.app.core.config import get_model_settings, settings
from backend.app.core.storage import read_json, write_json
from backend.app.src.ingestion.model_client import LLMClient
from backend.app.src.ingestion.pdf_to_markdown import convert_pdf_to_markdown
from backend.app.src.syllabus.llm_syllabus_extractor import (
    SyllabusExtractionError,
    build_syllabus_document,
    extract_syllabus_components,
    extract_syllabus_metadata,
    extract_syllabus_objectives,
    extract_syllabus_topics,
)
from backend.app.src.syllabus.metadata import infer_year_from_filename
from backend.app.src.syllabus.seab_scraper import resolve_seab_syllabus_pdf
from backend.app.src.syllabus.syllabus_registry import write_syllabus_registry

router = APIRouter(prefix="/api", tags=["syllabus"])
SYLLABUS_INGEST_TOTAL_STEPS = 12


class SyllabusUrlIngestRequest(BaseModel):
    url: HttpUrl
    label: Optional[str] = None


@router.get("/syllabus/latest")
def latest_syllabus(subject_code: str = "2174") -> dict:
    entry = _syllabus_entry(subject_code)
    if entry is None:
        return _unconfigured_syllabus(subject_code)
    return {
        "subject": entry.get("subject"),
        "subject_code": entry.get("subject_code"),
        "year": entry.get("year"),
        "pdf_url": entry.get("pdf_url"),
        "route": f"configured_subject_{entry.get('subject_code')}_{entry.get('year')}",
        "configured": _is_configured_syllabus_entry(entry),
    }


@router.get("/subjects")
def subjects() -> dict:
    entries = _syllabus_entries()
    return {
        "subjects": [
            {
                "subject": entry.get("subject"),
                "subject_code": entry.get("subject_code"),
                "latest_year": entry.get("year"),
                "route": f"configured_subject_{entry.get('subject_code')}_{entry.get('year')}",
                "configured": _is_configured_syllabus_entry(entry),
            }
            for entry in entries
        ],
        "fallback_route": {"route": "unavailable", "configured": False, "behavior": "stop_processing"},
    }


@router.get("/syllabuses")
def list_syllabuses() -> dict:
    entries = _syllabus_entries()
    return {
        "syllabuses": [_public_syllabus_entry(entry) for entry in entries],
    }


@router.get("/syllabuses/{subject_code}")
def syllabus_detail(subject_code: str) -> dict:
    entry = _syllabus_entry(subject_code)
    if entry is None:
        raise HTTPException(status_code=404, detail="Syllabus not found.")
    json_path = _resolve_path(entry.get("json_path"))
    if json_path is None or not json_path.exists():
        raise HTTPException(status_code=404, detail="Syllabus JSON not found.")
    syllabus = read_json(json_path)
    markdown_path = _resolve_path(syllabus.get("markdown_path") or entry.get("markdown_path"))
    return {
        "entry": _public_syllabus_entry(entry),
        "syllabus": syllabus,
        "requirements": _requirement_rows(syllabus, markdown_path),
    }


@router.get("/syllabuses/{subject_code}/pdf")
def syllabus_pdf(subject_code: str) -> FileResponse:
    entry = _syllabus_entry(subject_code)
    if entry is None:
        raise HTTPException(status_code=404, detail="Syllabus not found.")
    json_path = _resolve_path(entry.get("json_path"))
    syllabus = read_json(json_path) if json_path and json_path.exists() else {}
    pdf_path = _resolve_path(syllabus.get("pdf_path") or entry.get("pdf_path"))
    if pdf_path is None or not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Syllabus PDF not found.")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
        content_disposition_type="inline",
    )


@router.delete("/syllabuses/{subject_code}")
def delete_syllabus(subject_code: str) -> dict:
    entries = _syllabus_entries()
    entry = next((item for item in entries if str(item.get("subject_code")) == str(subject_code)), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="Syllabus not found.")

    deleted_paths = []
    json_path = _resolve_path(entry.get("json_path"))
    syllabus = read_json(json_path) if json_path and json_path.exists() else {}
    candidate_paths = [
        json_path,
        _resolve_path(syllabus.get("markdown_path") or entry.get("markdown_path")),
        _resolve_path(syllabus.get("pdf_path") or entry.get("pdf_path")),
    ]
    for path in candidate_paths:
        if path and _is_safe_generated_path(path) and path.exists():
            path.unlink()
            deleted_paths.append(str(path))

    remaining_entries = [item for item in entries if str(item.get("subject_code")) != str(subject_code)]
    _write_syllabus_registry_entries(remaining_entries)
    return {"ok": True, "subject_code": subject_code, "deleted_paths": deleted_paths}


@router.post("/syllabuses/ingest-url")
def ingest_syllabus_url(payload: SyllabusUrlIngestRequest) -> dict:
    result = None
    for event in _ingest_syllabus_events(payload):
        if event.get("status") == "complete":
            result = event.get("result")
    if result is None:
        raise HTTPException(status_code=500, detail="Syllabus ingestion did not produce a result.")
    return result


@router.post("/syllabuses/ingest-url/events")
def ingest_syllabus_url_events(payload: SyllabusUrlIngestRequest) -> StreamingResponse:
    def stream() -> Iterator[str]:
        try:
            for event in _ingest_syllabus_events(payload):
                yield _sse(event)
        except HTTPException as exc:
            yield _sse(
                {
                    "status": "failed",
                    "stage": "failed",
                    "progress": 100,
                    "step": SYLLABUS_INGEST_TOTAL_STEPS,
                    "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
                    "message": str(exc.detail),
                    "error": exc.detail,
                }
            )
        except Exception as exc:
            yield _sse(
                {
                    "status": "failed",
                    "stage": "failed",
                    "progress": 100,
                    "step": SYLLABUS_INGEST_TOTAL_STEPS,
                    "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
                    "message": str(exc),
                    "error": str(exc),
                }
            )

    return StreamingResponse(stream(), media_type="text/event-stream")


def _ingest_syllabus_events(payload: SyllabusUrlIngestRequest) -> Iterator[dict]:
    source_url = str(payload.url)
    yield {
        "status": "running",
        "stage": "resolve_link",
        "progress": 5,
        "step": 1,
        "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
        "message": "Resolving SEAB page/text fragment or direct PDF link.",
        "detail": source_url,
    }
    try:
        pdf_url, anchor_label, page_url = resolve_seab_syllabus_pdf(source_url)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    yield {
        "status": "running",
        "stage": "download_pdf",
        "progress": 15,
        "step": 2,
        "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
        "message": "Downloading syllabus PDF.",
        "detail": pdf_url,
    }
    try:
        response = httpx.get(pdf_url, timeout=60, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Could not download syllabus PDF: {exc}") from exc

    filename = _safe_pdf_filename(pdf_url)
    pdf_path = settings.data_dir / "raw" / "syllabus_pdfs" / filename
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(response.content)

    yield {
        "status": "running",
        "stage": "save_pdf",
        "progress": 30,
        "step": 3,
        "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
        "message": "Saved PDF to local syllabus storage.",
        "detail": str(pdf_path),
    }
    year = infer_year_from_filename(pdf_path, settings.history_syllabus_year)
    stem = pdf_path.stem.lower()
    md_path = settings.data_dir / "processed" / "markdown" / "syllabus" / f"{stem}.md"
    yield {
        "status": "running",
        "stage": "convert_markdown",
        "progress": 40,
        "step": 4,
        "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
        "message": "Converting PDF pages to Markdown for model extraction.",
        "detail": str(md_path),
    }
    convert_pdf_to_markdown(pdf_path, md_path)

    label = (payload.label or anchor_label or "").strip() or None
    configured_model = get_model_settings()
    client = LLMClient(
        provider=configured_model.provider,
        base_url=configured_model.base_url,
        model=configured_model.model,
        timeout=configured_model.timeout_seconds,
    )
    try:
        markdown = md_path.read_text(encoding="utf-8")
        llm_call = {
            "provider": configured_model.provider,
            "base_url": configured_model.base_url,
            "model": configured_model.model,
            "timeout_seconds": configured_model.timeout_seconds,
        }
        yield {
            "status": "running",
            "stage": "llm_metadata",
            "progress": 50,
            "step": 5,
            "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
            "message": "Calling local LLM to extract syllabus metadata.",
            "detail": f"{configured_model.provider} / {configured_model.model} at {configured_model.base_url}",
            "llm_call": {**llm_call, "goal": "Extract subject, subject code, and year."},
        }
        metadata, metadata_artifact = extract_syllabus_metadata(markdown, client)
        yield {
            "status": "running",
            "stage": "llm_objectives",
            "progress": 58,
            "step": 6,
            "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
            "message": "Calling local LLM to extract assessment objectives.",
            "detail": f"{configured_model.provider} / {configured_model.model} at {configured_model.base_url}",
            "llm_call": {**llm_call, "goal": "Extract assessment objectives only."},
        }
        objectives, objectives_artifact = extract_syllabus_objectives(markdown, client)
        yield {
            "status": "running",
            "stage": "llm_components",
            "progress": 66,
            "step": 7,
            "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
            "message": "Calling local LLM to extract assessment components and rules.",
            "detail": f"{configured_model.provider} / {configured_model.model} at {configured_model.base_url}",
            "llm_call": {**llm_call, "goal": "Extract papers, sections, marks, weighting, and assessment rules only."},
        }
        components, components_artifact = extract_syllabus_components(markdown, client)
        yield {
            "status": "running",
            "stage": "llm_topics",
            "progress": 74,
            "step": 8,
            "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
            "message": "Calling local LLM to extract examinable topics/content.",
            "detail": f"{configured_model.provider} / {configured_model.model} at {configured_model.base_url}",
            "llm_call": {**llm_call, "goal": "Extract examinable topics, themes, content areas, and subtopics only."},
        }
        topics, topics_artifact = extract_syllabus_topics(markdown, client)
        yield {
            "status": "running",
            "stage": "merge_extraction",
            "progress": 82,
            "step": 9,
            "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
            "message": "Merging chunked LLM outputs into one syllabus document.",
            "detail": "Combining metadata, objectives, components, topics, and issues.",
        }
        syllabus = build_syllabus_document(
            markdown_path=md_path,
            pdf_path=pdf_path,
            source_url=pdf_url,
            metadata=metadata,
            objectives=objectives,
            components=components,
            topics=topics,
            label=label,
            year=year,
        )
        extraction_artifact = {
            "source_url": pdf_url,
            "pdf_path": str(pdf_path),
            "markdown_path": str(md_path),
            "provider": configured_model.provider,
            "base_url": configured_model.base_url,
            "model": configured_model.model,
            "calls": [metadata_artifact, objectives_artifact, components_artifact, topics_artifact],
            "parsed_json": syllabus.model_dump(mode="json"),
            "issues": [issue.model_dump(mode="json") for issue in syllabus.issues],
        }
    except SyllabusExtractionError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"LLM syllabus extraction did not produce a complete syllabus: {exc}",
        ) from exc

    yield {
        "status": "running",
        "stage": "validate_extraction",
        "progress": 88,
        "step": 10,
        "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
        "message": "Validated LLM output against the syllabus schema and completeness gate.",
        "detail": f"{len(syllabus.objectives)} objectives, {len(syllabus.components)} components, {len(syllabus.topics)} topics",
    }
    json_path = settings.data_dir / "processed" / "json" / "syllabus" / f"{stem}.json"
    artifact_path = settings.data_dir / "processed" / "json" / "syllabus" / f"{stem}.extraction.json"
    yield {
        "status": "running",
        "stage": "persist_artifacts",
        "progress": 94,
        "step": 11,
        "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
        "message": "Saving syllabus JSON, extraction audit artifact, and registry entry.",
        "detail": str(json_path),
    }
    write_json(json_path, syllabus.model_dump(mode="json"))
    extraction_artifact["pdf_sha256"] = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    write_json(artifact_path, extraction_artifact)
    write_syllabus_registry(
        syllabus,
        extraction_artifact["pdf_sha256"],
        source_page_url=page_url,
        json_path=json_path,
    )
    result = {
        "ok": True,
        "subject": syllabus.subject,
        "subject_code": syllabus.subject_code,
        "year": syllabus.year,
        "pdf_url": pdf_url,
        "pdf_path": str(pdf_path),
        "markdown_path": str(md_path),
        "json_path": str(json_path),
        "extraction_artifact_path": str(artifact_path),
        "source_page_url": page_url,
        "issues": [issue.model_dump(mode="json") for issue in syllabus.issues],
    }
    yield {
        "status": "complete",
        "stage": "complete",
        "progress": 100,
        "step": 12,
        "total_steps": SYLLABUS_INGEST_TOTAL_STEPS,
        "message": "Syllabus ingestion complete.",
        "detail": f"{syllabus.subject} ({syllabus.subject_code})",
        "result": result,
    }


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


def _safe_pdf_filename(pdf_url: str) -> str:
    candidate = pdf_url.rstrip("/").rsplit("/", 1)[-1].split("?", 1)[0] or "syllabus.pdf"
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate)
    if not candidate.lower().endswith(".pdf"):
        candidate = f"{candidate}.pdf"
    return candidate.lower()


def _syllabus_entries() -> list[dict]:
    index_path = settings.data_dir / "reference" / "syllabus_index.json"
    if not index_path.exists():
        return []
    return read_json(index_path).get("syllabuses", [])


def _write_syllabus_registry_entries(entries: list[dict]) -> None:
    latest = entries[-1] if entries else None
    payload = {"latest": latest, "syllabuses": entries} if latest else {"syllabuses": []}
    write_json(settings.data_dir / "reference" / "syllabus_index.json", payload)

    subjects = []
    for entry in entries:
        subject = {"subject": entry.get("subject"), "subject_code": entry.get("subject_code"), "latest_year": entry.get("year")}
        existing = next((item for item in subjects if item["subject_code"] == subject["subject_code"]), None)
        if existing is None:
            subjects.append(subject)
        elif subject["latest_year"] >= existing["latest_year"]:
            existing.update(subject)
    write_json(settings.data_dir / "reference" / "subject_registry.json", {"subjects": subjects})


def _syllabus_entry(subject_code: str) -> Optional[dict]:
    for entry in _syllabus_entries():
        if str(entry.get("subject_code")) == str(subject_code):
            return entry
    return None


def _is_configured_syllabus_entry(entry: dict) -> bool:
    json_path = entry.get("json_path")
    if not json_path:
        return False
    path = Path(str(json_path))
    if not path.is_absolute():
        path = settings.root_dir / path
    if not path.exists():
        return False
    syllabus = read_json(path)
    return bool(syllabus.get("objectives") and syllabus.get("components") and syllabus.get("topics"))


def _public_syllabus_entry(entry: dict) -> dict:
    return {
        "subject": entry.get("subject"),
        "subject_code": entry.get("subject_code"),
        "year": entry.get("year"),
        "source_page_url": entry.get("source_page_url"),
        "pdf_url": entry.get("pdf_url"),
        "pdf_url_local": f"/api/syllabuses/{entry.get('subject_code')}/pdf",
        "json_path": entry.get("json_path"),
        "markdown_path": entry.get("markdown_path"),
        "configured": _is_configured_syllabus_entry(entry),
    }


def _requirement_rows(syllabus: dict, markdown_path: Optional[Path] = None) -> list[dict]:
    rows: list[dict] = []
    for objective in syllabus.get("objectives") or []:
        rows.append(
            {
                "type": "Assessment objective",
                "reference": objective.get("ao_id"),
                "requirement": objective.get("name"),
                "details": objective.get("description"),
                "page": objective.get("source_page"),
            }
        )
    for component in syllabus.get("components") or []:
        details = []
        if component.get("objectives"):
            details.append(f"Objectives: {', '.join(component.get('objectives') or [])}")
        if component.get("rules"):
            details.append(f"Rules: {'; '.join(component.get('rules') or [])}")
        rows.append(
            {
                "type": "Assessment component",
                "reference": " ".join(str(part) for part in [component.get("paper"), component.get("section")] if part),
                "requirement": component.get("name"),
                "details": "; ".join(details),
                "page": component.get("source_page"),
                "marks": component.get("marks"),
            }
        )
    for topic in syllabus.get("topics") or []:
        details = []
        if topic.get("subtopics"):
            details.append(f"Subtopics: {', '.join(topic.get('subtopics') or [])}")
        if topic.get("key_concepts"):
            details.append(f"Key concepts: {', '.join(topic.get('key_concepts') or [])}")
        rows.append(
            {
                "type": "Topic/content",
                "reference": topic.get("paper") or topic.get("topic_id"),
                "requirement": topic.get("topic"),
                "details": "; ".join(details) or topic.get("unit"),
                "page": topic.get("source_page"),
            }
        )
    return rows


def _resolve_path(value: object) -> Optional[Path]:
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        path = settings.root_dir / path
    return path


def _is_safe_generated_path(path: Path) -> bool:
    try:
        path.resolve().relative_to(settings.data_dir.resolve())
    except ValueError:
        return False
    return path.is_file()


def _unconfigured_syllabus(subject_code: str) -> dict:
    return {
        "subject": "Unconfigured",
        "subject_code": subject_code,
        "year": settings.history_syllabus_year,
        "pdf_url": None,
        "route": "unavailable",
        "configured": False,
    }
