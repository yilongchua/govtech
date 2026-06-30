from pathlib import Path
from typing import Any

from backend.app.schemas.exam import ExamPaper, SourceItem
from backend.app.src.extraction.image_source_interpreter import interpret_image_only_sources
from backend.app.src.ingestion.model_client import LocalModelClient


def _exam_with_image_source() -> ExamPaper:
    return ExamPaper(
        subject="History",
        paper_code="2174/01",
        paper_title="History",
        total_marks=50,
        raw_pdf_path="data/raw/exam_pdfs/2174_specimen_paper_1.pdf",
        markdown_path="paper.md",
        sources=[
            SourceItem(
                source_id="E",
                source_type="cartoon",
                attribution="A cartoon published in a British newspaper.",
                page_number=4,
            )
        ],
        questions=[],
    )


class _VisionClient(LocalModelClient):
    def complete_image_json(self, image_path: Path, prompt: str) -> dict[str, Any]:
        self.last_prompt = prompt
        self.last_raw_response = {"content": "mock vision"}
        return {
            "source_id": "E",
            "source_type": "cartoon",
            "text": "The cartoon criticises appeasement by showing Hitler benefiting from delayed resistance.",
            "confidence": "medium",
            "visible_text": [],
            "reasoning": ["The source is presented as a political cartoon."],
        }


class _SchemaEchoVisionClient(LocalModelClient):
    def complete_image_json(self, image_path: Path, prompt: str) -> dict[str, Any]:
        self.last_prompt = prompt
        self.last_raw_response = {"content": "schema echo"}
        return {
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "type": "object",
        }


def test_interprets_image_only_source_with_vision_model(tmp_path) -> None:
    exam = _exam_with_image_source()
    client = _VisionClient(provider="mock", base_url="http://localhost:1234/v1", model="vision")

    artifact = interpret_image_only_sources(
        exam,
        Path("data/raw/exam_pdfs/2174_specimen_paper_1.pdf"),
        tmp_path,
        client,
    )

    assert artifact["sources"][0]["status"] == "interpreted"
    assert exam.sources[0].text.startswith("The cartoon criticises appeasement")
    assert exam.sources[0].image_path
    assert exam.issues == []


def test_warns_when_image_only_source_cannot_be_interpreted(tmp_path) -> None:
    exam = _exam_with_image_source()
    client = LocalModelClient(provider="mock", base_url="http://localhost:1234/v1", model="mock")

    artifact = interpret_image_only_sources(
        exam,
        Path("data/raw/exam_pdfs/2174_specimen_paper_1.pdf"),
        tmp_path,
        client,
    )

    assert artifact["sources"][0]["status"] == "warning"
    assert exam.issues[0].code == "IMAGE_SOURCE_NO_TEXT"
    assert exam.issues[0].severity == "WARNING"
    assert exam.issues[0].message == "Source E is an image/cartoon without transcribed text. Vision interpretation may be required."


def test_warning_does_not_duplicate_source_prefix(tmp_path) -> None:
    exam = _exam_with_image_source()
    exam.sources[0].source_id = "Source E"
    client = LocalModelClient(provider="mock", base_url="http://localhost:1234/v1", model="mock")

    interpret_image_only_sources(
        exam,
        Path("data/raw/exam_pdfs/2174_specimen_paper_1.pdf"),
        tmp_path,
        client,
    )

    assert exam.issues[0].message == "Source E is an image/cartoon without transcribed text. Vision interpretation may be required."


def test_schema_echo_response_gets_readable_warning_reason(tmp_path) -> None:
    exam = _exam_with_image_source()
    client = _SchemaEchoVisionClient(provider="mock", base_url="http://localhost:1234/v1", model="vision")

    interpret_image_only_sources(
        exam,
        Path("data/raw/exam_pdfs/2174_specimen_paper_1.pdf"),
        tmp_path,
        client,
    )

    assert exam.issues[0].reason == "Vision model returned the output schema instead of an image-source interpretation."
