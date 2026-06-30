from __future__ import annotations

from pathlib import Path
import hashlib

from backend.app.schemas.base import ValidationIssue
from backend.app.core.config import get_model_settings, settings
from backend.app.core.storage import job_dir, write_json
from backend.app.src.comparison.topic_weightage import calculate_topic_weightage
from backend.app.src.ingestion.first_page_classifier import classify_first_page
from backend.app.src.ingestion.model_client import LLMClient
from backend.app.src.ingestion.model_preflight import check_text_json_capability
from backend.app.src.ingestion.page_renderer import render_first_page
from backend.app.src.ingestion.pdf_guard import validate_pdf_file
from backend.app.src.ingestion.pdf_to_markdown import convert_pdf_to_markdown
from backend.app.src.extraction.image_source_interpreter import interpret_image_only_sources
from backend.app.src.reporting.report_builder import build_report
from backend.app.src.subjects import resolve_subject_route_with_status


def run_analysis(
    pdf_path: Path,
    job_id: str,
    provider: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    selected_subject_code: str | None = None,
) -> dict:
    issues = validate_pdf_file(pdf_path)
    audit_events: list[dict] = [{"stage": "start", "pdf_path": str(pdf_path), "selected_subject_code": selected_subject_code}]
    pdf_sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    image_path = render_first_page(pdf_path, settings.data_dir / "processed" / "images" / job_id)
    audit_events.append({"stage": "render_first_page", "image_path": str(image_path)})
    configured_model = get_model_settings()
    client = LLMClient(
        provider=provider or configured_model.provider,
        base_url=base_url or configured_model.base_url,
        model=model or configured_model.model,
        timeout=configured_model.timeout_seconds,
    )
    text_preflight_issue, text_preflight_artifact = check_text_json_capability(client)
    if text_preflight_issue is not None:
        issues.append(text_preflight_issue)
    audit_events.append(
        {
            "stage": "model_text_json_preflight",
            "ok": text_preflight_artifact["ok"],
            "reason": text_preflight_artifact.get("reason"),
        }
    )
    first_page = classify_first_page(image_path, client)
    write_json(
        job_dir("json", job_id) / "raw_model_response.json",
        {
            "model_text_json_preflight": text_preflight_artifact,
            "first_page_check": first_page.model_dump(mode="json"),
            "raw_response": client.last_raw_response,
            "prompt": client.last_prompt,
            "prompt_version": "classify_first_page.j2:2026-06-29",
        },
    )
    audit_events.append({"stage": "classify_first_page", "subject": first_page.subject, "paper_code": first_page.paper_code})
    route_resolution = resolve_subject_route_with_status(first_page, selected_subject_code=selected_subject_code)
    audit_events.append(
        {
            "stage": "resolve_subject_route",
            "status": route_resolution.status,
            "reason": route_resolution.reason,
            "candidates": route_resolution.candidates or [],
        }
    )
    if route_resolution.status != "ready" or route_resolution.route is None:
        return _stopped_route_report(job_id, first_page, route_resolution, audit_events)
    route = route_resolution.route
    audit_events.append({"stage": "resolve_subject_route", "route_id": route.route_id, "subject_label": route.subject_label})
    md_path = job_dir("markdown", job_id) / "exam.md"
    convert_pdf_to_markdown(pdf_path, md_path)
    audit_events.append({"stage": "convert_pdf_to_markdown", "markdown_path": str(md_path)})
    syllabus = route.load_syllabus(first_page)
    exam, extraction_artifact = route.extract_exam(md_path, pdf_path, first_page, syllabus, client)
    image_source_artifact = interpret_image_only_sources(
        exam,
        pdf_path,
        settings.data_dir / "processed" / "images" / job_id / "sources",
        client,
    )
    extraction_artifact["image_source_interpretation"] = image_source_artifact
    write_json(
        job_dir("json", job_id) / "raw_extraction.json",
        {
            "first_page_check": first_page.model_dump(mode="json"),
            "markdown_path": str(md_path),
            "pdf_sha256": pdf_sha256,
            "exam_extraction": extraction_artifact,
        },
    )
    write_json(job_dir("json", job_id) / "exam_structure.json", exam.model_dump(mode="json"))
    exam.issues.extend(issues)
    rule_checks, rule_issues = route.run_rules(exam, syllabus)
    exam.issues.extend(rule_issues)
    annotations = route.annotate(exam, syllabus, client)
    topic_weightage = calculate_topic_weightage(exam, annotations)
    report = build_report(
        job_id,
        syllabus,
        exam,
        rule_checks,
        annotations,
        topic_weightage,
        structure_metrics=route.structure_metrics(exam, syllabus),
        route_id=route.route_id,
    )
    output_path = job_dir("json", job_id) / "comparison_report.json"
    write_json(output_path, report.model_dump(mode="json"))
    audit_events.append({"stage": "complete", "report_path": str(output_path), "issue_count": len(report.issues)})
    write_json(job_dir("json", job_id) / "audit_log.json", {"job_id": job_id, "events": audit_events})
    return report.model_dump(mode="json")


def _stopped_route_report(job_id: str, first_page, route_resolution, audit_events: list[dict]) -> dict:
    issue = ValidationIssue(
        code=f"route_resolution_{route_resolution.status}",
        severity="ERROR" if route_resolution.status == "unsupported" else "WARNING",
        stage="route_resolution",
        message="Processing stopped because the PDF could not be matched to a configured subject route.",
        reason=route_resolution.reason,
        evidence={
            "first_page_check": first_page.model_dump(mode="json"),
            "route_candidates": route_resolution.candidates or [],
        },
        recoverable=True,
    )
    payload = {
        "job_id": job_id,
        "status": "stopped",
        "stage": "route_resolution",
        "reason": route_resolution.reason,
        "message": "The backend could not confidently match this PDF to a configured syllabus route.",
        "first_page_check": first_page.model_dump(mode="json"),
        "route_candidates": route_resolution.candidates or [],
        "issues": [issue.model_dump(mode="json")],
    }
    output_path = job_dir("json", job_id) / "comparison_report.json"
    write_json(output_path, payload)
    audit_events.append({"stage": "stopped", "report_path": str(output_path), "reason": route_resolution.reason})
    write_json(job_dir("json", job_id) / "audit_log.json", {"job_id": job_id, "events": audit_events})
    return payload


def run_history_analysis(
    pdf_path: Path,
    job_id: str,
    provider: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> dict:
    return run_analysis(pdf_path, job_id, provider=provider, base_url=base_url, model=model)
