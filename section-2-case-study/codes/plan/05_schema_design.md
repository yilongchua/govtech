# 05 - Schema Design

Use Pydantic models for every pipeline boundary. The main principle: schemas should accumulate validation issues and reasons instead of throwing away imperfect documents.

## Base Issue Schema

```python
from pydantic import BaseModel, Field
from typing import Literal

class ValidationIssue(BaseModel):
    code: str
    severity: Literal["INFO", "WARNING", "ERROR"]
    stage: str
    message: str
    reason: str | None = None
    evidence: dict = Field(default_factory=dict)
    recoverable: bool = True
```

## Base Pipeline Model

```python
class PipelineBaseModel(BaseModel):
    issues: list[ValidationIssue] = Field(default_factory=list)

    def add_issue(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)
```

## Syllabus Schema

```python
class AssessmentObjective(BaseModel):
    ao_id: str
    name: str
    description: str
    skills: list[str] = []
    source_page: int | None = None

class SyllabusTopic(BaseModel):
    paper: str
    unit: str
    topic: str
    subtopics: list[str] = []
    key_concepts: list[str] = []
    is_source_based_eligible: bool = False
    source_page: int | None = None

class AssessmentComponent(BaseModel):
    paper: str
    section: str
    name: str
    marks: int
    weighting_percent: float | None = None
    objectives: list[str]
    rules: list[str] = []

class SyllabusDocument(PipelineBaseModel):
    subject: str
    subject_code: str
    year: int
    source_url: str
    pdf_path: str
    markdown_path: str
    objectives: list[AssessmentObjective]
    components: list[AssessmentComponent]
    topics: list[SyllabusTopic]
```

## Exam Paper Schema

```python
class SourceItem(BaseModel):
    source_id: str
    source_type: str
    text: str | None = None
    image_path: str | None = None
    attribution: str | None = None
    date: str | None = None
    page_number: int | None = None

class ExamQuestion(BaseModel):
    question_id: str
    section: str
    prompt: str
    marks: int | None = None
    required_sources: list[str] = []
    choice_group: str | None = None
    page_number: int | None = None

class ExamPaper(PipelineBaseModel):
    subject: str | None = None
    paper_code: str | None = None
    paper_title: str | None = None
    exam_year: int | None = None
    duration_minutes: int | None = None
    total_marks: int | None = None
    raw_pdf_path: str
    markdown_path: str
    sources: list[SourceItem]
    questions: list[ExamQuestion]
```

## Extraction Output Format

The extraction prompt should return JSON in this shape:

```json
{
  "subject": "History",
  "paper_code": "2174/01",
  "paper_title": "Paper 1 Extension of European control in Southeast Asia and challenges to European dominance, 1870s-1942",
  "exam_year": 2024,
  "duration_minutes": 110,
  "total_marks": 50,
  "sources": [
    {
      "source_id": "A",
      "source_type": "speech",
      "text": "...",
      "attribution": "A speech made by Hitler...",
      "date": "26 September 1938",
      "page_number": 3
    }
  ],
  "questions": [
    {
      "question_id": "1(a)",
      "section": "A",
      "prompt": "How useful is this source as evidence of Hitler's foreign policy ambitions?",
      "marks": 6,
      "required_sources": ["A"],
      "choice_group": null,
      "page_number": 2
    }
  ],
  "issues": []
}
```

## AI Annotation Schema

```python
class QuestionAnnotation(BaseModel):
    question_id: str
    predicted_objectives: list[str]
    predicted_topic: str
    syllabus_topic_id: str | None = None
    evidence_from_question: str
    evidence_from_syllabus: str
    confidence: float
    ambiguity_notes: list[str] = []
```

## Comparison Report Schema

```python
class RuleCheckResult(BaseModel):
    rule_id: str
    expected: str
    observed: str
    passed: bool
    severity_if_failed: str

class TopicWeightage(BaseModel):
    topic: str
    required_marks: int
    offered_marks: int
    candidate_experienced_notes: str | None = None

class ComparisonReport(PipelineBaseModel):
    job_id: str
    syllabus: SyllabusDocument
    exam_paper: ExamPaper
    rule_checks: list[RuleCheckResult]
    annotations: list[QuestionAnnotation]
    topic_weightage: list[TopicWeightage]
    summary_findings: list[str]
    chart_payloads: dict
```

## Rule Config In Schema

Instead of hard-coding all validation, use a schema-backed config:

```json
{
  "paper_code": "2174/01",
  "rules": [
    {
      "rule_id": "paper_1_total_marks",
      "description": "Paper 1 should total 50 marks",
      "field": "total_marks",
      "operator": "equals",
      "value": 50,
      "severity_if_failed": "ERROR"
    }
  ]
}
```

