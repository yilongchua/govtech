from __future__ import annotations

from typing import Any, TypedDict


class AnalysisState(TypedDict, total=False):
    job_id: str
    pdf_path: str
    page_image_paths: list[str]
    markdown_path: str
    first_page_check: dict[str, Any]
    subject: str
    paper_code: str
    syllabus_doc: dict[str, Any]
    exam_paper: dict[str, Any]
    annotations: list[dict[str, Any]]
    rule_checks: list[dict[str, Any]]
    comparison_report: dict[str, Any]
    issues: list[dict[str, Any]]

