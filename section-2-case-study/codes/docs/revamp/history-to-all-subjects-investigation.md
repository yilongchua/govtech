# Revamp Investigation: From History-Only To All-Subject Exam Alignment

Date: 2026-06-30

## Current Status

This document records the pre-revamp investigation that identified History-only assumptions. The implemented system now has:

- generic `run_analysis` orchestration;
- `history_o_level_2174` and `generic_exam_subject` routes;
- backend-provided `structure_metrics`;
- `download_filename_base`;
- `QuestionAnnotation.evidence_page_numbers` instead of confidence;
- LLM-backed question-to-syllabus mapping for real model clients;
- generic frontend copy and route-driven report rendering.

See `implementation-notes.md` plus the top-level docs for the current functional flow.

## Executive Summary

At the time of investigation, the implementation was not just branded as a History tool; the runtime behavior was deeply coupled to Singapore-Cambridge O-Level History syllabus `2174`, especially Paper 1/Paper 2 structure, source-based questions, essays, AO1/AO2/AO3, Section A/Section B, 50 candidate marks, and specific History topics.

The reusable foundation was the generic document pipeline shape: upload PDF, validate PDF, render first page, classify subject metadata, convert to Markdown, extract structured exam data, compare against a syllabus, produce JSON/Markdown/DOCX reports. The recommended revamp was to replace History-specific functions/config/prompts with subject routes backed by a registry, subject-specific syllabus assets, rule packs, prompt variables, and comparison strategies.

## Pre-Revamp Runtime Flow

The backend upload path was:

1. `frontend/src/App.tsx` submits a PDF through `uploadPaper`.
2. `backend/app/api/routes_upload.py` accepts the file and always calls `run_history_analysis`.
3. `backend/app/src/graph/workflow.py` validates the PDF, renders the first page, classifies metadata, converts PDF to Markdown, loads the hard-coded History syllabus files, extracts a History exam structure, applies History rules, annotates with a History matcher, calculates History-style weightage, and builds a report.

The first-page classifier already asks for subject-level routing metadata, but routing is not actually used to select a subject pipeline. It is recorded, then the History pipeline continues.

## Backend History Assumptions

### Application Identity And Settings

| Area | Location | Assumption | Impact |
|---|---|---|---|
| FastAPI app title | `backend/app/main.py:12` | App is named `History Exam Paper Alignment Tool`. | Cosmetic/API metadata only. |
| Health response | `backend/app/main.py:27-29` | Returns `subject: History` and `history_syllabus_year`. | Any monitoring/client metadata assumes one subject. |
| Settings | `backend/app/core/config.py:54-58` | Uses `HISTORY_SYLLABUS_YEAR` and `HISTORY_SYLLABUS_PDF_URL`; default URL is `2174_y26_sy.pdf`. | Cannot configure multiple subjects or syllabus URLs without new settings model. |

### Upload And Pipeline Orchestration

| Area | Location | Assumption | Impact |
|---|---|---|---|
| Upload route | `backend/app/api/routes_upload.py:11,39` | Imports and calls `run_history_analysis` for every PDF. | Non-History uploads still go through History extraction/rules. |
| Workflow function | `backend/app/src/graph/workflow.py:8-22` | Imports History-specific rules, extractor, and syllabus extractor; function is named `run_history_analysis`. | Core orchestration has no subject abstraction. |
| Syllabus file selection | `backend/app/src/graph/workflow.py:53-55` | Always loads root files `2174_y26_sy.md` and `2174_y26_sy.pdf`. | Subject/year cannot be selected from upload metadata. |
| Rule execution | `backend/app/src/graph/workflow.py:69` | Always calls `run_history_paper_rules`. | Math, Science, English, etc. would be marked against History section/mark rules. |
| Annotation | `backend/app/src/graph/workflow.py:71` | Always calls the deterministic History semantic matcher. | Topic/objective mapping is invalid outside History. |

### Syllabus Layer

