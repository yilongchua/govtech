from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.app.api.state import JOBS
from backend.app.core.analysis_cache import load_cached_report, store_cached_report
from backend.app.core.config import settings
from backend.app.core.storage import new_job_id, write_json
from backend.app.src.graph.workflow import run_analysis

router = APIRouter(prefix="/api", tags=["uploads"])


@router.post("/uploads")
async def upload_exam_paper(file: UploadFile = File(...), syllabus_subject_code: Optional[str] = Form(default=None)) -> dict:
    job = await _process_upload(file, syllabus_subject_code)
    return {"job_id": job["job_id"], **job["state"]}


@router.post("/uploads/batch")
async def upload_exam_papers(files: list[UploadFile] = File(...), syllabus_subject_code: Optional[str] = Form(default=None)) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF file is required.")
    jobs = [await _process_upload(file, syllabus_subject_code) for file in files]
    batch_id = new_job_id()
    batch = {
        "batch_id": batch_id,
        "status": "complete" if all(job["state"]["status"] == "complete" for job in jobs) else "partial",
        "jobs": [{"job_id": job["job_id"], "filename": job["filename"], **job["state"]} for job in jobs],
    }
    write_json(settings.data_dir / "processed" / "json" / "batches" / f"{batch_id}.json", batch)
    return batch


async def _process_upload(file: UploadFile, syllabus_subject_code: Optional[str] = None) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"PDF exceeds max upload size of {settings.max_upload_bytes} bytes.")
    job_id = new_job_id()
    pdf_sha256 = hashlib.sha256(content + (syllabus_subject_code or "").encode("utf-8")).hexdigest()
    upload_dir = settings.data_dir / "raw" / "uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / "original.pdf"
    pdf_path.write_bytes(content)

    original_filename = Path(file.filename).name
    if settings.analysis_cache_enabled:
        cached_report = load_cached_report(pdf_sha256, job_id)
        if cached_report is not None:
            JOBS[job_id] = {
                "status": "complete",
                "progress": 100,
                "stage": "cache-hit",
                "filename": original_filename,
                "report": cached_report,
            }
            write_json(settings.data_dir / "processed" / "json" / job_id / "job.json", JOBS[job_id])
            return {"job_id": job_id, "filename": original_filename, "state": JOBS[job_id]}

    JOBS[job_id] = {"status": "running", "progress": 10, "stage": "uploaded", "filename": original_filename}
    try:
        report = run_analysis(pdf_path, job_id, selected_subject_code=syllabus_subject_code)
        if settings.analysis_cache_enabled:
            store_cached_report(pdf_sha256, report)
        stopped = report.get("status") == "stopped"
        JOBS[job_id] = {
            "status": "stopped" if stopped else "complete",
            "progress": 100,
            "stage": report.get("stage", "complete") if stopped else "complete",
            "filename": original_filename,
            "report": report,
        }
        write_json(settings.data_dir / "processed" / "json" / job_id / "job.json", JOBS[job_id])
    except Exception as exc:
        JOBS[job_id] = {
            "status": "failed",
            "progress": 100,
            "stage": "failed",
            "filename": original_filename,
            "error": str(exc),
        }
        write_json(settings.data_dir / "processed" / "json" / job_id / "job.json", JOBS[job_id])
    return {"job_id": job_id, "filename": original_filename, "state": JOBS[job_id]}
