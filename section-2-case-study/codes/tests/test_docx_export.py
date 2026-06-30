from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from backend.app.src.reporting.docx_export import report_to_docx


def test_report_to_docx_generates_word_package() -> None:
    docx_bytes = report_to_docx(
        {
            "job_id": "test-job",
            "summary_findings": ["Paper structure matches the syllabus baseline."],
            "exam_paper": {
                "subject": "History",
                "paper_code": "2174/01",
                "paper_title": "Paper 1",
                "exam_year": 2026,
                "duration_minutes": 90,
                "total_marks": 50,
                "questions": [
                    {
                        "question_id": "1a",
                        "section": "A",
                        "prompt": "Study Source A.",
                        "marks": 5,
                        "choice_group": None,
                        "page_number": 2,
                    }
                ],
                "sources": [{"source_id": "A", "source_type": "text", "text": "A source", "page_number": 2}],
            },
            "syllabus": {"subject": "History", "subject_code": "2174", "year": 2026, "source_url": "local"},
            "rule_checks": [{"rule_id": "marks", "expected": "50", "observed": "50", "passed": True}],
            "topic_weightage": [{"topic": "Cold War", "required_marks": 30, "offered_marks": 30}],
            "annotations": [
                {
                    "question_id": "1a",
                    "predicted_objectives": ["AO1"],
                    "predicted_topic": "Cold War",
                    "evidence_page_numbers": [2],
                    "evidence_from_question": "Study Source A.",
                    "evidence_from_syllabus": "Source-based case study.",
                    "ambiguity_notes": [],
                }
            ],
            "issues": [],
        }
    )

    assert docx_bytes.startswith(b"PK")
    with ZipFile(BytesIO(docx_bytes)) as docx:
        assert "word/document.xml" in docx.namelist()
        document = docx.read("word/document.xml").decode("utf-8")
    assert "History 2174/01 Alignment Report" in document
    assert "Extracted Questions" in document
    assert "Study Source A." in document
