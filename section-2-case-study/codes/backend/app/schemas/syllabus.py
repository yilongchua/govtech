from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from backend.app.schemas.base import PipelineBaseModel


class AssessmentObjective(BaseModel):
    ao_id: str
    name: str
    description: str
    skills: list[str] = []
    source_page: Optional[int] = None


class SyllabusTopic(BaseModel):
    topic_id: str
    paper: str
    unit: str
    topic: str
    subtopics: list[str] = []
    key_concepts: list[str] = []
    is_source_based_eligible: bool = False
    source_page: Optional[int] = None


class AssessmentComponent(BaseModel):
    paper: str
    section: str
    name: str
    marks: int
    weighting_percent: Optional[float] = None
    objectives: list[str]
    rules: list[str] = []
    source_page: Optional[int] = None


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
