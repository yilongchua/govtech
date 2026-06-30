from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def report_to_docx(report: dict) -> bytes:
    document = _document_xml(_report_blocks(report))
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", _content_types_xml())
        docx.writestr("_rels/.rels", _package_relationships_xml())
        docx.writestr("word/_rels/document.xml.rels", _document_relationships_xml())
        docx.writestr("word/styles.xml", _styles_xml())
        docx.writestr("word/document.xml", document)
    return buffer.getvalue()


def _report_blocks(report: dict) -> list[str]:
    paper = report.get("exam_paper", {})
    syllabus = report.get("syllabus", {})
    issues = report.get("issues", [])
    checks_requiring_attention = [check for check in report.get("rule_checks", []) if not check.get("passed")]
    title_subject = syllabus.get("subject") or paper.get("subject") or "Exam"

    blocks = [
        _heading(f"{title_subject} {paper.get('paper_code') or 'Exam Paper'} Alignment Report", 1),
        _paragraph(f"Job ID: {_text(report.get('job_id'))}"),
        _heading("Summary Findings", 2),
    ]

    findings = report.get("summary_findings", [])
    if findings:
        blocks.extend(_bullet(item) for item in findings)
    else:
        blocks.append(_paragraph("No summary findings recorded."))

    blocks.extend(
        [
            _heading("Document Summary", 2),
            _table(
                ["Field", "Value"],
                [[label, _text(paper.get(key))] for label, key in [
                    ("Subject", "subject"),
                    ("Paper code", "paper_code"),
                    ("Paper title", "paper_title"),
                    ("Exam year", "exam_year"),
                    ("Duration minutes", "duration_minutes"),
                    ("Total marks", "total_marks"),
                ]],
            ),
            _heading("Syllabus Baseline", 2),
            _table(
                ["Field", "Value"],
                [[label, _text(syllabus.get(key))] for label, key in [
                    ("Subject", "subject"),
                    ("Subject code", "subject_code"),
                    ("Year", "year"),
                    ("Source URL", "source_url"),
                ]],
            ),
            _heading("Extracted Paper Structure", 2),
            _table(
                ["Field", "Extracted value"],
                [
                    [_text(item.get("label")), _text(item.get("value"))]
                    for item in _structure_metrics(report)
                ],
            ),
            _heading("Checks Requiring Attention", 2),
            (
                _table(
                    ["Rule", "Expected", "Observed", "Status"],
                    [
                        [
                            _text(check.get("rule_id")),
                            _text(check.get("expected")),
                            _text(check.get("observed")),
                            "Review",
                        ]
                        for check in checks_requiring_attention
                    ],
                )
                if checks_requiring_attention
                else _paragraph("No structural checks require review.")
            ),
            _heading("Topic Weightage", 2),
            _table(
                ["Topic", "Required marks", "Offered marks", "Notes"],
                [
                    [
                        _text(item.get("topic")),
                        _text(item.get("required_marks")),
                        _text(item.get("offered_marks")),
                        _text(item.get("candidate_experienced_notes")),
                    ]
                    for item in report.get("topic_weightage", [])
                ],
            ),
            _heading("Objective Alignment", 2),
            _table(
                ["Question", "Objectives", "Topic", "Evidence pages", "Evidence", "Notes"],
                [
                    [
                        _text(item.get("question_id")),
                        ", ".join(item.get("predicted_objectives", [])),
                        _text(item.get("predicted_topic")),
                        ", ".join(str(page) for page in item.get("evidence_page_numbers", [])),
                        _join_text([item.get("evidence_from_question"), item.get("evidence_from_syllabus")]),
                        _join_text(item.get("ambiguity_notes", [])),
                    ]
                    for item in report.get("annotations", [])
                ],
            ),
            _heading("Extracted Questions", 2),
            _table(
                ["Question", "Section", "Prompt", "Marks", "Choice group", "Page"],
                [
                    [
                        _text(item.get("question_id")),
                        _text(item.get("section")),
                        _text(item.get("prompt")),
                        _text(item.get("marks")),
                        _text(item.get("choice_group")),
                        _text(item.get("page_number")),
                    ]
                    for item in paper.get("questions", [])
                ],
            ),
            _heading("Extracted Sources", 2),
            _table(
                ["Source", "Type", "Text", "Attribution", "Date", "Page"],
                [
                    [
                        _text(item.get("source_id")),
                        _text(item.get("source_type")),
                        _text(item.get("text") or item.get("image_path")),
                        _text(item.get("attribution")),
                        _text(item.get("date")),
                        _text(item.get("page_number")),
                    ]
                    for item in paper.get("sources", [])
                ],
            ),
            _heading("Warnings And Errors", 2),
        ]
    )

    if issues:
        blocks.append(
            _table(
                ["Severity", "Code", "Message", "Reason"],
                [
                    [
                        _text(issue.get("severity")),
                        _text(issue.get("code")),
                        _text(issue.get("message")),
                        _text(issue.get("reason")),
                    ]
                    for issue in issues
                ],
            )
        )
    else:
        blocks.append(_paragraph("No issues recorded."))

    return blocks


