from __future__ import annotations

from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.storage import read_json, write_json


def cache_report_path(pdf_sha256: str) -> Path:
    return settings.data_dir / "processed" / "cache" / pdf_sha256 / "comparison_report.json"


def load_cached_report(pdf_sha256: str, job_id: str) -> dict | None:
    path = cache_report_path(pdf_sha256)
    if not path.exists():
        return None
    report = read_json(path)
    report["job_id"] = job_id
    write_json(settings.data_dir / "processed" / "json" / job_id / "comparison_report.json", report)
    return report


def store_cached_report(pdf_sha256: str, report: dict) -> None:
    write_json(cache_report_path(pdf_sha256), report)
