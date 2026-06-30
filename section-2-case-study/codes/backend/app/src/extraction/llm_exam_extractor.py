from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.schemas.base import ValidationIssue
from backend.app.schemas.exam import ExamPaper, FirstPageCheck
from backend.app.schemas.syllabus import SyllabusDocument
from backend.app.src.extraction.exam_extractor import extract_history_exam
from backend.app.src.ingestion.model_client import LLMClient
from backend.app.src.prompts import render_prompt


def extract_history_exam_with_llm(
    markdown_path: Path,
    pdf_path: Path,
    first_page: FirstPageCheck,
    syllabus: SyllabusDocument,
    model_client: LLMClient,
) -> tuple[ExamPaper, dict[str, Any]]:
    return extract_exam_with_llm(
        markdown_path,
        pdf_path,
        first_page,
        syllabus,
        model_client,
        fallback_subject="history",
    )


def extract_exam_with_llm(
    markdown_path: Path,
    pdf_path: Path,
    first_page: FirstPageCheck,
    syllabus: SyllabusDocument,
    model_client: LLMClient,
    fallback_subject: str = "generic",
) -> tuple[ExamPaper, dict[str, Any]]:
    text = markdown_path.read_text(encoding="utf-8")
    prompt = render_prompt(
        "extract_exam_structure.j2",
        ExamPaper,
        subject_route=first_page.subject or syllabus.subject,
        exam_markdown=text,
        first_page_check=first_page.model_dump(mode="json"),
        syllabus_context=_syllabus_context(syllabus),
    )
    artifact: dict[str, Any] = {
        "strategy": "llm_exam_extraction",
        "prompt": prompt,
        "raw_response": None,
        "parsed_extraction": None,
        "fallback_used": False,
        "fallback_reason": None,
    }

    try:
        if model_client.provider == "mock" and model_client.mock_json_response is None:
            exam = _fallback_exam(markdown_path, pdf_path, first_page, fallback_subject)
            artifact.update(
                {
                    "raw_response": "mock",
                    "parsed_extraction": exam.model_dump(mode="json"),
                    "strategy": "mock_llm_exam_extraction",
                }
            )
            return exam, artifact

        raw = model_client.complete_json(prompt)
        artifact["raw_response"] = model_client.last_raw_response
        raw.pop("_raw_response", None)
        raw.setdefault("raw_pdf_path", str(pdf_path))
        raw.setdefault("markdown_path", str(markdown_path))
        exam = ExamPaper(**raw)
        _validate_llm_exam(exam, require_source_page_numbers=True)
        artifact["parsed_extraction"] = exam.model_dump(mode="json")
        return exam, artifact
    except Exception as exc:
        fallback = _fallback_exam(markdown_path, pdf_path, first_page, fallback_subject)
        issue = ValidationIssue(
            code="llm_exam_extraction_fallback",
            severity="WARNING",
            stage="exam_extraction",
            message="LLM exam extraction was rejected; regex extraction was used instead.",
            reason=str(exc),
        )
        fallback.issues.append(issue)
        artifact.update(
            {
                "raw_response": model_client.last_raw_response,
                "fallback_used": True,
                "fallback_reason": str(exc),
                "fallback_extraction": fallback.model_dump(mode="json"),
            }
        )
        return fallback, artifact


def _validate_llm_exam(exam: ExamPaper, require_source_page_numbers: bool = False) -> None:
    if not exam.questions:
        raise ValueError("LLM extraction did not return any questions.")
    if exam.total_marks is None:
        raise ValueError("LLM extraction did not return total candidate marks.")
    for question in exam.questions:
        if not question.question_id or not question.section:
            raise ValueError("LLM extraction returned a question without id or section.")
        if question.marks is None:
            raise ValueError(f"LLM extraction returned question {question.question_id} without marks.")
    if require_source_page_numbers:
        missing = [source.source_id for source in exam.sources if source.page_number is None]
        if missing:
            raise ValueError(f"LLM extraction returned sources without page numbers: {', '.join(missing)}")


def _syllabus_context(syllabus: SyllabusDocument) -> dict[str, Any]:
    return {
        "subject": syllabus.subject,
        "subject_code": syllabus.subject_code,
        "year": syllabus.year,
        "components": [component.model_dump(mode="json") for component in syllabus.components],
        "objectives": [objective.model_dump(mode="json") for objective in syllabus.objectives],
        "topics": [topic.model_dump(mode="json") for topic in syllabus.topics],
    }


def _fallback_exam(markdown_path: Path, pdf_path: Path, first_page: FirstPageCheck, fallback_subject: str) -> ExamPaper:
    if fallback_subject.lower() == "history":
        return extract_history_exam(markdown_path, pdf_path, first_page)
    return extract_generic_exam(markdown_path, pdf_path, first_page)


def extract_generic_exam(markdown_path: Path, pdf_path: Path, first_page: FirstPageCheck) -> ExamPaper:
    text = markdown_path.read_text(encoding="utf-8")
    questions = []
    page_number: int | None = None
    section = "Main"
    import re

    for raw_line in text.splitlines():
        line = raw_line.strip()
        page_match = re.match(r"## Page\s+(\d+)", line)
        if page_match:
            page_number = int(page_match.group(1))
            continue
        section_match = re.match(r"^(Section|Part)\s+([A-Z0-9]+)", line, re.I)
        if section_match:
            section = section_match.group(0)
            continue
        question_match = re.match(r"^(\d+[.)]?|\([a-z]\))\s+(.+?)\s*\[(\d+)\]\s*$", line)
        if question_match:
            qid, prompt, marks = question_match.groups()
            questions.append(
                {
                    "question_id": qid.rstrip("."),
                    "section": section,
                    "prompt": prompt,
                    "marks": int(marks),
                    "page_number": page_number,
                }
            )

    from backend.app.schemas.base import ValidationIssue
    from backend.app.schemas.exam import ExamQuestion

    issues = []
    if not first_page.is_exam_paper:
        issues.append(ValidationIssue(code="first_page_not_exam", severity="ERROR", stage="first_page_check", message="First page was not classified as an exam-paper cover.", evidence=first_page.model_dump()))
    if not questions:
        issues.append(ValidationIssue(code="generic_extraction_low_recall", severity="WARNING", stage="exam_extraction", message="Generic regex extraction found no bracket-mark questions; use LLM extraction for this subject."))

    parsed_questions = [ExamQuestion(**question) for question in questions]
    return ExamPaper(
        subject=first_page.subject,
        paper_code=first_page.paper_code,
        paper_title=first_page.paper_title or "Exam paper",
        exam_year=first_page.exam_year,
        total_marks=sum(question.marks or 0 for question in parsed_questions) or None,
        raw_pdf_path=str(pdf_path),
        markdown_path=str(markdown_path),
        questions=parsed_questions,
        sources=[],
        issues=issues,
    )
