from __future__ import annotations

import re

from backend.app.schemas.comparison import QuestionAnnotation
from backend.app.schemas.exam import ExamQuestion, SourceItem
from backend.app.schemas.syllabus import SyllabusDocument, SyllabusTopic
from backend.app.src.ingestion.model_client import LLMClient
from backend.app.src.prompts import render_prompt


def annotate_question(
    question: ExamQuestion,
    syllabus: SyllabusDocument,
    paper_code: str | None = None,
    model_client: LLMClient | None = None,
    sources: list[SourceItem] | None = None,
    all_questions: list[ExamQuestion] | None = None,
) -> QuestionAnnotation:
    if model_client is not None and model_client.provider != "mock":
        llm_annotation = _annotate_question_with_llm(
            question,
            syllabus,
            model_client,
            sources or [],
            all_questions or [],
        )
        if llm_annotation is not None:
            return llm_annotation
    fallback_annotation = _annotate_question_with_rules(question, syllabus, paper_code, sources or [])
    if fallback_annotation is not None:
        return fallback_annotation
    return _uncertain_annotation(question, sources or [], "No reliable syllabus-topic mapping was available.")


def _annotate_question_with_llm(
    question: ExamQuestion,
    syllabus: SyllabusDocument,
    model_client: LLMClient,
    sources: list[SourceItem],
    all_questions: list[ExamQuestion],
) -> QuestionAnnotation | None:
    prompt = render_prompt(
        "map_question_to_syllabus.j2",
        QuestionAnnotation,
        question_json=question.model_dump(mode="json"),
        question_context_json=_parent_question_context(question, all_questions, sources),
        syllabus_candidates_json=[topic.model_dump(mode="json") for topic in syllabus.topics],
    )
    try:
        raw = model_client.complete_json(prompt)
        raw.pop("_raw_response", None)
        raw.setdefault("question_id", question.question_id)
        raw.setdefault("evidence_page_numbers", _trace_pages(question, sources))
        annotation = QuestionAnnotation(**raw)
        if not annotation.evidence_page_numbers:
            annotation.evidence_page_numbers = _trace_pages(question, sources)
        _validate_annotation(annotation, syllabus)
        return annotation
    except Exception:
        return None


def _annotate_question_with_rules(
    question: ExamQuestion,
    syllabus: SyllabusDocument,
    paper_code: str | None,
    sources: list[SourceItem],
) -> QuestionAnnotation | None:
    objectives = _objectives_for_question(question, syllabus, paper_code)
    topic = _best_topic_for_question(question, syllabus, paper_code, sources)
    if not objectives and topic is None:
        return None
    return QuestionAnnotation(
        question_id=question.question_id,
        predicted_objectives=objectives,
        predicted_topic=topic.topic if topic else "Uncertain",
        syllabus_topic_id=topic.topic_id if topic else None,
        evidence_from_question=question.prompt[:240],
        evidence_from_syllabus=topic.topic if topic else "No syllabus topic was selected.",
        evidence_page_numbers=_trace_pages(question, sources),
        ambiguity_notes=["Rule-based fallback used because model-backed syllabus mapping was unavailable or invalid."],
    )


def _parent_question_context(question: ExamQuestion, all_questions: list[ExamQuestion], sources: list[SourceItem]) -> dict:
    parent_id = _parent_question_id(question.question_id)
    required_source_ids = set(question.required_sources)
    sibling_questions = [
        item
        for item in all_questions
        if _parent_question_id(item.question_id) == parent_id and item.question_id != question.question_id
    ]
    if question.section == "A":
        context_sources = sources
    else:
        context_sources = [source for source in sources if source.source_id in required_source_ids]
    return {
        "parent_question_id": parent_id,
        "parent_question_note": "Sub-questions with the same parent id form one larger question/case study.",
        "sibling_subquestions": [
            {
                "question_id": item.question_id,
                "section": item.section,
                "prompt": item.prompt,
                "marks": item.marks,
                "required_sources": item.required_sources,
                "page_number": item.page_number,
            }
            for item in sibling_questions
        ],
        "shared_sources": [
            {
                "source_id": source.source_id,
                "source_type": source.source_type,
                "attribution": source.attribution,
                "date": source.date,
                "text_excerpt": (source.text or "")[:600],
                "page_number": source.page_number,
            }
            for source in context_sources
        ],
    }


