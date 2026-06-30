from pathlib import Path

from backend.app.schemas.exam import FirstPageCheck
from backend.app.schemas.syllabus import AssessmentComponent, AssessmentObjective, SyllabusDocument, SyllabusTopic
from backend.app.src.extraction.exam_extractor import extract_history_exam
from backend.app.src.extraction.llm_exam_extractor import extract_history_exam_with_llm
from backend.app.src.ingestion.model_client import LocalModelClient
from backend.app.src.ingestion.pdf_to_markdown import convert_pdf_to_markdown


def _first_page() -> FirstPageCheck:
    return FirstPageCheck(
        is_exam_paper=True,
        subject="History",
        paper_code="2174/01",
        paper_title="History",
        exam_year=2024,
    )


def _syllabus():
    return SyllabusDocument(
        subject="History",
        subject_code="2174",
        year=2026,
        source_url="https://example.test/syllabus.pdf",
        pdf_path="2174_y26_sy.pdf",
        markdown_path="2174_y26_sy.md",
        objectives=[
            AssessmentObjective(ao_id="AO1", name="Deploy Knowledge", description="Use historical knowledge.", skills=[]),
            AssessmentObjective(ao_id="AO2", name="Construct Explanation", description="Explain historical events.", skills=[]),
            AssessmentObjective(ao_id="AO3", name="Evaluate Sources", description="Evaluate source materials.", skills=[]),
        ],
        components=[
            AssessmentComponent(paper="2174/01", section="A", name="Source-Based Case Study", marks=30, objectives=["AO1", "AO3"], rules=[]),
            AssessmentComponent(paper="2174/01", section="B", name="Essay Questions", marks=20, objectives=["AO1", "AO2"], rules=[]),
        ],
        topics=[
            SyllabusTopic(topic_id="p1_wwii_europe", paper="2174/01", unit="War in Europe", topic="Key developments leading to World War II in Europe"),
        ],
    )


def _mock_client(response):
    return LocalModelClient(
        provider="mock",
        base_url="http://localhost:1234/v1",
        model="qwen/qwen3.6-35b-a3b",
        mock_json_response=response,
    )


def test_llm_exam_extractor_accepts_valid_mock_output(tmp_path) -> None:
    pdf = Path("data/raw/exam_pdfs/2174_specimen_paper_1.pdf")
    md = tmp_path / "paper.md"
    convert_pdf_to_markdown(pdf, md)
    expected = extract_history_exam(md, pdf, _first_page())

    exam, artifact = extract_history_exam_with_llm(
        md,
        pdf,
        _first_page(),
        _syllabus(),
        _mock_client(expected.model_dump(mode="json")),
    )

    assert artifact["fallback_used"] is False
    assert exam.total_marks == 50
    assert len(exam.questions) == 9
    assert not any(issue.code == "llm_exam_extraction_fallback" for issue in exam.issues)


def test_llm_exam_extractor_falls_back_on_invalid_json(tmp_path) -> None:
    pdf = Path("data/raw/exam_pdfs/2174_specimen_paper_1.pdf")
    md = tmp_path / "paper.md"
    convert_pdf_to_markdown(pdf, md)

    exam, artifact = extract_history_exam_with_llm(
        md,
        pdf,
        _first_page(),
        _syllabus(),
        _mock_client("not json"),
    )

    assert artifact["fallback_used"] is True
    assert exam.total_marks == 50
    assert any(issue.code == "llm_exam_extraction_fallback" for issue in exam.issues)


def test_llm_exam_extractor_reports_empty_model_response(tmp_path) -> None:
    pdf = Path("data/raw/exam_pdfs/2174_specimen_paper_1.pdf")
    md = tmp_path / "paper.md"
    convert_pdf_to_markdown(pdf, md)

    exam, artifact = extract_history_exam_with_llm(
        md,
        pdf,
        _first_page(),
        _syllabus(),
        _mock_client(""),
    )

    assert artifact["fallback_used"] is True
    assert artifact["fallback_reason"] == "Model response was empty."
    assert exam.total_marks == 50
    assert any(issue.reason == "Model response was empty." for issue in exam.issues)


def test_llm_exam_extractor_falls_back_on_incomplete_output(tmp_path) -> None:
    pdf = Path("data/raw/exam_pdfs/2174_specimen_paper_1.pdf")
    md = tmp_path / "paper.md"
    convert_pdf_to_markdown(pdf, md)

    exam, artifact = extract_history_exam_with_llm(
        md,
        pdf,
        _first_page(),
        _syllabus(),
        _mock_client({"subject": "History", "paper_code": "2174/01"}),
    )

    assert artifact["fallback_used"] is True
    assert exam.total_marks == 50
    assert any(issue.code == "llm_exam_extraction_fallback" for issue in exam.issues)
