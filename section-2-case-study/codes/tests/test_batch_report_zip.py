from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

import orjson

from backend.app.api import routes_jobs


def test_batch_reports_zip_contains_completed_reports_and_failures(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(routes_jobs, "settings", SimpleNamespace(data_dir=tmp_path))
    report = {
        "job_id": "job-one",
        "download_filename_base": "history-paper-one",
        "exam_paper": {
            "subject": "History",
            "paper_code": "2174/01",
            "paper_title": "Paper 1",
            "total_marks": 50,
            "questions": [],
            "sources": [],
        },
        "syllabus": {"subject": "History", "subject_code": "2174", "year": 2026},
        "rule_checks": [],
        "topic_weightage": [],
        "annotations": [],
        "issues": [],
    }
    report_dir = tmp_path / "processed" / "json" / "job-one"
    report_dir.mkdir(parents=True)
    (report_dir / "comparison_report.json").write_bytes(orjson.dumps(report))
    batch_dir = tmp_path / "processed" / "json" / "batches"
    batch_dir.mkdir(parents=True)
    (batch_dir / "batch-one.json").write_bytes(
        orjson.dumps(
            {
                "batch_id": "batch-one",
                "status": "partial",
                "jobs": [
                    {"job_id": "job-one", "filename": "history paper.pdf", "status": "complete"},
                    {"job_id": "job-two", "filename": "bad.pdf", "status": "failed", "error": "Unreadable PDF"},
                ],
            }
        )
    )

    response = routes_jobs.get_batch_reports_zip("batch-one")

    assert response.media_type == "application/zip"
    with ZipFile(BytesIO(response.body)) as archive:
        names = set(archive.namelist())
        assert "history-paper-one.json" in names
        assert "history-paper-one.docx" in names
        assert "failed-uploads.json" in names
        failures = orjson.loads(archive.read("failed-uploads.json"))
    assert failures == [{"job_id": "job-two", "filename": "bad.pdf", "status": "failed", "error": "Unreadable PDF"}]
