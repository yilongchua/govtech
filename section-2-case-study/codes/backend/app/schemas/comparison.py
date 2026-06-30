from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel

from backend.app.schemas.base import PipelineBaseModel
from backend.app.schemas.exam import ExamPaper
from backend.app.schemas.syllabus import SyllabusDocument


class QuestionAnnotation(BaseModel):
    question_id: str
    predicted_objectives: list[str]
    predicted_topic: str
    syllabus_topic_id: Optional[str] = None
    evidence_from_question: str
    evidence_from_syllabus: str
    evidence_page_numbers: list[int] = []
    ambiguity_notes: list[str] = []


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
    candidate_experienced_notes: Optional[str] = None


class StructureMetric(BaseModel):
    label: str
    value: Optional[Union[str, int, float]] = None


class ComparisonReport(PipelineBaseModel):
    job_id: str
    syllabus: SyllabusDocument
    exam_paper: ExamPaper
    rule_checks: list[RuleCheckResult]
    annotations: list[QuestionAnnotation]
    topic_weightage: list[TopicWeightage]
    structure_metrics: list[StructureMetric] = []
    download_filename_base: str = "exam-alignment"
    summary_findings: list[str]
    chart_payloads: dict


class ModelOutputEvaluation(PipelineBaseModel):
    extraction_consistency_score: float
    annotation_grounding_score: float
    topic_weightage_score: float
    issues_found: list[str] = []
    unsupported_claims: list[str] = []
    recommended_human_review: bool = True
