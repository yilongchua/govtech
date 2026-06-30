# Plan Implementation Status

Audit date: 2026-06-29

This status checks each Markdown file in `section-2-case-study/plan/` against the current implementation.

## Summary

| Plan file | Status | Evidence |
|---|---|---|
| `README.md` | Implemented | Product goal, local inputs, structured report generation, and accumulated issue handling are implemented. |
| `01_repo_structure.md` | Implemented | Planned backend, frontend, scripts, tests, prompts, schemas, jobs, Docker, and data-reference structure exist. |
| `02_frontend_experience.md` | Implemented | Upload-first UI, latest-year selector, PDF-only dropzone, submit action, loading bar, report tables, issue panel, and JSON/Markdown exports exist. |
| `03_backend_pipeline.md` | Implemented | FastAPI upload/job/report/syllabus endpoints, PDF guard, first-page render/classification, Markdown conversion, syllabus extraction, exam extraction, rule checks, annotations, topic weightage, raw artifacts, and report payloads exist. |
| `04_ingestion_and_syllabus_refresh.md` | Implemented | PDF-only ingestion, first-page vision sanity check, page-bounded Markdown conversion, raw/structured persistence, API-based syllabus URL ingestion, and registry files exist. |
| `05_schema_design.md` | Implemented | Pydantic models exist for validation issues, base pipeline model, syllabus, exam paper, first-page check, annotations, rule checks, topic weightage, and report output. Rule config JSON exists. |
| `06_prompts_and_langgraph.md` | Implemented for MVP | Prompt files exist, local model adapters support mock/LM Studio/Ollama, graph state/nodes exist, `langgraph` is declared as a dependency, and the tested workflow executes the History route. |
| `07_evaluation_and_reporting.md` | Implemented | Gold fixture, evaluation script, rule checks, report JSON, Markdown report export, chart payloads, and topic-weightage split are implemented. |
| `08_implementation_phases.md` | Implemented for MVP | Phases 0-6 are implemented. Phase 7 has MVP hooks for file-size limits, timeouts, audit logs, PDF hash tracking, prompt versioning, and URL-scoped syllabus ingestion. Virus scanning, external monitoring, and role-based syllabus management remain deployment-environment concerns. |

## Implemented Artifacts

| Area | Evidence |
|---|---|
| Docker backend/frontend | `Dockerfile.backend`, `Dockerfile.frontend`, `docker-compose.yml`. |
| Backend API | `backend/app/api/routes_upload.py`, `routes_jobs.py`, `routes_syllabus.py`, `backend/app/main.py`. |
| History workflow | `backend/app/src/graph/workflow.py`, `nodes.py`, `state.py`. |
| PDF ingestion | `backend/app/src/ingestion/pdf_guard.py`, `page_renderer.py`, `pdf_to_markdown.py`, `first_page_classifier.py`. |
| Local model support | `backend/app/src/ingestion/model_client.py` supports `mock`, `openai-compatible`, and `ollama`. |
| Prompt files | `backend/app/prompts/*.j2`. |
| Raw artifacts | `raw_model_response.json`, `raw_extraction.json`, `exam_structure.json`, `audit_log.json`, `comparison_report.json` per job. |
| Syllabus ingestion and registry | `POST /api/syllabuses/ingest-url`, `data/reference/syllabus_index.json`, `subject_registry.json`. |
| Rule config | `data/reference/rule_config_2174_01.json`, `backend/app/src/comparison/rule_config.py`. |
| Schemas | `backend/app/schemas/base.py`, `exam.py`, `syllabus.py`, `comparison.py`, `errors.py`, `report.py`. |
| Frontend | `frontend/src/App.tsx`, `UploadDropzone.tsx`, `ProgressBar.tsx`, `ComparisonReport.tsx`, `ErrorPanel.tsx`. |
| Evaluation | `tests/fixtures/history_2174_paper_1_gold.json`, `scripts/evaluate_report.py`. |
| Tests | `tests/test_pdf_guard.py`, `test_syllabus_extractor.py`, `test_exam_extractor.py`, `test_rule_checks.py`, `test_topic_weightage.py`, `test_workflow_smoke.py`. |

## Latest Verification

Commands run:

```bash
python3 scripts/run_e2e_local_model_test.py --pdf data/raw/exam_pdfs/2174_specimen_paper_1.pdf --provider mock
python3 scripts/evaluate_report.py --report data/processed/json/b6f7dfc6c322/comparison_report.json
python3 -m pytest -q
npm --prefix frontend run build
docker compose config
docker compose build
docker compose up -d
curl http://127.0.0.1:8000/api/health
curl -I http://127.0.0.1:5173
curl http://127.0.0.1:8000/api/jobs/{job_id}/report.md
docker compose down
```

Results:

```text
E2E mock run passed: subject=History, total_marks=50, issues=0
Evaluation passed: topic_top1_accuracy=1.0, ao_accuracy=1.0, topic_weightage_accuracy=1.0
pytest passed: 6 passed
frontend build passed
compose config passed
docker compose build passed
backend health returned {"ok":true,"subject":"History","syllabus_year":2026}
frontend returned HTTP/1.1 200 OK
Markdown report endpoint returned a report
```

Real LM Studio/OpenAI-compatible E2E run was previously verified with:

```bash
python3 scripts/run_e2e_local_model_test.py \
  --pdf data/raw/exam_pdfs/2174_specimen_paper_1.pdf \
  --provider openai-compatible \
  --base-url http://localhost:1234/v1 \
  --model qwen/qwen3.6-35b-a3b \
  --require-real-model
```

Result:

```text
subject=History
total_marks=50
issues=0
```

Ollama support is implemented and preflighted by the same E2E script. Ollama was not installed/running locally during verification, so that endpoint could not be executed on this machine.

## Deployment Notes

The MVP is complete for the History Paper 1 case-study workflow. The following are intentionally deployment-environment concerns rather than local MVP blockers:

| Concern | Current handling |
|---|---|
| Virus scanning | Not bundled; add at deployment boundary if accepting untrusted public uploads. |
| External monitoring | Audit logs are written per job; production metrics shipping should be added when deployed. |
| Multi-subject support | Subject routing is documented, but the launcher is intentionally History-specific. |
| Advanced semantic retrieval | Current matcher is deterministic and auditable for History; embeddings/cross-encoder can be added for broader scaling. |
