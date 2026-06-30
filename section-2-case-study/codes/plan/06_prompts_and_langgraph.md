# 06 - Prompts And LangGraph Backbone

## Model Assumption

Use a local Qwen 3.6 35B-A3B vision-capable model. Serve it behind a stable API endpoint, preferably OpenAI-compatible:

```text
LOCAL_MODEL_BASE_URL=http://localhost:1234/v1
LOCAL_MODEL_NAME=qwen/qwen3.6-35b-a3b
```

The system works even if the model output is imperfect. Model responses are schema-validated and stored as raw audit artifacts. Malformed JSON is converted into a recoverable issue-style response for the first-page classifier.

## LangGraph State

```python
class AnalysisState(TypedDict):
    job_id: str
    pdf_path: str
    page_image_paths: list[str]
    markdown_path: str | None
    first_page_check: dict | None
    subject: str | None
    paper_code: str | None
    syllabus_doc: dict | None
    exam_paper: dict | None
    annotations: list[dict]
    rule_checks: list[dict]
    comparison_report: dict | None
    issues: list[dict]
```

## Graph Nodes

```text
validate_pdf
  -> render_first_page
  -> classify_first_page
  -> convert_pdf_to_markdown
  -> extract_exam_structure
  -> load_or_refresh_syllabus
  -> extract_syllabus_objectives
  -> rule_based_checks
  -> route_by_subject
  -> annotate_questions
  -> semantic_compare
  -> calculate_topic_weightage
  -> build_report
```

## Subject Routing

The first-page classifier extracts the subject. The subject then selects:

| Subject | Extraction schema |
|---|---|
| History | source-based case study, essay prompts, sources, topic tags, AO1/AO2/AO3 |
| Mathematics | structured questions, subparts, marks, formula/topic skills |
| Science | structured questions, diagrams, data tables, practical/inquiry skills |
| Unknown | generic exam-paper schema with issues |

For this case study, implement the History route first.

## Prompt Files

### `prompts/classify_first_page.j2`

Purpose: classify whether the first page is an exam cover and extract paper metadata.

Output schema:

```json
{
  "is_exam_paper": true,
  "subject": "History",
  "paper_code": "2174/01",
  "paper_title": "...",
  "exam_year": 2024,
  "confidence": 0.94,
  "reasons": ["The page contains GCE Ordinary Level and paper instructions."]
}
```

### `prompts/extract_syllabus_objectives.j2`

Purpose: extract assessment objectives, scheme of assessment, and syllabus topics.

Rules:

1. Return JSON only.
2. Preserve objective names exactly where possible.
3. Include page numbers.
4. Mark source-based eligible topics when the syllabus marks them with `*`.

### `prompts/extract_exam_structure.j2`

Purpose: extract paper metadata, sections, questions, marks, sources, and choice groups.

Important History-specific behavior:

1. Identify Section A as source-based if it contains sources and Q1(a)-Q1(e).
2. Identify Section B as essays.
3. Preserve `OR` relationships for Q2(a)/(b).
4. Extract marks in brackets.
5. Include image-based source placeholders when text extraction only captures captions.

### `prompts/map_question_to_syllabus.j2`

Purpose: map each question to assessment objective and syllabus topic.

Output per question:

```json
{
  "question_id": "1(a)",
  "predicted_objectives": ["AO1", "AO3"],
  "predicted_topic": "Key developments leading to the outbreak of World War II in Europe",
  "evidence_from_question": "How useful is this source...",
  "evidence_from_syllabus": "Objective 3: Interpret and Evaluate Source Materials",
  "confidence": 0.91,
  "ambiguity_notes": []
}
```

### `prompts/evaluate_model_output.j2`

Purpose: ask a separate model pass to critique the extraction and annotation.

Checks:

1. Does every question have marks?
2. Are all source references valid?
3. Are AO labels plausible?
4. Are topic labels supported by syllabus text?
5. Did the model confuse offered essay marks with candidate-required marks?

## Semantic Comparison

After topic extraction, the MVP uses a deterministic History-specific semantic matcher to map question wording to syllabus fields. This is intentionally auditable for the case study. Embeddings or a cross-encoder can be added later for broader subject coverage.

MVP approach:

1. Read each question prompt and source requirement.
2. Apply source-based and essay command-word rules for AO mapping.
3. Match key topic terms such as appeasement, Versailles, colonisation, Japan, and Asia-Pacific.
4. Return a syllabus topic id, evidence text, and confidence.
5. Persist the result inside the comparison report for review.

This auditable approach is more reliable for the current History-only launcher than making the LLM search the whole syllabus from scratch.
