from __future__ import annotations

from backend.app.schemas.base import ValidationIssue
from backend.app.schemas.comparison import RuleCheckResult
from backend.app.schemas.exam import ExamPaper
from backend.app.schemas.syllabus import SyllabusDocument
from backend.app.src.comparison.rule_config import load_rule_config


def run_history_paper_rules(exam: ExamPaper) -> tuple[list[RuleCheckResult], list[ValidationIssue]]:
    config = load_rule_config()
    checks: list[RuleCheckResult] = []
    issues: list[ValidationIssue] = []

    def add(rule_id: str, expected: str, observed: str, passed: bool, severity: str = "WARNING") -> None:
        checks.append(RuleCheckResult(rule_id=rule_id, expected=expected, observed=observed, passed=passed, severity_if_failed=severity))
        if not passed:
            issues.append(ValidationIssue(code=rule_id, severity=severity, stage="rule_checks", message=f"Rule failed: {rule_id}", reason=f"Expected {expected}; observed {observed}"))

    section_a_marks = sum(q.marks or 0 for q in exam.questions if q.section == "A")
    section_b_questions = [q for q in exam.questions if q.section == "B"]
    section_b_offered = _effective_offered_marks(section_b_questions)
    section_b_candidate = 20 if section_b_offered >= 20 else section_b_offered
    add("history_launcher_subject", "History", exam.subject or "unknown", (exam.subject or "").lower() == "history", "ERROR")
    config_by_id = {rule["rule_id"]: rule for rule in config.get("rules", [])}
    add("supported_paper_code", "2174/01 or 2174/02", exam.paper_code or "unknown", exam.paper_code in {"2174/01", "2174/02"}, "ERROR")
    add("total_candidate_marks", "50 candidate marks", str(exam.total_marks), exam.total_marks == config_by_id.get("total_candidate_marks", {}).get("value", 50), "ERROR")
    add("section_a_marks", "30", str(section_a_marks), section_a_marks == config_by_id.get("section_a_marks", {}).get("value", 30), "ERROR")
    add("section_b_candidate_marks", "20", str(section_b_candidate), section_b_candidate == config_by_id.get("section_b_candidate_marks", {}).get("value", 20), "ERROR")
    add("section_b_offered_questions", "At least 3 offered essay prompts", str(len(section_b_questions)), len(section_b_questions) >= 3, "WARNING")
    add("source_count_max", "<= 6", str(len(exam.sources)), len(exam.sources) <= config_by_id.get("source_count_max", {}).get("value", 6), "WARNING")
    for qid in ["1(a)", "1(b)", "1(c)", "1(d)", "1(e)"]:
        add(f"has_{qid}", "present", "present" if any(q.question_id == qid for q in exam.questions) else "missing", any(q.question_id == qid for q in exam.questions), "ERROR")
    add("section_b_offered_marks", "30 offered marks, 20 candidate marks", str(section_b_offered), section_b_offered >= 30, "WARNING")
    return checks, issues


def run_generic_paper_rules(exam: ExamPaper, syllabus: SyllabusDocument) -> tuple[list[RuleCheckResult], list[ValidationIssue]]:
    checks: list[RuleCheckResult] = []
    issues: list[ValidationIssue] = []

    def add(rule_id: str, expected: str, observed: str, passed: bool, severity: str = "WARNING") -> None:
        checks.append(RuleCheckResult(rule_id=rule_id, expected=expected, observed=observed, passed=passed, severity_if_failed=severity))
        if not passed:
            issues.append(ValidationIssue(code=rule_id, severity=severity, stage="rule_checks", message=f"Rule failed: {rule_id}", reason=f"Expected {expected}; observed {observed}"))

    add("exam_subject_detected", "Known subject", exam.subject or "unknown", bool(exam.subject), "ERROR")
    add("paper_code_detected", "Paper code or component identifier when visible", exam.paper_code or "unknown", bool(exam.paper_code), "WARNING")
    add("questions_extracted", "At least one question", str(len(exam.questions)), len(exam.questions) > 0, "ERROR")
    add("question_page_traceability", "Every extracted question has a page number", _count_with_page_numbers(exam.questions), all(q.page_number is not None for q in exam.questions), "WARNING")
    add("source_page_traceability", "Every extracted source has a page number", _count_with_page_numbers(exam.sources), all(source.page_number is not None for source in exam.sources), "WARNING")
    if syllabus.source_url == "unconfigured":
        issues.append(
            ValidationIssue(
                code="generic_route_syllabus_unconfigured",
                severity="INFO",
                stage="rule_checks",
                message="Generic subject route was used; configure a subject-specific syllabus and rule pack for production-grade alignment.",
                evidence={"subject": exam.subject, "paper_code": exam.paper_code},
            )
        )
    return checks, issues


def _effective_offered_marks(questions) -> int:
    total = 0
    grouped: dict[str, int] = {}
    for question in questions:
        marks = question.marks or 0
        if question.choice_group:
            grouped[question.choice_group] = max(grouped.get(question.choice_group, 0), marks)
        else:
            total += marks
    return total + sum(grouped.values())


def _count_with_page_numbers(items) -> str:
    with_pages = sum(1 for item in items if item.page_number is not None)
    return f"{with_pages}/{len(items)}"
