# 03 - Backend Pipeline

## End-To-End Flow

```text
PDF upload
  -> file guard
  -> first-page render
  -> vision sanity check
  -> subject and paper type extraction
  -> PDF-to-Markdown conversion
  -> raw text and raw JSON persistence
  -> syllabus lookup or refresh
  -> syllabus objective extraction
  -> exam paper structure extraction
  -> rule-based checks
  -> AI annotation per question
  -> semantic comparison to syllabus fields
  -> topic weightage calculation
  -> error accumulation
  -> report JSON and chart payloads
```

## API Layer

Use FastAPI:

| Endpoint | Notes |
|---|---|
| `POST /api/uploads` | Accepts `multipart/form-data`; only `application/pdf`. |
| `GET /api/jobs/{job_id}` | Returns progress, current stage, and partial warnings. |
| `GET /api/jobs/{job_id}/report` | Returns final structured comparison. |
| `GET /api/syllabus/latest` | Returns most recent available syllabus year and subject metadata. |
| `POST /api/syllabuses/ingest-url` | Ingest a submitted SEAB syllabus page/PDF URL. |

## Storage

Persist all intermediate artifacts:

```text
data/raw/uploads/{job_id}/original.pdf
data/processed/images/{job_id}/page_001.png
data/processed/markdown/{job_id}/exam.md
data/processed/json/{job_id}/raw_extraction.json
data/processed/json/{job_id}/exam_structure.json
data/processed/json/{job_id}/comparison_report.json
```

This is important for auditability. A model output is only useful if reviewers can trace it back to the original PDF and extracted text.

## Rule-Based Checks

Rules should live in `backend/app/src/comparison/rule_checks.py`, but rule definitions should be represented in schemas/config so they can be versioned.

Do not raise a hard exception for content mismatch. Instead append records to `errors: list[ValidationIssue]`.

Examples:

| Rule | If failed |
|---|---|
| First page is exam cover | Add `ERROR` if document is likely not an exam paper. |
| Total marks found | Add `WARNING` if missing, `ERROR` if contradictory totals. |
| Expected section labels | Add `WARNING` if Section A/B absent. |
| Source count <= syllabus max | Add `WARNING` if exceeded. |
| Paper code found | Add `WARNING`; route subject by best effort. |

## Syllabus Lookup

The backend should obtain the latest syllabus objective for the detected subject and year. For the current MVP:

1. Use the 2026 SEAB page as the listing source.
2. Extract the exact History syllabus PDF link.
3. Download it into `data/raw/syllabus_pdfs/`.
4. Convert to Markdown.
5. Extract structured objective JSON.

The current exact URL is:

```text
https://isomer-user-content.by.gov.sg/334/3622b032-4be0-497a-9192-399cb6c98b65/2174_y26_sy.pdf
```

The page URL is:

```text
https://www.seab.gov.sg/gce-o-level/o-level-syllabuses-examined-for-school-candidates-2026/
```

## Job Execution

For the case-study implementation, synchronous execution is acceptable. In a production environment, use a job queue:

| Component | Option |
|---|---|
| Queue | Redis Queue, Celery, or Dramatiq |
| Progress | Store in Redis or local JSON during MVP |
| Large files | Stream upload to disk |
| Timeouts | Apply per model call and per job |
