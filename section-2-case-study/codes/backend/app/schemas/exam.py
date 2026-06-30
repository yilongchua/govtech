from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from backend.app.schemas.base import PipelineBaseModel


class SourceItem(BaseModel):
    source_id: str
    source_type: str = "text"
    text: Optional[str] = None
    image_path: Optional[str] = None
    attribution: Optional[str] = None
    date: Optional[str] = None
    page_number: Optional[int] = None


class ImageSourceInterpretation(BaseModel):
    source_id: str
    source_type: str = "image"
    text: str
    confidence: Optional[str] = None
    visible_text: list[str] = []
    reasoning: list[str] = []


class ExamQuestion(BaseModel):
    question_id: str
    section: str
    prompt: str
    marks: Optional[int] = None
    required_sources: list[str] = []
    choice_group: Optional[str] = None
    page_number: Optional[int] = None


class FirstPageCheck(BaseModel):
    is_exam_paper: bool
    subject: Optional[str] = None
    paper_code: Optional[str] = None
    paper_title: Optional[str] = None
    exam_year: Optional[int] = None
    reasons: list[str] = []


class ExamPaper(PipelineBaseModel):
    subject: Optional[str] = None
    paper_code: Optional[str] = None
    paper_title: Optional[str] = None
    exam_year: Optional[int] = None
    duration_minutes: Optional[int] = None
    total_marks: Optional[int] = None
    raw_pdf_path: str
    markdown_path: str
    sources: list[SourceItem] = []
    questions: list[ExamQuestion] = []
