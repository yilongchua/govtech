from backend.app.schemas.comparison import QuestionAnnotation
from backend.app.schemas.exam import ExamPaper, ExamQuestion
from backend.app.src.comparison.topic_weightage import calculate_topic_weightage


def annotation(question_id: str, topic: str) -> QuestionAnnotation:
    return QuestionAnnotation(
        question_id=question_id,
        predicted_objectives=["AO1", "AO2"],
        predicted_topic=topic,
        evidence_from_question="prompt",
        evidence_from_syllabus="syllabus",
        evidence_page_numbers=[1],
    )


def test_choice_group_counts_max_marks_for_topic() -> None:
    exam = ExamPaper(
        raw_pdf_path="paper.pdf",
        markdown_path="paper.md",
        questions=[
            ExamQuestion(question_id="2(a)", section="B", prompt="A", marks=10, choice_group="2_either_or"),
            ExamQuestion(question_id="2(b)", section="B", prompt="B", marks=10, choice_group="2_either_or"),
        ],
    )
    result = calculate_topic_weightage(
        exam,
        [
            annotation("2(a)", "Colonial Southeast Asia"),
            annotation("2(b)", "Colonial Southeast Asia"),
        ],
    )
    assert result[0].offered_marks == 10
