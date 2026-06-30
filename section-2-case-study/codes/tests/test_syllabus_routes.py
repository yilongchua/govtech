from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.api import routes_syllabus
from backend.app.core.storage import write_json
from backend.app.main import app
from backend.app.schemas.syllabus import AssessmentComponent, AssessmentObjective, SyllabusDocument, SyllabusTopic
from backend.app.src.syllabus.llm_syllabus_extractor import (
    SyllabusComponentsResult,
    SyllabusExtractionError,
    SyllabusMetadata,
    SyllabusObjectivesResult,
    SyllabusTopicsResult,
)
from backend.app.src.syllabus import syllabus_registry


def _settings(tmp_path):
    root = tmp_path
    return SimpleNamespace(root_dir=root, data_dir=root / "data", history_syllabus_year=2026)


def _syllabus(subject_code: str, pdf_path: Path, md_path: Path) -> SyllabusDocument:
    return SyllabusDocument(
        subject="History" if subject_code == "2174" else "Science",
        subject_code=subject_code,
        year=2026,
        source_url=f"https://example.test/{subject_code}_y26_sy.pdf",
        pdf_path=str(pdf_path),
        markdown_path=str(md_path),
        objectives=[AssessmentObjective(ao_id="AO1", name="Objective", description="Description", skills=[])],
        components=[
            AssessmentComponent(
                paper=f"{subject_code}/01",
                section="A",
                name="Paper 1",
                marks=50,
                objectives=["AO1"],
                rules=["Answer all questions"],
            )
        ],
        topics=[
            SyllabusTopic(
                topic_id="topic_1",
                paper=f"{subject_code}/01",
                unit="Unit",
                topic="Topic",
            )
        ],
    )


class _Response:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self) -> None:
        return None


def _setup_ingest_test(monkeypatch, tmp_path, subject_code: str):
    fake_settings = _settings(tmp_path)
    monkeypatch.setattr(routes_syllabus, "settings", fake_settings)
    monkeypatch.setattr(syllabus_registry, "settings", fake_settings)
    monkeypatch.setattr(
        routes_syllabus,
        "resolve_seab_syllabus_pdf",
        lambda source_url: (f"https://example.test/{subject_code}_y26_sy.pdf", "Label", "https://example.test/page"),
    )
    pdf_bytes = Path("2174_y26_sy.pdf").read_bytes()
    monkeypatch.setattr(routes_syllabus.httpx, "get", lambda *args, **kwargs: _Response(pdf_bytes))
    return fake_settings


@pytest.mark.parametrize("subject_code", ["2174", "1136"])
def test_ingest_url_always_uses_llm_syllabus_extractor(monkeypatch, tmp_path, subject_code) -> None:
    fake_settings = _setup_ingest_test(monkeypatch, tmp_path, subject_code)
    calls = []

    def fake_metadata(markdown, client):
        calls.append({"call": "metadata", "timeout": client.timeout})
        return SyllabusMetadata(subject="History", subject_code=subject_code, year=2026), {"call": "metadata"}

    monkeypatch.setattr(routes_syllabus, "extract_syllabus_metadata", fake_metadata)
    monkeypatch.setattr(
        routes_syllabus,
        "extract_syllabus_objectives",
        lambda markdown, client: (SyllabusObjectivesResult(objectives=_syllabus(subject_code, Path("paper.pdf"), Path("sy.md")).objectives), {"call": "objectives"}),
    )
    monkeypatch.setattr(
        routes_syllabus,
        "extract_syllabus_components",
        lambda markdown, client: (SyllabusComponentsResult(components=_syllabus(subject_code, Path("paper.pdf"), Path("sy.md")).components), {"call": "components"}),
    )
    monkeypatch.setattr(
        routes_syllabus,
        "extract_syllabus_topics",
        lambda markdown, client: (SyllabusTopicsResult(topics=_syllabus(subject_code, Path("paper.pdf"), Path("sy.md")).topics), {"call": "topics"}),
    )

    response = TestClient(app).post("/api/syllabuses/ingest-url", json={"url": "https://example.test/page"})

    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0]["timeout"] > 0
    assert response.json()["subject_code"] == subject_code
    assert Path(response.json()["json_path"]).exists()
    assert Path(response.json()["extraction_artifact_path"]).exists()
    assert (fake_settings.data_dir / "reference" / "syllabus_index.json").exists()


