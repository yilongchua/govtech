from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from backend.app.schemas.base import ValidationIssue
from backend.app.schemas.syllabus import AssessmentComponent, AssessmentObjective, SyllabusDocument, SyllabusTopic
from backend.app.src.ingestion.model_client import LLMClient
from backend.app.src.prompts import render_prompt
from backend.app.src.syllabus.metadata import infer_subject_code, infer_subject_from_pdf, infer_year_from_filename


class SyllabusExtractionError(ValueError):
    pass


class SyllabusMetadata(BaseModel):
    subject: str | None = None
    subject_code: str | None = None
    year: int | None = None
    issues: list[ValidationIssue] = []


class SyllabusObjectivesResult(BaseModel):
    objectives: list[AssessmentObjective] = []
    issues: list[ValidationIssue] = []


class SyllabusComponentsResult(BaseModel):
    components: list[AssessmentComponent] = []
    issues: list[ValidationIssue] = []


class SyllabusTopicsResult(BaseModel):
    topics: list[SyllabusTopic] = []
    issues: list[ValidationIssue] = []


def extract_syllabus_metadata(markdown: str, client: LLMClient) -> tuple[SyllabusMetadata, dict[str, Any]]:
    return _complete_partial(
        "metadata",
        "extract_syllabus_metadata.j2",
        SyllabusMetadata,
        _targeted_markdown(markdown, ["syllabus", "subject", "code", "examination", "ordinary level"]),
        client,
    )


def extract_syllabus_objectives(markdown: str, client: LLMClient) -> tuple[SyllabusObjectivesResult, dict[str, Any]]:
    return _complete_partial(
        "objectives",
        "extract_syllabus_objectives_only.j2",
        SyllabusObjectivesResult,
        _targeted_markdown(markdown, ["assessment objectives", "objectives", "learning outcomes", "aims"]),
        client,
    )


def extract_syllabus_components(markdown: str, client: LLMClient) -> tuple[SyllabusComponentsResult, dict[str, Any]]:
    return _complete_partial(
        "components",
        "extract_syllabus_components_only.j2",
        SyllabusComponentsResult,
        _targeted_markdown(markdown, ["assessment", "paper", "component", "marks", "weighting", "section"]),
        client,
    )


def extract_syllabus_topics(markdown: str, client: LLMClient) -> tuple[SyllabusTopicsResult, dict[str, Any]]:
    return _complete_partial(
        "topics",
        "extract_syllabus_topics_only.j2",
        SyllabusTopicsResult,
        _targeted_markdown(markdown, ["content", "topic", "theme", "syllabus content", "conversation", "section"]),
        client,
    )


def extract_syllabus_with_llm(
    markdown_path: Path,
    pdf_path: Path,
    source_url: str,
    client: LLMClient,
    *,
    label: str | None = None,
    year: int | None = None,
) -> tuple[SyllabusDocument, dict[str, Any]]:
    markdown = markdown_path.read_text(encoding="utf-8")
    try:
        metadata, metadata_artifact = extract_syllabus_metadata(markdown, client)
        objectives, objectives_artifact = extract_syllabus_objectives(markdown, client)
        components, components_artifact = extract_syllabus_components(markdown, client)
        topics, topics_artifact = extract_syllabus_topics(markdown, client)
    except Exception as exc:
        if isinstance(exc, SyllabusExtractionError):
            raise
        raise SyllabusExtractionError(str(exc)) from exc

    payload = {
        "subject": metadata.subject or label or infer_subject_from_pdf(pdf_path) or f"Syllabus {infer_subject_code(pdf_path)}",
        "subject_code": str(metadata.subject_code or infer_subject_code(pdf_path)),
        "year": int(metadata.year or year or infer_year_from_filename(pdf_path)),
        "source_url": source_url,
        "pdf_path": str(pdf_path),
        "markdown_path": str(markdown_path),
        "objectives": objectives.objectives,
        "components": components.components,
        "topics": topics.topics,
        "issues": [
            *metadata.issues,
            *objectives.issues,
            *components.issues,
            *topics.issues,
        ],
    }
    try:
        syllabus = SyllabusDocument(**payload)
    except ValidationError as exc:
        raise SyllabusExtractionError(str(exc)) from exc

    missing = _missing_required_sections(syllabus)
    if missing:
        raise SyllabusExtractionError(
            "LLM syllabus extraction did not produce complete objectives, components, and topics: "
            + ", ".join(missing)
        )

    artifact = {
        "source_url": source_url,
        "pdf_path": str(pdf_path),
        "markdown_path": str(markdown_path),
        "provider": client.provider,
        "base_url": client.base_url,
        "model": client.model,
        "calls": [metadata_artifact, objectives_artifact, components_artifact, topics_artifact],
        "parsed_json": syllabus.model_dump(mode="json"),
        "issues": [issue.model_dump(mode="json") for issue in syllabus.issues],
    }
    return syllabus, artifact