| Area | Location | Assumption | Impact |
|---|---|---|---|
| Syllabus API | `backend/app/api/routes_syllabus.py:19-26` | `/api/syllabus/latest` always returns History `2174`. | Frontend cannot discover/select other subjects. |
| Refresh endpoint | Removed | CLI/API refresh scripts are no longer part of the ingestion surface. | Syllabus ingestion is driven by submitted SEAB page/PDF URLs. |
| SEAB scraper | `backend/app/src/syllabus/seab_scraper.py` | Resolves submitted SEAB syllabus page/text-fragment URLs or direct SEAB-hosted PDF URLs. | Syllabus discovery depends on user-submitted URLs and configured subject extractors. |
| Registry writer | `backend/app/src/syllabus/syllabus_registry.py` | Writes one `syllabus_index.json`, one `subject_registry.json`, and fixed JSON path `2174_y26_sy.json`. | Registry is a singleton, not a catalog. |
| Syllabus extractor | `backend/app/src/syllabus/llm_syllabus_extractor.py` | Uses the configured LLM to extract objectives, components, topics, and rules for every ingested syllabus. | Extraction quality is model-dependent and requires audit artifacts. |

The syllabus schema itself is partly reusable (`backend/app/schemas/syllabus.py:10-48`), but it has History-shaped fields such as `is_source_based_eligible`. Other subjects may need fields like calculator policy, formula sheet availability, practical components, oral/listening components, coursework, lab skills, stimulus materials, data-response questions, or paper option routes.

### Exam Extraction

| Area | Location | Assumption | Impact |
|---|---|---|---|
| Fallback extractor | `backend/app/src/extraction/exam_extractor.py:10-28` | Function is `extract_history_exam`; searches `HISTORY ([0-9]+/[0-9]+)`, rejects non-History first pages, defaults title to `History exam paper`. | Regex fallback cannot parse other subject covers reliably. |
| Section parsing | `backend/app/src/extraction/exam_extractor.py:76-99` | Expects `Section A` and `Section B`; Section A contains Q1(a)-Q1(e); Section B contains questions 2-9 with optional `(a)/(b)` either-or groups. | Strongly tied to History papers. |
| Candidate marks | `backend/app/src/extraction/exam_extractor.py:106-113` | Candidate total is Section A marks plus `20` when Section B exists. | Invalid for most subjects. |
| Source parsing | `backend/app/src/extraction/exam_extractor.py:116-139` | Extracts `Source A-F` and source references from prompts. | Useful for source/stimulus subjects only, not universal. |
| LLM validation | `backend/app/src/extraction/llm_exam_extractor.py:81-92` | Allows only `2174/01` or `2174/02`; requires total marks and marks for every question. | Blocks other paper codes and subjects with different mark visibility conventions. |
| Mock model | `backend/app/src/ingestion/model_client.py:22-33` | Mock classifier always returns History `2174/01`. | Tests/dev mode cannot simulate subject routing without changes. |

The generic `ExamPaper`, `ExamQuestion`, and `FirstPageCheck` schemas are good starting points (`backend/app/schemas/exam.py:10-50`), but may need optional component metadata, question type, paper/component id, choice policy, stimulus refs, skills tags, and subject-specific extracted features.

### Rule Checks

| Area | Location | Assumption | Impact |
|---|---|---|---|
| Rule function | `backend/app/src/comparison/rule_checks.py:9-33` | Function is `run_history_paper_rules`. | No rule engine abstraction. |
| Subject rule | `backend/app/src/comparison/rule_checks.py:23` | Requires `exam.subject == History`. | Non-History always errors. |
| Paper codes | `backend/app/src/comparison/rule_checks.py:25` | Supports only `2174/01` and `2174/02`. | Non-History always errors. |
| Marks/sections | `backend/app/src/comparison/rule_checks.py:26-33` | Requires 50 candidate marks, Section A 30, Section B 20 candidate marks, at least three essays, max six sources, Q1(a)-Q1(e), 30 offered marks. | Rule model is actually a History Paper 1/2 blueprint. |
| Default config | `backend/app/src/comparison/rule_config.py` and `data/reference/rule_config_2174_01.json` | Rule config is `2174`-specific and only lightly used by code. | Needs per-subject/per-paper rule packs and a generic evaluator. |

