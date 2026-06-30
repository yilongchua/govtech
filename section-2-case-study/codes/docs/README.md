# Technical Documentation

These notes explain the implemented exam-paper alignment tool for engineering handoff and maintenance. The current system supports a configured History `2174` route and a conservative generic fallback route for other subjects.

## Documents

| File | Focus |
|---|---|
| `01_system_architecture.md` | Frontend/backend architecture, subject routing, APIs, and external local model dependency. |
| `02_frontend_flow.md` | Frontend states, populated UI information, report rendering, and traceability fields. |
| `03_backend_pipeline.md` | End-to-end backend flow from uploaded PDF to routed comparison report. |
| `04_local_model_testing.md` | LM Studio, Ollama, and mock provider E2E testing paths. |
| `05_data_contracts.md` | JSON schemas and report payload fields consumed by the frontend and exports. |
| `revamp/` | Investigation and implementation notes for the History-to-all-subjects revamp. |

## Diagrams

Generated PNG diagrams live under `docs/diagrams/`. They are useful orientation aids, but the Markdown files are the source of truth for the latest routed flow.

Regenerate diagrams with:

```bash
cd section-2-case-study
python3 docs/generate_diagrams.py
```
