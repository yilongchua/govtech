from __future__ import annotations

import re
from pathlib import Path

from backend.app.schemas.base import ValidationIssue
from backend.app.schemas.exam import ExamPaper, ExamQuestion, FirstPageCheck, SourceItem


def extract_history_exam(markdown_path: Path, pdf_path: Path, first_page: FirstPageCheck) -> ExamPaper:
    text = markdown_path.read_text(encoding="utf-8")
    markdown_paper_code = _search(r"HISTORY\s+([0-9]+/[0-9]+)", text)
    paper_code = markdown_paper_code or first_page.paper_code
    questions = _extract_questions(text)
    sources = _extract_sources(text)
    total_marks = _candidate_total_marks(questions)
    duration = 110 if "1 hour 50 minutes" in text else None
    issues: list[ValidationIssue] = []
    if not first_page.is_exam_paper:
        issues.append(ValidationIssue(code="first_page_not_exam", severity="ERROR", stage="first_page_check", message="First page was not classified as an exam-paper cover.", evidence=first_page.model_dump()))
    if (first_page.subject or "").lower() != "history":
        issues.append(ValidationIssue(code="not_history", severity="ERROR", stage="first_page_check", message="This launcher is specific to History exam papers.", evidence=first_page.model_dump()))
    if not questions:
        issues.append(ValidationIssue(code="no_questions", severity="ERROR", stage="exam_extraction", message="No questions were extracted from the paper."))
    return ExamPaper(
        subject=first_page.subject or "History",
        paper_code=paper_code,
        paper_title=_paper_title(text, paper_code) or first_page.paper_title or "History exam paper",
        exam_year=first_page.exam_year,
        duration_minutes=duration,
        total_marks=total_marks,
        raw_pdf_path=str(pdf_path),
        markdown_path=str(markdown_path),
        sources=sources,
        questions=questions,
        issues=issues,
    )


def _extract_questions(text: str) -> list[ExamQuestion]:
    questions: list[ExamQuestion] = []
    section: str | None = None
    current: tuple[str, str, str | None, list[str], int | None] | None = None
    page_number: int | None = None

    def flush() -> None:
        nonlocal current
        if not current:
            return
        qid, q_section, choice_group, parts, question_page = current
        block = _clean_prompt(" ".join(parts))
        match = re.search(r"\[(\d+)\]\s*$", block)
        if not match:
            current = None
            return
        marks = int(match.group(1))
        prompt = _clean_prompt(re.sub(r"\s*\[\d+\]\s*$", "", block))
        questions.append(
            ExamQuestion(
                question_id=qid,
                section=q_section,
                prompt=prompt,
                marks=marks,
                required_sources=_sources_from_prompt(prompt),
                choice_group=choice_group,
                page_number=question_page,
            )
        )
        current = None

    for line in text.splitlines():
        stripped = line.strip()
        page_match = re.match(r"## Page\s+(\d+)", stripped)
        if page_match:
            flush()
            page_number = int(page_match.group(1))
            continue
        if not stripped or stripped == "OR":
            continue
        if stripped.startswith("Section A"):
            flush()
            section = "A"
            continue
        if stripped.startswith("Section B"):
            flush()
            section = "B"
            continue
        if section == "A":
            match_a = re.match(r"^(?:1\s+)?\(([a-e])\)\s+(.+)$", stripped)
            if match_a:
                flush()
                part, prompt_start = match_a.groups()
                current = (f"1({part})", "A", None, [prompt_start], page_number)
                continue
        if section == "B":
            match_q = re.match(r"^([2-9])(?:\s+\(([ab])\))?\s+(.+)$", stripped)
            if match_q:
                flush()
                qn, part, prompt_start = match_q.groups()
                qid = f"{qn}({part})" if part else qn
                choice_group = f"{qn}_either_or" if part else None
                current = (qid, "B", choice_group, [prompt_start], page_number)
                continue
        if current:
            current[3].append(stripped)
    flush()
    return questions


def _candidate_total_marks(questions: list[ExamQuestion]) -> int | None:
    if not questions:
        return None
    section_a_marks = sum(q.marks or 0 for q in questions if q.section == "A")
    section_b_questions = [q for q in questions if q.section == "B"]
    if section_a_marks and section_b_questions:
        return section_a_marks + 20
    return sum(q.marks or 0 for q in questions)


def _extract_sources(text: str) -> list[SourceItem]:
    sources = []
    for match in re.finditer(r"Source ([A-F]):\s+(.+?)(?=\nSource [A-F]:|\n## Page|\Z)", text, re.S):
        sid, body = match.groups()
        page_number = _page_number_before(text, match.start())
        first_line, _, rest = body.strip().partition("\n")
        sources.append(SourceItem(source_id=sid, source_type=_infer_source_type(first_line), attribution=first_line.strip(), text=rest.strip() or None, page_number=page_number))
    return sources


def _infer_source_type(attribution: str) -> str:
    lowered = attribution.lower()
    if "cartoon" in lowered:
        return "cartoon"
    if "photograph" in lowered:
        return "photograph"
    if "speech" in lowered:
        return "speech"
    if "letter" in lowered:
        return "letter"
    return "text"


def _sources_from_prompt(prompt: str) -> list[str]:
    return re.findall(r"Source(?:s)? ([A-F])", prompt)


def _clean_prompt(prompt: str) -> str:
    return re.sub(r"\s+", " ", prompt).strip()


def _search(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1) if match else None


def _page_number_before(text: str, index: int) -> int | None:
    pages = list(re.finditer(r"## Page\s+(\d+)", text[:index]))
    return int(pages[-1].group(1)) if pages else None


def _paper_title(text: str, paper_code: str | None) -> str | None:
    if not paper_code:
        return None
    paper_number = paper_code.split("/")[-1].lstrip("0")
    match = re.search(rf"Paper {paper_number}\s+(.+?)\s+For examination", text, re.S)
    if match:
        return _clean_prompt(f"Paper {paper_number} {match.group(1)}")
    return f"Paper {paper_number}"