def _sum_section_marks(questions: list[dict], section: str) -> int:
    return sum(item.get("marks") or 0 for item in questions if item.get("section") == section)


def _effective_offered_marks(questions: list[dict]) -> int:
    total = 0
    grouped: dict[str, int] = {}
    for question in questions:
        marks = question.get("marks") or 0
        choice_group = question.get("choice_group")
        if choice_group:
            grouped[choice_group] = max(grouped.get(choice_group, 0), marks)
        else:
            total += marks
    return total + sum(grouped.values())


def _structure_metrics(report: dict) -> list[dict]:
    paper = report.get("exam_paper", {})
    return report.get("structure_metrics") or [
        {"label": "Subject", "value": paper.get("subject") or "Unknown"},
        {"label": "Total marks", "value": paper.get("total_marks")},
        {"label": "Question count", "value": len(paper.get("questions", []))},
        {"label": "Source count", "value": len(paper.get("sources", []))},
    ]


def _document_xml(blocks: list[str]) -> str:
    body = "".join(blocks)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}"
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1080" '
        'w:bottom="1440" w:left="1080" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
        "</w:body></w:document>"
    )


def _heading(text: object, level: int) -> str:
    size = "32" if level == 1 else "24"
    return (
        "<w:p><w:pPr><w:spacing w:after=\"160\"/></w:pPr><w:r><w:rPr>"
        f'<w:b/><w:sz w:val="{size}"/></w:rPr><w:t>{_xml(text)}</w:t></w:r></w:p>'
    )


def _paragraph(text: object) -> str:
    return f"<w:p><w:r><w:t>{_xml(text)}</w:t></w:r></w:p>"


def _bullet(text: object) -> str:
    return _paragraph(f"- {_text(text)}")


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return _paragraph("No records.")
    table = [
        "<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/><w:tblBorders>"
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="d9e2ec"/>'
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="d9e2ec"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="d9e2ec"/>'
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="d9e2ec"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="d9e2ec"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="d9e2ec"/>'
        "</w:tblBorders></w:tblPr>",
        _row(headers, header=True),
    ]
    table.extend(_row(row) for row in rows)
    table.append("</w:tbl>")
    return "".join(table)


def _row(cells: list[str], header: bool = False) -> str:
    return "<w:tr>" + "".join(_cell(cell, header) for cell in cells) + "</w:tr>"


def _cell(text: object, header: bool = False) -> str:
    shading = '<w:shd w:fill="f8fafc"/>' if header else ""
    bold = "<w:b/>" if header else ""
    return (
        "<w:tc><w:tcPr>"
        f"{shading}<w:tcMar><w:top w:w=\"90\" w:type=\"dxa\"/><w:left w:w=\"90\" w:type=\"dxa\"/>"
        '<w:bottom w:w="90" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tcMar>'
        f"</w:tcPr><w:p><w:r><w:rPr>{bold}</w:rPr><w:t>{_xml(text)}</w:t></w:r></w:p></w:tc>"
    )


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _join_text(value: object) -> str:
    if isinstance(value, list):
        return "; ".join(_text(item) for item in value if _text(item))
    return _text(value)


def _xml(value: object) -> str:
    return escape(_text(value), {'"': "&quot;"})


def _content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""


def _package_relationships_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""


def _document_relationships_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def _styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="21"/></w:rPr></w:rPrDefault>
  </w:docDefaults>
</w:styles>"""
