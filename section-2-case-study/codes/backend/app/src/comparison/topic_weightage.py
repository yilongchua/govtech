from __future__ import annotations

from collections import defaultdict

from backend.app.schemas.comparison import QuestionAnnotation, TopicWeightage
from backend.app.schemas.exam import ExamPaper


def calculate_topic_weightage(exam: ExamPaper, annotations: list[QuestionAnnotation]) -> list[TopicWeightage]:
    by_qid = {a.question_id: a for a in annotations}
    required = defaultdict(int)
    offered = defaultdict(int)
    choice_group_topic_marks: dict[tuple[str, str], int] = {}
    for q in exam.questions:
        annotation = by_qid.get(q.question_id)
        if not annotation or q.marks is None:
            continue
        topic = annotation.predicted_topic
        if _is_compulsory_question(exam, q):
            required[topic] += q.marks
            offered[topic] += q.marks
        else:
            if q.choice_group:
                key = (q.choice_group, topic)
                choice_group_topic_marks[key] = max(choice_group_topic_marks.get(key, 0), q.marks)
            else:
                offered[topic] += q.marks
    for (_, topic), marks in choice_group_topic_marks.items():
        offered[topic] += marks
    topics = sorted(set(required) | set(offered))
    return [
        TopicWeightage(
            topic=topic,
            required_marks=required[topic],
            offered_marks=offered[topic],
            candidate_experienced_notes=_candidate_notes(exam),
        )
        for topic in topics
    ]


def _is_compulsory_question(exam: ExamPaper, question) -> bool:
    if (exam.subject or "").lower() == "history":
        return question.section == "A"
    return question.choice_group is None


def _candidate_notes(exam: ExamPaper) -> str:
    if (exam.subject or "").lower() == "history":
        return "Section A is compulsory; Section B is offered as choices, so not all offered marks are experienced by one candidate."
    return "Required marks are counted for non-choice questions; offered marks include configured choice alternatives where present."
