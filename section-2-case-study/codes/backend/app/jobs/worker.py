from __future__ import annotations

from pathlib import Path

from backend.app.src.graph.workflow import run_analysis


def run_job(pdf_path: Path, job_id: str) -> dict:
    return run_analysis(pdf_path, job_id)
