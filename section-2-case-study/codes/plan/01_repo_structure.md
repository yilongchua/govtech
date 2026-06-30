# 01 - Repository Structure

## Target Structure

```text
section-2-case-study/
|-- README.md
|-- requirements.txt
|-- pyproject.toml
|-- docker-compose.yml
|-- Dockerfile.backend
|-- Dockerfile.frontend
|-- .env.example
|-- 2174_y26_sy.pdf
|-- 2174_y26_sy.md
|-- data/
|   |-- raw/
|   |   |-- uploads/
|   |   |-- syllabus_pdfs/
|   |   |-- exam_pdfs/
|   |-- processed/
|   |   |-- markdown/
|   |   |-- json/
|   |   |-- images/
|   |-- reference/
|   |   |-- syllabus_index.json
|   |   |-- subject_registry.json
|-- frontend/
|   |-- package.json
|   |-- vite.config.ts
|   |-- src/
|   |   |-- App.tsx
|   |   |-- components/
|   |   |   |-- UploadDropzone.tsx
|   |   |   |-- ProgressBar.tsx
|   |   |   |-- ComparisonReport.tsx
|   |   |   |-- ErrorPanel.tsx
|   |   |-- api/
|   |   |   |-- client.ts
|   |   |-- styles/
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- api/
|   |   |   |-- routes_upload.py
|   |   |   |-- routes_jobs.py
|   |   |   |-- routes_syllabus.py
|   |   |-- core/
|   |   |   |-- config.py
|   |   |   |-- logging.py
|   |   |   |-- storage.py
|   |   |-- src/
|   |   |   |-- ingestion/
|   |   |   |   |-- pdf_guard.py
|   |   |   |   |-- pdf_to_markdown.py
|   |   |   |   |-- first_page_classifier.py
|   |   |   |   |-- page_renderer.py
|   |   |   |-- syllabus/
|   |   |   |   |-- seab_scraper.py
|   |   |   |   |-- llm_syllabus_extractor.py
|   |   |   |   |-- metadata.py
|   |   |   |   |-- syllabus_registry.py
|   |   |   |-- extraction/
|   |   |   |   |-- exam_extractor.py
|   |   |   |   |-- question_segmenter.py
|   |   |   |   |-- source_segmenter.py
|   |   |   |-- comparison/
|   |   |   |   |-- rule_checks.py
|   |   |   |   |-- semantic_matcher.py
|   |   |   |   |-- topic_weightage.py
|   |   |   |-- graph/
|   |   |   |   |-- nodes.py
|   |   |   |   |-- state.py
|   |   |   |   |-- workflow.py
|   |   |   |-- reporting/
|   |   |   |   |-- report_builder.py
|   |   |   |   |-- chart_payloads.py
|   |   |-- prompts/
|   |   |   |-- classify_first_page.j2
|   |   |   |-- extract_exam_structure.j2
|   |   |   |-- extract_syllabus_objectives.j2
|   |   |   |-- map_question_to_syllabus.j2
|   |   |   |-- evaluate_model_output.j2
|   |   |-- schemas/
|   |   |   |-- base.py
|   |   |   |-- errors.py
|   |   |   |-- exam.py
|   |   |   |-- syllabus.py
|   |   |   |-- comparison.py
|   |   |   |-- report.py
|   |   |-- jobs/
|   |   |   |-- worker.py
|   |   |   |-- progress.py
|-- scripts/
|   |-- convert_pdf_to_md.py
|   |-- run_local_paper_analysis.py
|   |-- sanity_check_exam_pdf.py
|-- tests/
|   |-- fixtures/
|   |-- test_pdf_guard.py
|   |-- test_syllabus_extractor.py
|   |-- test_exam_extractor.py
|   |-- test_rule_checks.py
|   |-- test_topic_weightage.py
|-- plan/
```

## Production Environment Assumptions

The system should be split into a lightweight frontend and a backend API. The backend owns file storage, extraction, model calls, rule checks, and report generation. The frontend should only upload PDFs, show progress, and render the returned structured report.

## Dependencies

`requirements.txt` should include:

```text
fastapi
uvicorn[standard]
pydantic
pydantic-settings
python-multipart
httpx
beautifulsoup4
jinja2
lxml
pypdf
pdfplumber
pymupdf
pillow
langgraph
orjson
tenacity
pytest
```

If the local Qwen 3.6 35B-A3B vision model is served through an OpenAI-compatible endpoint, the backend should also include an OpenAI-compatible client. If it is served through vLLM or Ollama, add the relevant runtime client and document the endpoint in `.env.example`.

## Docker

Use Docker for reproducibility:

| File | Responsibility |
|---|---|
| `Dockerfile.backend` | Python runtime, PDF tooling, API server, worker process. |
| `Dockerfile.frontend` | Node build, static frontend serving. |
| `docker-compose.yml` | Backend, frontend, optional Redis queue, optional local model endpoint reference. |

The model itself should not be bundled into the app image. Treat Qwen as an external service with a configured URL, model name, timeout, and retry policy.
