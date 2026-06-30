from __future__ import annotations


def _sum_section_marks(questions: list[dict], section: str) -> int:
    return sum(item.get("marks") or 0 for item in questions if item.get("section") == section)


def _effective_offered_marks(questions: list[dict]) -> int:
    total = 0
    grouped: dict[str, int] = {}
    for question in questions:
        marks = question.get("marks") or 0
        choice_group = question.get("choice_group")
        if choice_group:
            grouped[choice_group] = max(grouped.get(choice_group, 0), marks)
        else:
            total += marks
    return total + sum(grouped.values())


def report_to_markdown(report: dict) -> str:
    paper = report.get("exam_paper", {})
    syllabus = report.get("syllabus", {})
    title_subject = syllabus.get("subject") or paper.get("subject") or "Exam"
    lines = [
        f"# {title_subject} {paper.get('paper_code') or 'Exam Paper'} Alignment Report",
        "",
        f"Job ID: `{report.get('job_id')}`",
        "",
        "## Document Summary",
        "",
        "| Field | Value |",
        "|---|---|",
    ]
    for key in ["subject", "paper_code", "paper_title", "exam_year", "duration_minutes", "total_marks"]:
        lines.append(f"| {key} | {paper.get(key, '')} |")
    lines.extend(["", "## Syllabus Baseline", "", "| Field | Value |", "|---|---|"])
    for key in ["subject", "subject_code", "year", "source_url"]:
        lines.append(f"| {key} | {syllabus.get(key, '')} |")
    lines.extend(["", "## Extracted Paper Structure", "", "| Field | Extracted value |", "|---|---:|"])
    metrics = report.get("structure_metrics") or [
        {"label": "Subject", "value": paper.get("subject") or "Unknown"},
        {"label": "Total marks", "value": paper.get("total_marks", "")},
        {"label": "Question count", "value": len(paper.get("questions", []))},
        {"label": "Source count", "value": len(paper.get("sources", []))},
    ]
    for item in metrics:
        lines.append(f"| {item.get('label')} | {item.get('value')} |")
    checks_requiring_attention = [check for check in report.get("rule_checks", []) if not check.get("passed")]
    lines.extend(["", "## Checks Requiring Attention", ""])
    if not checks_requiring_attention:
        lines.append("No structural checks require review.")
    else:
        lines.extend(["| Rule | Expected | Observed | Status |", "|---|---|---|---|"])
        for check in checks_requiring_attention:
            lines.append(f"| {check['rule_id']} | {check['expected']} | {check['observed']} | Review |")
    lines.extend(["", "## Topic Weightage", "", "| Topic | Required marks | Offered marks |", "|---|---:|---:|"])
    for item in report.get("topic_weightage", []):
        lines.append(f"| {item['topic']} | {item['required_marks']} | {item['offered_marks']} |")
    lines.extend(["", "## Objective Alignment", "", "| Question | Objectives | Topic | Evidence pages |", "|---|---|---|---|"])
    for item in report.get("annotations", []):
        pages = ", ".join(str(page) for page in item.get("evidence_page_numbers", []))
        lines.append(f"| {item['question_id']} | {', '.join(item['predicted_objectives'])} | {item['predicted_topic']} | {pages} |")
    lines.extend(["", "## Issues", ""])
    issues = report.get("issues", [])
    if not issues:
        lines.append("No issues recorded.")
    else:
        for issue in issues:
            lines.append(f"- **{issue['severity']}** `{issue['code']}`: {issue['message']}")
    return "\n".join(lines) + "\n"
