from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.app.schemas.base import ValidationIssue
from backend.app.schemas.exam import ExamPaper, ImageSourceInterpretation, SourceItem
from backend.app.src.ingestion.model_client import LLMClient
from backend.app.src.ingestion.page_renderer import render_page
from backend.app.src.prompts import render_prompt


IMAGE_SOURCE_NO_TEXT = "IMAGE_SOURCE_NO_TEXT"
IMAGE_SOURCE_NO_TEXT_MESSAGE = "{source_id} is an image/cartoon without transcribed text. Vision interpretation may be required."


def interpret_image_only_sources(
    exam: ExamPaper,
    pdf_path: Path,
    output_dir: Path,
    model_client: LLMClient,
) -> dict[str, Any]:
    artifact: dict[str, Any] = {"strategy": "vision_image_source_interpretation", "sources": []}
    for source in exam.sources:
        if not _needs_vision(source):
            continue
        source_artifact = _interpret_source(source, pdf_path, output_dir, model_client)
        artifact["sources"].append(source_artifact)
        if source_artifact["status"] == "interpreted":
            continue
        display_source_id = _display_source_id(source.source_id)
        exam.issues.append(
            ValidationIssue(
                code=IMAGE_SOURCE_NO_TEXT,
                severity="WARNING",
                stage="exam_extraction",
                message=IMAGE_SOURCE_NO_TEXT_MESSAGE.format(source_id=display_source_id),
                reason=source_artifact.get("reason"),
                evidence={
                    "source_id": display_source_id,
                    "raw_source_id": source.source_id,
                    "source_type": source.source_type,
                    "page_number": source.page_number,
                    "image_path": source.image_path,
                },
            )
        )
    return artifact


def _interpret_source(source: SourceItem, pdf_path: Path, output_dir: Path, model_client: LLMClient) -> dict[str, Any]:
    if source.page_number is None:
        return {"source_id": source.source_id, "status": "warning", "reason": "Source page number is missing."}
    try:
        image_path = render_page(pdf_path, source.page_number, output_dir)
        source.image_path = str(image_path)
        prompt = render_prompt(
            "interpret_image_source.j2",
            ImageSourceInterpretation,
            source_id=source.source_id,
            source_type=source.source_type,
            page_number=source.page_number,
            attribution=source.attribution or "",
        )
        raw = model_client.complete_image_json(image_path, prompt)
        raw.pop("_raw_response", None)
        if _looks_like_json_schema(raw):
            raise ValueError("Vision model returned the output schema instead of an image-source interpretation.")
        raw.setdefault("source_id", source.source_id)
        raw.setdefault("source_type", source.source_type)
        try:
            interpretation = ImageSourceInterpretation(**raw)
        except ValidationError as exc:
            missing_fields = [
                ".".join(str(part) for part in error["loc"])
                for error in exc.errors()
                if error.get("type") == "missing"
            ]
            if missing_fields:
                raise ValueError(f"Vision model response was missing required field(s): {', '.join(missing_fields)}.") from exc
            raise
        if not interpretation.text.strip():
            raise ValueError("Vision model did not return interpreted source text.")
        source.text = interpretation.text.strip()
        return {
            "source_id": source.source_id,
            "status": "interpreted",
            "image_path": str(image_path),
            "prompt": prompt,
            "raw_response": model_client.last_raw_response,
            "interpretation": interpretation.model_dump(mode="json"),
        }
    except Exception as exc:
        return {
            "source_id": source.source_id,
            "status": "warning",
            "image_path": source.image_path,
            "raw_response": model_client.last_raw_response,
            "reason": str(exc),
        }


def _needs_vision(source: SourceItem) -> bool:
    source_type = source.source_type.lower()
    return any(token in source_type for token in ("cartoon", "image", "photo", "photograph", "illustration"))


def _display_source_id(source_id: str) -> str:
    stripped = source_id.strip()
    if stripped.lower().startswith("source "):
        return stripped
    return f"Source {stripped}"


def _looks_like_json_schema(raw: dict[str, Any]) -> bool:
    return "properties" in raw and ("type" in raw or "required" in raw or "title" in raw)