### Semantic Matching And Topic Weightage

| Area | Location | Assumption | Impact |
|---|---|---|---|
| Objective mapping | `backend/app/src/comparison/semantic_matcher.py:8-13` | Section A/source/cartoonist => AO1+AO3, everything else => AO1+AO2. | History AO model does not generalize to other subjects. |
| Topic defaults | `backend/app/src/comparison/semantic_matcher.py:15-20` | Defaults to History topics based on `2174/02` vs everything else. | Mislabels unknown content as History. |
| Keyword topic matcher | `backend/app/src/comparison/semantic_matcher.py:22-47` | Matches Malaya, Cold War, Vietnam, Versailles, Hitler, appeasement, etc. | Entirely History-specific. |
| Weightage | `backend/app/src/comparison/topic_weightage.py:19-37` | Section A required; Section B offered as choices; fixed explanatory note. | Does not fit many papers where all questions are compulsory, options appear within sections, or candidates choose from multiple papers. |

For all-subject support, `annotate_question` should become a strategy selected by subject/paper. At minimum, there should be a generic LLM/embedding-based matcher that receives syllabus topics/objectives as candidates rather than keywording known History content.

### Reporting

| Area | Location | Assumption | Impact |
|---|---|---|---|
| Report summary | `backend/app/src/reporting/report_builder.py:23-28` | Uses `History paper`, `History syllabus baseline`, Section A AO1+AO3, Section B AO1+AO2, essay-choice marks. | Reports will make false claims for other subjects. |
| DOCX heading | `backend/app/src/reporting/docx_export.py:23-35` | Heading is `History {paper_code} Alignment Report`. | Cosmetic but user-facing. |
| DOCX structure metrics | `backend/app/src/reporting/docx_export.py:28-80` | Computes Section B candidate/offered marks and source count. | Same History structural assumption appears in exported report. |
| Download filename | `backend/app/api/routes_jobs.py:39-43` | Filename is `history-alignment-{job_id}.docx`. | Cosmetic but should be generalized. |

### Prompts

| Prompt | Location | History Assumption |
|---|---|---|
| First-page classifier | `backend/app/prompts/classify_first_page.j2:7` | Says the only supported route is History. |
| Exam extraction | `backend/app/prompts/extract_exam_structure.j2:3-16` | Role is for History papers; objective says History `2174`; asks for source-based Section A, essays, Q2(a)/Q2(b), Paper 2 essay behavior. |
| Syllabus extraction | `backend/app/prompts/extract_syllabus_objectives.j2:3-13` | Role is O-Level History; asks for Paper 1/Paper 2 topic structure and source-based eligibility. |
| Output evaluation | `backend/app/prompts/evaluate_model_output.j2:7-15` | Evaluates History output, source-based/essay AO plausibility, offered essay marks. |
| Question mapping | `backend/app/prompts/map_question_to_syllabus.j2` | Mostly generic, but currently not used by the deterministic matcher. |

Prompt templates should become subject-aware templates with injected subject metadata, assessment vocabulary, component definitions, and extraction hints.

### Tests And Fixtures

The tests mostly lock in History behavior:

- `tests/test_rule_checks.py:4-33` tests `run_history_paper_rules` and `extract_history_exam` against `2174` specimen papers.
- `tests/test_syllabus_extractor.py` validates LLM-backed syllabus extraction with mocked model output.
- `tests/test_docx_export.py:15-55` expects History `2174/01`, Cold War, and `History 2174/01 Alignment Report`.
- `tests/fixtures/history_2174_paper_1_gold.json` is a History gold fixture.

These tests should remain as a History route regression suite, but new generic tests are needed for routing, registry lookup, rule-pack loading, and at least one non-History fixture.

## Frontend History Assumptions

### App Copy And State

