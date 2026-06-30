from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.app.core.config import settings


def ensure_data_dirs() -> None:
    for rel in [
        "raw/uploads",
        "raw/syllabus_pdfs",
        "raw/exam_pdfs",
        "processed/markdown",
        "processed/json",
        "processed/images",
        "processed/cache",
        "reference",
    ]:
        (settings.data_dir / rel).mkdir(parents=True, exist_ok=True)


def new_job_id() -> str:
    return uuid4().hex[:12]


def job_dir(kind: str, job_id: str) -> Path:
    path = settings.data_dir / "processed" / kind / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_dumps(payload))


def read_json(path: Path) -> dict:
    return _loads(path.read_bytes())


def _dumps(payload: object) -> bytes:
    try:
        import orjson

        return orjson.dumps(payload, option=orjson.OPT_INDENT_2 | orjson.OPT_SERIALIZE_NUMPY)
    except ModuleNotFoundError:
        import json

        return json.dumps(payload, indent=2, default=str).encode("utf-8")


def _loads(payload: bytes) -> dict:
    try:
        import orjson

        return orjson.loads(payload)
    except ModuleNotFoundError:
        import json

        return json.loads(payload.decode("utf-8"))
