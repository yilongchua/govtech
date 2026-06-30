from __future__ import annotations

from backend.app.schemas.comparison import QuestionAnnotation, TopicWeightage
from backend.app.schemas.exam import ExamPaper


def build_chart_payloads(exam: ExamPaper, annotations: list[QuestionAnnotation], topic_weightage: list[TopicWeightage]) -> dict:
    section_marks = {}
    for question in exam.questions:
        section_marks[question.section] = section_marks.get(question.section, 0) + (question.marks or 0)
    return {
        "marks_by_section": [{"section": section, "marks": marks} for section, marks in sorted(section_marks.items())],
        "topic_weightage": [item.model_dump() for item in topic_weightage],
        "objective_heatmap": [item.model_dump() for item in annotations],
    }
