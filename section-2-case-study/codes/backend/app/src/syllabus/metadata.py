from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader


def infer_year_from_filename(path: Path, default: int = 2026) -> int:
    match = re.search(r"y(\d{2})", path.name)
    return 2000 + int(match.group(1)) if match else default


def infer_subject_code(path: Path, default: str = "unknown") -> str:
    match = re.search(r"(^|[_-])(\d{4})([_-])", path.name)
    return match.group(2) if match else default


def infer_subject_from_pdf(path: Path) -> str | None:
    try:
        page_text = PdfReader(str(path)).pages[0].extract_text() or ""
    except Exception:
        return None
    lines = [" ".join(line.split()) for line in page_text.splitlines()]
    for line in lines[:24]:
        if not line or line.isdigit() or len(line) < 4:
            continue
        if "syllabus" in line.casefold() or "singapore-cambridge" in line.casefold():
            continue
        return line[:120]
    return None