def _parent_question_id(question_id: str) -> str:
    match = re.match(r"^(\d+)\([a-z]\)$", question_id.strip(), re.I)
    return match.group(1) if match else question_id.strip()


def _objectives_for_question(question: ExamQuestion, syllabus: SyllabusDocument, paper_code: str | None) -> list[str]:
    for component in syllabus.components:
        if _same_paper(component.paper, paper_code) and component.section == question.section:
            return component.objectives
    if question.section == "A" and question.required_sources:
        return _known_objectives(syllabus, ["AO1", "AO3"])
    if question.section == "B":
        return _known_objectives(syllabus, ["AO1", "AO2"])
    return []


def _best_topic_for_question(
    question: ExamQuestion,
    syllabus: SyllabusDocument,
    paper_code: str | None,
    sources: list[SourceItem],
) -> SyllabusTopic | None:
    candidates = [topic for topic in syllabus.topics if _same_paper(topic.paper, paper_code)]
    if not candidates:
        candidates = syllabus.topics
    if question.section == "A":
        eligible = [topic for topic in candidates if topic.is_source_based_eligible]
        if eligible:
            candidates = eligible
    if not candidates:
        return None
    evidence_text = _topic_evidence_text(question, sources)
    scored = [(_topic_score(evidence_text, topic), topic) for topic in candidates]
    best_score, best_topic = max(scored, key=lambda item: item[0])
    if best_score <= 0:
        return None
    return best_topic


def _topic_evidence_text(question: ExamQuestion, sources: list[SourceItem]) -> str:
    linked_source_ids = set(question.required_sources)
    if question.section == "A":
        linked_source_ids = {source.source_id for source in sources}
    source_text = " ".join(
        " ".join(filter(None, [source.attribution, source.text, source.date]))
        for source in sources
        if source.source_id in linked_source_ids
    )
    return f"{question.prompt} {source_text}".lower()


def _topic_score(evidence_text: str, topic: SyllabusTopic) -> int:
    score = 0
    weighted_phrases = [topic.topic, topic.unit, *topic.subtopics, *topic.key_concepts]
    for phrase in weighted_phrases:
        normalised = _normalise_text(phrase)
        if not normalised:
            continue
        if normalised in evidence_text:
            score += 8 + len(normalised.split())
            continue
        tokens = [token for token in _tokens(normalised) if len(token) > 3]
        score += sum(2 for token in tokens if token in evidence_text)
    return score


def _same_paper(topic_paper: str | None, paper_code: str | None) -> bool:
    if not topic_paper or not paper_code:
        return True
    return topic_paper.strip() == paper_code.strip()


def _known_objectives(syllabus: SyllabusDocument, objective_ids: list[str]) -> list[str]:
    supported = {objective.ao_id for objective in syllabus.objectives}
    return [objective_id for objective_id in objective_ids if objective_id in supported]


def _normalise_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _validate_annotation(annotation: QuestionAnnotation, syllabus: SyllabusDocument) -> None:
    topic_ids = {topic.topic_id for topic in syllabus.topics}
    objective_ids = {objective.ao_id for objective in syllabus.objectives}
    if annotation.syllabus_topic_id and annotation.syllabus_topic_id not in topic_ids:
        raise ValueError(f"Annotation returned unsupported topic id: {annotation.syllabus_topic_id}")
    unsupported_objectives = [objective for objective in annotation.predicted_objectives if objective not in objective_ids]
    if unsupported_objectives:
        raise ValueError(f"Annotation returned unsupported objective ids: {', '.join(unsupported_objectives)}")


def _uncertain_annotation(question: ExamQuestion, sources: list[SourceItem], reason: str) -> QuestionAnnotation:
    return QuestionAnnotation(
        question_id=question.question_id,
        predicted_objectives=[],
        predicted_topic="Uncertain",
        syllabus_topic_id=None,
        evidence_from_question=question.prompt[:240],
        evidence_from_syllabus="No syllabus topic was selected.",
        evidence_page_numbers=_trace_pages(question, sources),
        ambiguity_notes=[reason],
    )


def _trace_pages(question: ExamQuestion, sources: list[SourceItem]) -> list[int]:
    pages = set()
    if question.page_number is not None:
        pages.add(question.page_number)
    required = set(question.required_sources)
    for source in sources:
        if source.source_id in required and source.page_number is not None:
            pages.add(source.page_number)
    return sorted(pages)
