from pathlib import Path

from backend.app.src.graph.workflow import run_analysis


def test_history_specimen_workflow_mock_model() -> None:
    pdf = Path("data/raw/exam_pdfs/2174_specimen_paper_1.pdf")
    if not pdf.exists():
        return
    report = run_analysis(pdf, "pytest_smoke", provider="mock")
    assert report["exam_paper"]["subject"] == "History"
    assert report["exam_paper"]["total_marks"] == 50
    assert len(report["exam_paper"]["questions"]) >= 5
    assert report["annotations"][0]["predicted_objectives"] == ["AO1", "AO3"]
    assert report["annotations"][0]["predicted_topic"] == "Key developments leading to the outbreak of World War II in Europe"
    assert any(
        item["topic"] == "Key developments leading to the outbreak of World War II in Europe"
        and item["required_marks"] == 30
        for item in report["topic_weightage"]
    )


def test_history_specimen_paper_2_workflow_mock_model() -> None:
    pdf = Path("data/raw/exam_pdfs/2174_specimen_paper_2.pdf")
    if not pdf.exists():
        return
    report = run_analysis(pdf, "pytest_smoke_paper_2", provider="mock")
    assert report["exam_paper"]["paper_code"] == "2174/02"
    assert report["exam_paper"]["total_marks"] == 50
    assert len(report["exam_paper"]["questions"]) == 8
    assert [issue["code"] for issue in report["issues"]] == ["IMAGE_SOURCE_NO_TEXT"]
    assert report["annotations"][0]["predicted_objectives"] == ["AO1", "AO3"]
    assert any(
        item["topic"] == "Why did the Communist insurgency in Malaya fail?"
        and item["required_marks"] == 30
        for item in report["topic_weightage"]
    )
