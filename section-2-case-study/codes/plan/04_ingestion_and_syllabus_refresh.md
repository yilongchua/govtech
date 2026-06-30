# 04 - Ingestion And Syllabus Ingestion

## PDF-Only Ingestion

The upload endpoint should accept only PDF files.

Validation layers:

| Layer | Check |
|---|---|
| MIME type | Must be `application/pdf`. |
| Extension | Must end with `.pdf`. |
| PDF parser | Must be readable by `pypdf` or `pymupdf`. |
| Page count | Must have at least one page. |
| First page | Must look like an examination paper cover. |

## First Page Assumption

Always assume the first page must start with the exam-paper cover. This makes the first-page classifier a cheap and useful sanity check.

The system should render the first page to an image and send it to the vision model with a simple classification prompt:

```text
You are checking whether this first page is an examination paper cover page.
Return JSON only:
{
  "is_exam_paper": true/false,
  "subject": "history|math|science|unknown",
  "paper_code": "string or null",
  "paper_title": "string or null",
  "exam_year": "string or null",
  "confidence": 0.0-1.0,
  "reasons": ["short evidence"]
}
```

If `is_exam_paper=false`, continue extracting if possible but append an `ERROR` issue. This supports the user's requirement to accumulate errors instead of failing immediately.

## PDF-To-Markdown Conversion

Use two extraction paths:

| Path | Purpose |
|---|---|
| Text extraction with `pypdf` or `pdfplumber` | Main Markdown conversion. |
| Page rendering with `pymupdf` | Image inputs for vision model and image-based source interpretation. |

The Markdown file should preserve page boundaries:

```markdown
# Original File Name

Source PDF: `original.pdf`

Pages: 6

## Page 1

...
```

## Raw And Structured Storage

All extracted data should be stored twice:

| Store | Content |
|---|---|
| Raw | Original PDF, rendered page images, raw Markdown, raw model responses. |
| Structured JSON | Validated Pydantic objects for syllabus, exam paper, comparison, and report. |

## Vision Model Usage

Use the local Qwen 3.6 35B-A3B vision-capable model for:

1. first-page exam-paper classification;
2. identifying subject and paper code from the cover;
3. interpreting source images such as cartoons, maps, diagrams, photographs, or figures;
4. checking whether page images contain text that OCR missed.

Do not use the vision model as the only source of truth. Pair it with extracted text and page references.

## Syllabus URL Ingestion

Syllabus PDFs are ingested through the backend API, not a local History-specific CLI or periodic refresh script.

Endpoint:

```text
POST /api/syllabuses/ingest-url
```

Behavior:

1. Accept a SEAB syllabus page URL, SEAB text-fragment URL, or direct SEAB-hosted PDF URL.
2. Resolve the URL to a syllabus PDF.
3. Download the PDF.
4. Store it under `data/raw/syllabus_pdfs/`.
5. Convert it to Markdown under `data/processed/markdown/syllabus/`.
6. Extract or initialize a `SyllabusDocument`.
7. Store JSON under `data/processed/json/syllabus/`.
8. Update the local syllabus registry.

There is no automatic periodic syllabus refresh. New syllabus documents are added only when a user submits a syllabus URL.

Store a `syllabus_index.json` with:

```json
{
  "subject": "History",
  "subject_code": "2174",
  "year": 2026,
  "source_page_url": "...",
  "pdf_url": "...",
  "pdf_sha256": "...",
  "downloaded_at": "...",
  "markdown_path": "...",
  "json_path": "..."
}
```
