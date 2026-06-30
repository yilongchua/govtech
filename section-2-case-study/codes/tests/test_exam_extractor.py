from pathlib import Path

from backend.app.schemas.exam import FirstPageCheck
from backend.app.src.extraction.exam_extractor import extract_history_exam
from backend.app.src.ingestion.pdf_to_markdown import convert_pdf_to_markdown


def test_exam_extractor_finds_history_questions(tmp_path) -> None:
    pdf = Path("data/raw/exam_pdfs/2174_specimen_paper_1.pdf")
    md = tmp_path / "paper.md"
    convert_pdf_to_markdown(pdf, md)
    exam = extract_history_exam(
        md,
        pdf,
        FirstPageCheck(is_exam_paper=True, subject="History", paper_code="2174/01", paper_title="History", exam_year=2024),
    )
    assert exam.total_marks == 50
    assert len(exam.questions) == 9


def test_exam_extractor_finds_paper_2_multiline_questions(tmp_path) -> None:
    pdf = Path("data/raw/exam_pdfs/2174_specimen_paper_2.pdf")
    md = tmp_path / "paper_2.md"
    convert_pdf_to_markdown(pdf, md)
    exam = extract_history_exam(
        md,
        pdf,
        FirstPageCheck(is_exam_paper=True, subject="History", paper_code="2174/01", paper_title="Mock Paper 1", exam_year=2024),
    )
    assert exam.paper_code == "2174/02"
    assert exam.total_marks == 50
    assert len(exam.questions) == 8
    assert [q.question_id for q in exam.questions] == ["1(a)", "1(b)", "1(c)", "1(d)", "1(e)", "2", "3", "4"]
    assert len(exam.sources) == 6