def test_ingest_url_events_streams_llm_call_and_completion(monkeypatch, tmp_path) -> None:
    _setup_ingest_test(monkeypatch, tmp_path, "2174")

    monkeypatch.setattr(routes_syllabus, "extract_syllabus_metadata", lambda markdown, client: (SyllabusMetadata(subject="History", subject_code="2174", year=2026), {"call": "metadata"}))
    monkeypatch.setattr(routes_syllabus, "extract_syllabus_objectives", lambda markdown, client: (SyllabusObjectivesResult(objectives=_syllabus("2174", Path("paper.pdf"), Path("sy.md")).objectives), {"call": "objectives"}))
    monkeypatch.setattr(routes_syllabus, "extract_syllabus_components", lambda markdown, client: (SyllabusComponentsResult(components=_syllabus("2174", Path("paper.pdf"), Path("sy.md")).components), {"call": "components"}))
    monkeypatch.setattr(routes_syllabus, "extract_syllabus_topics", lambda markdown, client: (SyllabusTopicsResult(topics=_syllabus("2174", Path("paper.pdf"), Path("sy.md")).topics), {"call": "topics"}))

    with TestClient(app).stream("POST", "/api/syllabuses/ingest-url/events", json={"url": "https://example.test/page"}) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"stage": "llm_metadata"' in body
    assert '"stage": "llm_objectives"' in body
    assert '"stage": "llm_components"' in body
    assert '"stage": "llm_topics"' in body
    assert '"step": 8' in body
    assert '"total_steps": 12' in body
    assert "Calling local LLM" in body
    assert '"status": "complete"' in body
    assert '"subject_code": "2174"' in body


def test_ingest_url_rejects_incomplete_llm_extraction_without_registry_write(monkeypatch, tmp_path) -> None:
    fake_settings = _setup_ingest_test(monkeypatch, tmp_path, "2174")

    def fake_metadata(*args, **kwargs):
        raise SyllabusExtractionError("topics")

    monkeypatch.setattr(routes_syllabus, "extract_syllabus_metadata", fake_metadata)

    response = TestClient(app).post("/api/syllabuses/ingest-url", json={"url": "https://example.test/page"})

    assert response.status_code == 422
    assert not (fake_settings.data_dir / "reference" / "syllabus_index.json").exists()


def test_requirement_rows_do_not_fall_back_to_markdown(tmp_path) -> None:
    md = tmp_path / "syllabus.md"
    md.write_text("## Page 1\nASSESSMENT OBJECTIVES\nThis looks useful but is unstructured.\n", encoding="utf-8")

    assert routes_syllabus._requirement_rows({"objectives": [], "components": [], "topics": []}, md) == []


def test_syllabus_pdf_is_served_inline_for_preview(tmp_path, monkeypatch) -> None:
    fake_settings = _settings(tmp_path)
    monkeypatch.setattr(routes_syllabus, "settings", fake_settings)
    pdf_path = fake_settings.data_dir / "raw" / "syllabus_pdfs" / "2174_y26_sy.pdf"
    json_path = fake_settings.data_dir / "processed" / "json" / "syllabus" / "2174_y26_sy.json"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(Path("2174_y26_sy.pdf").read_bytes())
    write_json(
        fake_settings.data_dir / "reference" / "syllabus_index.json",
        {
            "syllabuses": [
                {
                    "subject": "History",
                    "subject_code": "2174",
                    "year": 2026,
                    "pdf_path": str(pdf_path),
                    "json_path": str(json_path),
                }
            ]
        },
    )
    write_json(json_path, {"pdf_path": str(pdf_path)})

    response = TestClient(app).get("/api/syllabuses/2174/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline;")
