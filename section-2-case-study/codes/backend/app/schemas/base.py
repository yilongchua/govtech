from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    code: str
    severity: Literal["INFO", "WARNING", "ERROR"]
    stage: str
    message: str
    reason: Optional[str] = None
    evidence: dict = Field(default_factory=dict)
    recoverable: bool = True


class PipelineBaseModel(BaseModel):
    issues: list[ValidationIssue] = Field(default_factory=list)

    def add_issue(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)
