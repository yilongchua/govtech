from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from backend.app.schemas.base import ValidationIssue


def validate_pdf_file(pdf_path: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if pdf_path.suffix.lower() != ".pdf":
        issues.append(
            ValidationIssue(
                code="not_pdf_extension",
                severity="ERROR",
                stage="pdf_guard",
                message="Uploaded file is not a PDF.",
                reason=f"Extension was {pdf_path.suffix}",
            )
        )
        return issues
    try:
        reader = PdfReader(str(pdf_path))
        if len(reader.pages) < 1:
            issues.append(
                ValidationIssue(
                    code="empty_pdf",
                    severity="ERROR",
                    stage="pdf_guard",
                    message="PDF has no pages.",
                )
            )
    except Exception as exc:
        issues.append(
            ValidationIssue(
                code="unreadable_pdf",
                severity="ERROR",
                stage="pdf_guard",
                message="PDF could not be parsed.",
                reason=str(exc),
            )
        )
    return issues