| Area | Location | Assumption | Impact |
|---|---|---|---|
| Progress stage | `frontend/src/App.tsx:24-26` | Shows `Analysing History paper`. | Cosmetic but misleading. |
| Header | `frontend/src/App.tsx:42-43` | Title and subtitle explicitly say History POC and History syllabus. | User experience blocks all-subject positioning. |
| Dropzone | `frontend/src/components/UploadDropzone.tsx:39-41` | Says `Drop History exam paper PDF`. | Cosmetic but central first-screen copy. |

### Report UI Logic

| Area | Location | Assumption | Impact |
|---|---|---|---|
| Download names | `frontend/src/components/ComparisonReport.tsx:53-55` | Downloads are named `history-alignment-*`. | Cosmetic. |
| Section B computations | `frontend/src/components/ComparisonReport.tsx:28-48` | Computes offered/candidate marks through `choice_group`; caps Section B candidate marks at 20. | Encodes History choice structure in UI. |
| Structure table | `frontend/src/components/ComparisonReport.tsx:75-88` | Always shows Section A marks, Section B candidate/offered marks/questions, source count. | Non-History reports need dynamic component metrics, not hard-coded rows. |
| Objective labels | `frontend/src/components/ComparisonReport.tsx:126-140` | Displays objectives/topics generically, but labels come from History backend today. | UI can remain if backend annotations become subject-aware. |

The frontend API client is mostly neutral (`frontend/src/api/client.ts`), but `getLatestSyllabus()` currently maps to a singleton endpoint. A multi-subject UI likely needs `GET /api/subjects`, `GET /api/syllabi?subject_code=...`, and report-driven dynamic metric rendering.

## Reusable Parts

These can likely remain with modest changes:

- PDF upload/storage/cache flow in `backend/app/api/routes_upload.py`, minus the direct `run_history_analysis` call.
- PDF validation, first-page rendering, and PDF-to-Markdown conversion.
- `FirstPageCheck`, `ExamPaper`, `ExamQuestion`, and `SourceItem` as base schemas, with extensions.
- `SyllabusDocument`, `AssessmentObjective`, `AssessmentComponent`, and `SyllabusTopic` as base schemas, with additional optional fields.
- Report envelope shape: `ComparisonReport`, annotations, rule checks, issue collection, chart payload concept.
- Frontend summary/report rendering shell, once structure rows come from report payloads instead of local History calculations.

## Original Target Architecture

### 1. Subject Registry

Replace the singleton History registry with a catalog:

```json
{
  "subjects": [
    {
      "subject": "History",
      "subject_code": "2174",
      "level": "O-Level",
      "latest_year": 2026,
      "syllabus_assets": {
        "pdf_path": "...",
        "markdown_path": "...",
        "json_path": "..."
      },
      "route": "history_o_level_2174"
    }
  ]
}
```

This enables first-page classification to select a route by subject code rather than defaulting to History.

### 2. Subject Route Interface

Introduce a route abstraction, for example:

```python
class SubjectRoute(Protocol):
    route_id: str
    subject_codes: set[str]

    def load_syllabus(self, first_page: FirstPageCheck) -> SyllabusDocument: ...
    def extract_exam(self, markdown_path: Path, pdf_path: Path, first_page: FirstPageCheck, syllabus: SyllabusDocument, client: LocalModelClient) -> ExamPaper: ...
    def run_rules(self, exam: ExamPaper, syllabus: SyllabusDocument) -> list[RuleCheckResult]: ...
    def annotate(self, exam: ExamPaper, syllabus: SyllabusDocument, client: LocalModelClient) -> list[QuestionAnnotation]: ...
    def build_structure_metrics(self, exam: ExamPaper, syllabus: SyllabusDocument) -> list[dict]: ...
```

History can become the first concrete route. New subjects can start with a generic route that relies more heavily on LLM extraction and config-driven rules.

### 3. Generic Rule Engine

Move from `run_history_paper_rules` to data-driven rule packs:

