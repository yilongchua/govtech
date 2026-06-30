from __future__ import annotations

import re
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import orjson
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response

from backend.app.api.state import JOBS
from backend.app.core.config import settings
from backend.app.src.reporting.docx_export import DOCX_MEDIA_TYPE, report_to_docx
from backend.app.src.reporting.markdown_export import report_to_markdown

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    if job_id in JOBS:
        return {"job_id": job_id, **JOBS[job_id]}
    job_path = settings.data_dir / "processed" / "json" / job_id / "job.json"
    if job_path.exists():
        return {"job_id": job_id, **orjson.loads(job_path.read_bytes())}
    raise HTTPException(status_code=404, detail="Job not found.")


@router.get("/jobs/{job_id}/report")
def get_report(job_id: str) -> dict:
    report_path = settings.data_dir / "processed" / "json" / job_id / "comparison_report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found.")
    return orjson.loads(report_path.read_bytes())


@router.get("/jobs/{job_id}/report.md", response_class=PlainTextResponse)
def get_report_markdown(job_id: str) -> str:
    report = get_report(job_id)
    return report_to_markdown(report)


@router.get("/jobs/{job_id}/report.docx")
def get_report_docx(job_id: str) -> Response:
    report = get_report(job_id)
    filename = f"{report.get('download_filename_base') or f'exam-alignment-{job_id}'}.docx"
    return Response(
        content=report_to_docx(report),
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/batches/{batch_id}")
def get_batch(batch_id: str) -> dict:
    batch_path = settings.data_dir / "processed" / "json" / "batches" / f"{batch_id}.json"
    if not batch_path.exists():
        raise HTTPException(status_code=404, detail="Batch not found.")
    return orjson.loads(batch_path.read_bytes())


@router.get("/batches/{batch_id}/reports.zip")
def get_batch_reports_zip(batch_id: str) -> Response:
    batch = get_batch(batch_id)
    buffer = BytesIO()
    used_names: set[str] = set()
    failures = []
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for index, job in enumerate(batch.get("jobs", []), start=1):
            job_id = job.get("job_id")
            if not job_id:
                continue
            if job.get("status") != "complete":
                failures.append(
                    {
                        "job_id": job_id,
                        "filename": job.get("filename"),
                        "status": job.get("status"),
                        "error": job.get("error"),
                    }
                )
                continue
            report = get_report(job_id)
            base = _unique_archive_base(
                used_names,
                report.get("download_filename_base") or job.get("filename") or f"exam-alignment-{job_id}",
                index,
            )
            archive.writestr(f"{base}.json", orjson.dumps(report, option=orjson.OPT_INDENT_2))
            archive.writestr(f"{base}.docx", report_to_docx(report))
        if failures:
            archive.writestr("failed-uploads.json", orjson.dumps(failures, option=orjson.OPT_INDENT_2))

    filename = f"exam-alignment-reports-{batch_id}.zip"
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _unique_archive_base(used_names: set[str], raw_name: str, index: int) -> str:
    base = re.sub(r"\.pdf$", "", raw_name, flags=re.IGNORECASE)
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip(".-")
    if not base:
        base = f"report-{index}"
    candidate = base
    suffix = 2
    while candidate in used_names:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used_names.add(candidate)
    return candidate
