from pathlib import Path

from backend.app.src.ingestion.pdf_guard import validate_pdf_file


def test_pdf_guard_accepts_specimen_pdf() -> None:
    issues = validate_pdf_file(Path("data/raw/exam_pdfs/2174_specimen_paper_1.pdf"))
    assert issues == []

