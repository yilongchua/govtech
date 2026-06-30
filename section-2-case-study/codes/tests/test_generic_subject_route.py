from pathlib import Path

from backend.app.core.storage import write_json
from backend.app.schemas.exam import FirstPageCheck
from backend.app.src.subjects import GenericSubjectRoute, RouteConfig, resolve_subject_route_with_status
from backend.app.src.ingestion.model_client import LocalModelClient


def test_resolve_subject_route_stops_for_unconfigured_subject() -> None:
    resolution = resolve_subject_route_with_status(
        FirstPageCheck(
            is_exam_paper=True,
            subject="Mathematics",
            paper_code="4048/01",
            paper_title="Paper 1",
            exam_year=2026,
        )
    )

    assert resolution.status == "unsupported"
    assert resolution.route is None


def test_resolve_subject_route_uses_configured_generic_route_for_history() -> None:
    resolution = resolve_subject_route_with_status(
        FirstPageCheck(
            is_exam_paper=True,
            subject="History",
            paper_code="2174/01",
            paper_title="Paper 1",
            exam_year=2026,
        )
    )

    assert resolution.status == "ready"
    assert resolution.route is not None
    assert resolution.route.route_id == "configured_subject_2174_2026"


def test_generic_route_extracts_non_history_mock_output(tmp_path) -> None:
    md = tmp_path / "math.md"
    md.write_text("## Page 1\n1. Calculate 2 + 2. [1]\n", encoding="utf-8")
    pdf = Path("paper.pdf")
    first_page = FirstPageCheck(
        is_exam_paper=True,
        subject="Mathematics",
        paper_code="4048/01",
        paper_title="Paper 1",
        exam_year=2026,
    )
    syllabus_json = tmp_path / "syllabus.json"
    write_json(
        syllabus_json,
        {
            "subject": "Mathematics",
            "subject_code": "4048",
            "year": 2026,
            "source_url": "local",
            "pdf_path": "",
            "markdown_path": "",
            "objectives": [{"ao_id": "GENERIC", "name": "Generic", "description": "Generic objective", "skills": []}],
            "components": [{"paper": "4048/01", "section": "Main", "name": "Paper 1", "marks": 0, "objectives": ["GENERIC"], "rules": []}],
            "topics": [{"topic_id": "generic", "paper": "4048/01", "unit": "Generic", "topic": "Generic topic"}],
        },
    )
    route = GenericSubjectRoute(
        route_config=RouteConfig(
            route_id="configured_subject_4048_2026",
            subject="Mathematics",
            subject_code="4048",
            year=2026,
            syllabus_json_path=syllabus_json,
        )
    )
    syllabus = route.load_syllabus(first_page)
    exam, artifact = route.extract_exam(
        md,
        pdf,
        first_page,
        syllabus,
        LocalModelClient(provider="mock", base_url="http://localhost:1234/v1", model="mock"),
    )

    assert artifact["fallback_used"] is False
    assert exam.subject == "Mathematics"
    assert exam.paper_code == "4048/01"
    assert exam.questions[0].page_number == 1
