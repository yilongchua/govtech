from backend.app.schemas.exam import ExamQuestion, SourceItem
from backend.app.schemas.syllabus import AssessmentComponent, AssessmentObjective, SyllabusDocument, SyllabusTopic
from backend.app.src.comparison.semantic_matcher import annotate_question


class CapturingClient:
    provider = "openai-compatible"

    def __init__(self) -> None:
        self.last_prompt = ""

    def complete_json(self, prompt: str):
        self.last_prompt = prompt
        return {
            "question_id": "1(a)",
            "predicted_objectives": ["AO1", "AO3"],
            "predicted_topic": "Key developments leading to the outbreak of World War II in Europe",
            "syllabus_topic_id": "p1_wwii_europe",
            "evidence_from_question": "shared case study sources",
            "evidence_from_syllabus": "source-based case study topic",
            "evidence_page_numbers": [2, 3],
        }


def test_model_mapping_receives_parent_question_context_for_source_case_study() -> None:
    syllabus = SyllabusDocument(
        subject="History",
        subject_code="2174",
        year=2026,
        source_url="local",
        pdf_path="syllabus.pdf",
        markdown_path="syllabus.md",
        objectives=[
            AssessmentObjective(ao_id="AO1", name="Deploy Knowledge", description="Use knowledge."),
            AssessmentObjective(ao_id="AO3", name="Evaluate Sources", description="Evaluate sources."),
        ],
        components=[
            AssessmentComponent(
                paper="2174/01",
                section="A",
                name="Source-Based Case Study",
                marks=30,
                objectives=["AO1", "AO3"],
            )
        ],
        topics=[
            SyllabusTopic(
                topic_id="p1_wwii_europe",
                paper="2174/01",
                unit="War in Europe",
                topic="Key developments leading to the outbreak of World War II in Europe",
                is_source_based_eligible=True,
            )
        ],
    )
    questions = [
        ExamQuestion(
            question_id="1(a)",
            section="A",
            prompt="How useful is Source A as evidence of Hitler's foreign policy ambitions?",
            marks=5,
            required_sources=["A"],
            page_number=2,
        ),
        ExamQuestion(
            question_id="1(b)",
            section="A",
            prompt="Why do you think Rothermere wrote this letter?",
            marks=5,
            required_sources=["B"],
            page_number=2,
        ),
    ]
    sources = [
        SourceItem(
            source_id="A",
            attribution="A speech by Hitler about German expansion.",
            text="The source refers to German foreign policy in Europe.",
            page_number=2,
        ),
        SourceItem(
            source_id="B",
            attribution="A letter about appeasement.",
            text="The source refers to Chamberlain and the Munich Agreement.",
            page_number=3,
        ),
    ]
    client = CapturingClient()

    annotation = annotate_question(questions[0], syllabus, "2174/01", client, sources, questions)

    assert annotation.predicted_topic == "Key developments leading to the outbreak of World War II in Europe"
    assert '"parent_question_id": "1"' in client.last_prompt
    assert '"question_id": "1(b)"' in client.last_prompt
    assert '"shared_sources"' in client.last_prompt
    assert "Munich Agreement" in client.last_prompt
