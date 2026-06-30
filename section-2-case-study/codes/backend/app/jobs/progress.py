from __future__ import annotations

from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.storage import write_json


def write_progress(job_id: str, status: str, progress: int, stage: str, **extra: object) -> dict:
    payload = {"job_id": job_id, "status": status, "progress": progress, "stage": stage, **extra}
    path = settings.data_dir / "processed" / "json" / job_id / "job.json"
    write_json(path, payload)
    return payload

