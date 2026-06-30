from __future__ import annotations

from backend.app.schemas.comparison import ComparisonReport, QuestionAnnotation, RuleCheckResult, StructureMetric, TopicWeightage
from backend.app.schemas.exam import ExamPaper
from backend.app.schemas.syllabus import SyllabusDocument
from backend.app.src.reporting.chart_payloads import build_chart_payloads


def build_report(
    job_id: str,
    syllabus: SyllabusDocument,
    exam: ExamPaper,
    rule_checks: list[RuleCheckResult],
    annotations: list[QuestionAnnotation],
    topic_weightage: list[TopicWeightage],
    structure_metrics: list[StructureMetric] | None = None,
    route_id: str = "generic_exam_subject",
) -> ComparisonReport:
    issues = [*syllabus.issues, *exam.issues]
    for check in rule_checks:
        if not check.passed:
            from backend.app.schemas.base import ValidationIssue

            issues.append(ValidationIssue(code=check.rule_id, severity=check.severity_if_failed, stage="report", message="Rule check did not pass.", reason=f"Expected {check.expected}; observed {check.observed}"))
    paper_label = exam.paper_code or exam.paper_title or "Exam paper"
    summary = [
        f"{paper_label} is compared against the {syllabus.year} {syllabus.subject} syllabus baseline.",
        "Question and source page numbers are retained for traceability.",
    ]
    if syllabus.source_url == "unconfigured":
        summary.append("Generic route was used; configure the subject syllabus and rule pack for production-grade alignment.")
    chart_payloads = build_chart_payloads(exam, annotations, topic_weightage)
    filename_subject = (syllabus.subject or "exam").lower().replace(" ", "-")
    return ComparisonReport(
        job_id=job_id,
        syllabus=syllabus,
        exam_paper=exam,
        rule_checks=rule_checks,
        annotations=annotations,
        topic_weightage=topic_weightage,
        structure_metrics=structure_metrics or [],
        download_filename_base=f"{filename_subject}-alignment-{job_id}",
        summary_findings=summary,
        chart_payloads=chart_payloads,
        issues=issues,
    )
