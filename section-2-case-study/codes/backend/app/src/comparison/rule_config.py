from __future__ import annotations

from pathlib import Path

from backend.app.core.storage import read_json


DEFAULT_RULE_CONFIG = {
    "paper_codes": ["2174/01", "2174/02"],
    "rules": [
        {"rule_id": "total_candidate_marks", "description": "Paper should total 50 candidate marks", "field": "total_marks", "operator": "equals", "value": 50, "severity_if_failed": "ERROR"},
        {"rule_id": "section_a_marks", "description": "Section A should total 30 marks", "field": "section_a_marks", "operator": "equals", "value": 30, "severity_if_failed": "ERROR"},
        {"rule_id": "section_b_candidate_marks", "description": "Candidates should answer 20 marks from Section B", "field": "section_b_candidate_marks", "operator": "equals", "value": 20, "severity_if_failed": "ERROR"},
        {"rule_id": "source_count_max", "description": "Source-based case study should have at most 6 sources", "field": "source_count", "operator": "lte", "value": 6, "severity_if_failed": "WARNING"},
    ],
}


def load_rule_config(path: Path | None = None) -> dict:
    if path and path.exists():
        return read_json(path)
    return DEFAULT_RULE_CONFIG
