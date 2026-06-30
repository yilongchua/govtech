from __future__ import annotations

from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.storage import read_json, write_json
from backend.app.schemas.syllabus import SyllabusDocument


def write_syllabus_registry(
    syllabus: SyllabusDocument,
    pdf_sha256: str | None = None,
    *,
    source_page_url: str = "https://www.seab.gov.sg/gce-o-level/o-level-syllabuses-examined-for-school-candidates-2026/",
    json_path: Path | None = None,
) -> None:
    settings.data_dir.joinpath("reference").mkdir(parents=True, exist_ok=True)
    slug = _syllabus_slug(syllabus)
    resolved_json_path = json_path or settings.data_dir / "processed" / "json" / "syllabus" / f"{slug}.json"
    index = {
        "subject": syllabus.subject,
        "subject_code": syllabus.subject_code,
        "year": syllabus.year,
        "source_page_url": source_page_url,
        "pdf_url": syllabus.source_url,
        "pdf_sha256": pdf_sha256,
        "markdown_path": syllabus.markdown_path,
        "json_path": str(resolved_json_path),
    }
    entries = _read_syllabus_entries()
    entries = [entry for entry in entries if not (entry.get("subject_code") == syllabus.subject_code and entry.get("year") == syllabus.year)]
    entries.append(index)
    write_json(settings.data_dir / "reference" / "syllabus_index.json", {"latest": index, "syllabuses": entries})

    subjects = []
    for entry in entries:
        subject = {"subject": entry["subject"], "subject_code": entry["subject_code"], "latest_year": entry["year"]}
        existing = next((item for item in subjects if item["subject_code"] == subject["subject_code"]), None)
        if existing is None:
            subjects.append(subject)
        elif subject["latest_year"] >= existing["latest_year"]:
            existing.update(subject)
    write_json(settings.data_dir / "reference" / "subject_registry.json", {"subjects": subjects})


def latest_syllabus_json_path() -> Path:
    return settings.data_dir / "processed" / "json" / "syllabus" / "2174_y26_sy.json"


def _syllabus_slug(syllabus: SyllabusDocument) -> str:
    return f"{syllabus.subject_code}_y{str(syllabus.year)[-2:]}_sy".lower()


def _read_syllabus_entries() -> list[dict]:
    path = settings.data_dir / "reference" / "syllabus_index.json"
    if not path.exists():
        return []
    payload = read_json(path)
    if isinstance(payload.get("syllabuses"), list):
        return payload["syllabuses"]
    if payload.get("subject_code"):
        return [payload]
    return []
