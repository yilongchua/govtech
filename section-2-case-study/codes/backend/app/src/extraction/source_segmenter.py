from __future__ import annotations

from backend.app.schemas.exam import SourceItem
from backend.app.src.extraction.exam_extractor import _extract_sources


def segment_sources(markdown_text: str) -> list[SourceItem]:
    return _extract_sources(markdown_text)

