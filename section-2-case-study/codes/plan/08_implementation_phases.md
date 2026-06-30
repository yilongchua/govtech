# 08 - Implementation Phases

## Phase 0 - Organise Existing Artifacts

Status target:

1. Keep `2174_y26_sy.pdf` and `2174_y26_sy.md` as local syllabus references.
2. Keep uploaded and specimen exam papers under `data/raw/exam_pdfs/` or `data/raw/uploads/`.
3. Add `data/raw/`, `data/processed/`, and `data/reference/` folders.
4. Add initial `requirements.txt`.

## Phase 1 - Local CLI MVP

Build scripts first, before the web app:

| Script | Purpose |
|---|---|
| `scripts/convert_pdf_to_md.py` | Convert any PDF into page-bounded Markdown. |
| `scripts/sanity_check_exam_pdf.py` | Render first page and call Qwen vision classifier. |
| `scripts/run_local_paper_analysis.py` | Run full analysis on one exam-paper PDF. |

Expected CLI output:

```text
data/processed/json/{job_id}/comparison_report.json
data/processed/markdown/{job_id}/exam.md
```

## Phase 2 - Schemas And Rule Checks

Implement Pydantic schemas:

1. `ValidationIssue`
2. `SyllabusDocument`
3. `ExamPaper`
4. `QuestionAnnotation`
5. `ComparisonReport`

Then implement deterministic checks for Paper 1:

1. paper total is 50;
2. Section A total is 30;
3. Section B has 3 offered essays;
4. source count is <= 6;
5. essay questions are 10 marks each;
6. Q1(a)-Q1(e) are present.

All mismatches append issues; they do not crash the job.

## Phase 3 - LangGraph Backend

Implement the graph with clear node boundaries:

1. validate PDF;
2. classify first page;
3. convert PDF;
4. extract exam structure;
5. load selected syllabus;
6. extract syllabus objectives;
7. run rule checks;
8. annotate questions;
9. compare semantically;
10. build report.

Store raw model responses for every LLM node.

## Phase 4 - FastAPI Service

Add:

1. upload endpoint;
2. job progress endpoint;
3. report endpoint;
4. syllabus latest endpoint.

For MVP, progress can be stored in a local JSON file. In production, move progress state to Redis or a database.

## Phase 5 - Frontend

Build the upload-first UI:

1. first-page subject routing with History as the current POC syllabus route;
2. large drag-and-drop PDF upload area;
3. submit button;
4. loading bar;
5. structural comparison output;
6. warnings/errors panel;
7. JSON and Markdown export buttons.

## Phase 6 - Evaluation Pack

Create a labelled evaluation file:

```text
tests/fixtures/history_2174_paper_1_gold.json
```

Include:

1. expected paper metadata;
2. expected question list;
3. expected source list;
4. expected AO mapping;
5. expected topic mapping;
6. expected topic weightage.

Run automated tests before producing the final data story.

## Phase 7 - Production Hardening

Add:

1. file-size limits;
2. virus scanning if deployed externally;
3. model timeout and retry policy;
4. audit logs;
5. PDF hash tracking;
6. prompt versioning;
7. role-based access for syllabus management;
8. monitoring for failed extraction rates.

MVP status: file-size limits, model timeout configuration, audit logs, PDF hash tracking, prompt versioning, and URL-scoped syllabus ingestion are implemented. Virus scanning, external monitoring, and role-based syllabus management remain deployment-environment concerns.

## Suggested Final Deliverables

| Deliverable | Path |
|---|---|
| Backend prototype | `backend/` |
| Frontend prototype | `frontend/` |
| PDF conversion script | `scripts/convert_pdf_to_md.py` |
| First-page sanity script | `scripts/sanity_check_exam_pdf.py` |
| Evaluation gold labels | `tests/fixtures/history_2174_paper_1_gold.json` |
| Public data story | `section-2-case-study/slides/` or a Markdown report |
