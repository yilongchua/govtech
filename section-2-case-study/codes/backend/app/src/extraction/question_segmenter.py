from __future__ import annotations

from backend.app.schemas.exam import ExamQuestion
from backend.app.src.extraction.exam_extractor import _extract_questions


def segment_questions(markdown_text: str) -> list[ExamQuestion]:
    return _extract_questions(markdown_text)