def build_syllabus_document(
    *,
    markdown_path: Path,
    pdf_path: Path,
    source_url: str,
    metadata: SyllabusMetadata,
    objectives: SyllabusObjectivesResult,
    components: SyllabusComponentsResult,
    topics: SyllabusTopicsResult,
    label: str | None = None,
    year: int | None = None,
) -> SyllabusDocument:
    syllabus = SyllabusDocument(
        subject=metadata.subject or label or infer_subject_from_pdf(pdf_path) or f"Syllabus {infer_subject_code(pdf_path)}",
        subject_code=str(metadata.subject_code or infer_subject_code(pdf_path)),
        year=int(metadata.year or year or infer_year_from_filename(pdf_path)),
        source_url=source_url,
        pdf_path=str(pdf_path),
        markdown_path=str(markdown_path),
        objectives=objectives.objectives,
        components=components.components,
        topics=topics.topics,
        issues=[*metadata.issues, *objectives.issues, *components.issues, *topics.issues],
    )
    missing = _missing_required_sections(syllabus)
    if missing:
        raise SyllabusExtractionError(
            "LLM syllabus extraction did not produce complete objectives, components, and topics: "
            + ", ".join(missing)
        )
    return syllabus


def _complete_partial(
    call_name: str,
    template_name: str,
    output_model: type[BaseModel],
    markdown: str,
    client: LLMClient,
) -> tuple[Any, dict[str, Any]]:
    prompt = render_prompt(template_name, output_model, syllabus_markdown=markdown)
    try:
        raw = client.complete_json(prompt)
    except Exception as exc:
        raise SyllabusExtractionError(f"{call_name} extraction failed: {exc}") from exc

    raw_response = raw.pop("_raw_response", None)
    try:
        parsed = output_model(**raw)
    except ValidationError as exc:
        raise SyllabusExtractionError(f"{call_name} extraction returned invalid JSON: {exc}") from exc

    artifact = {
        "call": call_name,
        "template": template_name,
        "prompt": prompt,
        "raw_response": raw_response if raw_response is not None else client.last_raw_response,
        "reasoning_content": client.last_reasoning_content,
        "parsed_json": parsed.model_dump(mode="json"),
    }
    return parsed, artifact


def _targeted_markdown(markdown: str, keywords: list[str]) -> str:
    pages = _split_markdown_pages(markdown)
    selected = []
    lowered_keywords = [keyword.casefold() for keyword in keywords]
    for heading, body in pages:
        text = f"{heading}\n{body}"
        folded = text.casefold()
        if any(keyword in folded for keyword in lowered_keywords):
            selected.append(text)
    if not selected:
        return markdown
    header = markdown.split("## Page", 1)[0].strip()
    return "\n\n".join([header, *selected]).strip() + "\n"


def _split_markdown_pages(markdown: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^## Page \d+.*$", markdown, flags=re.M))
    if not matches:
        return [("", markdown)]
    pages = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        pages.append((match.group(0), markdown[start:end].strip()))
    return pages


def _missing_required_sections(syllabus: SyllabusDocument) -> list[str]:
    missing = []
    if not syllabus.objectives:
        missing.append("objectives")
    if not syllabus.components:
        missing.append("components")
    if not syllabus.topics:
        missing.append("topics")
    return missing