- supported paper codes
- expected total marks by paper/component
- compulsory vs optional components
- section/question count expectations
- source/stimulus constraints where applicable
- calculator/formula/practical/oral flags where applicable

History-specific rules stay in a `history_2174` pack. Other subjects add their own packs without editing central code.

### 4. Generic Syllabus Extraction

Syllabus extraction now uses a generic LLM extractor that outputs the base `SyllabusDocument`; subject-specific postprocessors can be added later if a subject needs additional validation.

The generic extractor should preserve:

- assessment objectives or learning outcomes
- paper/component structure
- topics/content domains
- mark/weighting rules
- choice/option rules
- allowed materials and special assessment features

### 5. Dynamic Report Metrics

Backend should emit report-ready structure metrics instead of making frontend/DOCX recompute History rows:

```json
"structure_metrics": [
  {"label": "Total marks", "value": 50},
  {"label": "Paper 1 Section A marks", "value": 30},
  {"label": "Source count", "value": 5}
]
```

This allows the frontend and DOCX exporter to render subject-appropriate rows.

## Original Migration Plan

1. Rename the orchestration entrypoint from `run_history_analysis` to a generic `run_analysis`, while keeping a History route internally.
2. Add a subject registry and route resolver based on `FirstPageCheck.paper_code`, `subject`, and configured aliases.
3. Move hard-coded `2174` syllabus paths into registry/config.
4. Convert History rule checks into a rule pack plus a generic evaluator.
5. Move History fallback extraction into `routes/history_2174.py`; add a generic LLM extraction route for unknown/new subjects.
6. Replace deterministic History topic matcher with a route-level matcher. For generic subjects, use syllabus candidate matching through `map_question_to_syllabus.j2`.
7. Add `structure_metrics` and `download_filename_base` to the report payload; update frontend and DOCX export to render those fields.
8. Update prompts to receive `subject_profile` instead of baking History into template text.
9. Keep existing History tests as route-specific regression tests; add routing/registry tests and one non-History smoke fixture.

## Risk Areas

- **Syllabus variability:** Different subjects express objectives, topics, assessment papers, and choice rules differently. A single schema can work only if optional metadata is flexible enough.
- **Question extraction:** History has predictable sections and source labels. Other subjects may use diagrams, tables, multi-part calculations, structured data booklets, listening/oral components, or practical papers.
- **Alignment semantics:** AO1/AO2/AO3 and topic keywords are History-specific. Generic alignment needs syllabus-grounded matching, not hard-coded terms.
- **Choice/weightage accounting:** The required/offered distinction is valuable, but the algorithm must be component-rule driven rather than Section A/Section B driven.
- **User trust:** Reports must avoid saying a subject is fully aligned when the route is generic or the syllabus/rule pack is unconfigured. Prefer explicit traceability through extracted question/source page numbers and human-review flags.

## Highest-Priority Files To Change Later

1. `backend/app/src/graph/workflow.py`
2. `backend/app/api/routes_upload.py`
3. `backend/app/api/routes_syllabus.py`
4. `backend/app/src/syllabus/llm_syllabus_extractor.py`
5. `backend/app/src/comparison/rule_checks.py`
6. `backend/app/src/comparison/semantic_matcher.py`
7. `backend/app/src/extraction/exam_extractor.py`
8. `backend/app/src/extraction/llm_exam_extractor.py`
9. `backend/app/src/reporting/report_builder.py`
10. `backend/app/src/reporting/docx_export.py`
11. `backend/app/prompts/extract_exam_structure.j2`
12. `backend/app/prompts/extract_syllabus_objectives.j2`
13. `frontend/src/App.tsx`
14. `frontend/src/components/UploadDropzone.tsx`
15. `frontend/src/components/ComparisonReport.tsx`

## Bottom Line

The product can be generalized, but this is a real architectural revamp rather than a rename. The clean path is to preserve the current History functionality as one route and build a subject-routing framework around it. That avoids breaking the working POC while making room for additional subjects through configuration, subject profiles, rule packs, and dynamic report rendering.
