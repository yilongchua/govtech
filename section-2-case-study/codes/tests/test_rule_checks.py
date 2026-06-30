from pathlib import Path

from backend.app.schemas.exam import FirstPageCheck
from backend.app.src.comparison.rule_checks import run_history_paper_rules
from backend.app.src.extraction.exam_extractor import extract_history_exam
from backend.app.src.ingestion.pdf_to_markdown import convert_pdf_to_markdown


def test_rule_checks_pass_for_specimen_paper(tmp_path) -> None:
    pdf = Path("data/raw/exam_pdfs/2174_specimen_paper_1.pdf")
    md = tmp_path / "paper.md"
    convert_pdf_to_markdown(pdf, md)
    exam = extract_history_exam(
        md,
        pdf,
        FirstPageCheck(is_exam_paper=True, subject="History", paper_code="2174/01", paper_title="History", exam_year=2024),
    )
    checks, issues = run_history_paper_rules(exam)
    assert all(check.passed for check in checks)
    assert issues == []


def test_rule_checks_pass_for_specimen_paper_2(tmp_path) -> None:
    pdf = Path("data/raw/exam_pdfs/2174_specimen_paper_2.pdf")
    md = tmp_path / "paper_2.md"
    convert_pdf_to_markdown(pdf, md)
    exam = extract_history_exam(
        md,
        pdf,
        FirstPageCheck(is_exam_paper=True, subject="History", paper_code="2174/01", paper_title="Mock Paper 1", exam_year=2024),
    )
    checks, issues = run_history_paper_rules(exam)
    assert all(check.passed for check in checks)
    assert issues == []
