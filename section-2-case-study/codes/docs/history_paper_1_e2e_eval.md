# History Paper 1 End-to-End Eval

This runbook reproduces the end-to-end local model pipeline and eval scoring for History 2174 Paper 1.

## Input

- Paper PDF: `data/raw/exam_pdfs/2174_specimen_paper_1.pdf`
- Gold fixture: `tests/fixtures/history_2174_paper_1_gold.json`
- Provider: `mock`

The mock provider is deterministic and does not require LM Studio, Ollama, or network access.

## 1. Run The End-To-End Pipeline

From the repository root:

```bash
python3 scripts/run_e2e_local_model_test.py \
  --pdf data/raw/exam_pdfs/2174_specimen_paper_1.pdf \
  --provider mock
```

The command prints a generated `job_id`. Example:

```text
job_id=c1aaf24be796
report=/Users/YLChua/Desktop/govtech/section-2-case-study/data/processed/json/c1aaf24be796/comparison_report.json
provider=mock
subject=History
total_marks=50
issues=0
```

Use the generated `job_id` in the next steps. Do not hard-code the example value unless you are intentionally inspecting that prior run.

## 2. Run The Eval Scorer

Replace `<job_id>` with the value printed by the pipeline:

```bash
python3 evals/evaluate_outputs.py \
  --job-id <job_id> \
  --reference tests/fixtures/history_2174_paper_1_gold.json
```

Expected successful summary:

```json
{
  "keys_evaluated": 28,
  "accuracy_exact_match_rate": 1.0,
  "accuracy_avg_textual_similarity": 1.0,
  "completeness_rate": 1.0,
  "hallucination_rate": 0.0,
  "failed_keys": [],
  "hallucinated_keys": []
}
```

The eval command writes:

```text
evals/runs/<timestamp>_<job_id>/summary.json
evals/runs/<timestamp>_<job_id>/eval_record.json
```

## 3. Inspect Generated Output

The generated report is:

```text
data/processed/json/<job_id>/comparison_report.json
```

For the example run above, the report can be opened here:

[Open example comparison report](../data/processed/json/c1aaf24be796/comparison_report.json)

Pretty-print the comparison report:

```bash
python3 -m json.tool data/processed/json/<job_id>/comparison_report.json
```

List the generated pipeline artifacts:

```bash
find data/processed/json/<job_id> -maxdepth 1 -type f -print
```

Expected files:

```text
data/processed/json/<job_id>/raw_extraction.json
data/processed/json/<job_id>/exam_structure.json
data/processed/json/<job_id>/comparison_report.json
data/processed/json/<job_id>/audit_log.json
data/processed/json/<job_id>/raw_model_response.json
```

## 4. Download The Report

Copy the generated comparison report to your Downloads folder:

```bash
cp data/processed/json/<job_id>/comparison_report.json ~/Downloads/history-paper-1-comparison-report-<job_id>.json
```

After replacing `<job_id>`, the downloaded report will be available at:

```text
~/Downloads/history-paper-1-comparison-report-<job_id>.json
```

For the example run, use:

```bash
cp data/processed/json/c1aaf24be796/comparison_report.json ~/Downloads/history-paper-1-comparison-report-c1aaf24be796.json
```

Example downloaded report hyperlink:

[Open downloaded example report](../../../../Downloads/history-paper-1-comparison-report-c1aaf24be796.json)

## Pass Criteria

- Pipeline exits with status `0`.
- `issues=0` in the pipeline output.
- `subject=History`.
- `total_marks=50`.
- Eval exits with status `0`.
- `accuracy_exact_match_rate` is `1.0`.
- `completeness_rate` is `1.0`.
- `hallucination_rate` is `0.0`.
- `failed_keys` and `hallucinated_keys` are empty arrays.

## Notes

- `comparison_report.json` includes extracted exam source text and can be large.
- The Paper 1 comparison report should classify Section A under `Key developments leading to the outbreak of World War II in Europe`.
- Section B has 40 offered marks in the extracted paper, but candidate-experienced Section B marks are 20 because candidates answer two essay questions.
