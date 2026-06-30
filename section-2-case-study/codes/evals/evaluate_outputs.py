from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.metrics import evaluate_key  # noqa: E402


DATA_DIR = ROOT / "data"
RUNS_DIR = ROOT / "evals" / "runs"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate stored LLM/pipeline outputs per extracted key.")
    parser.add_argument("--job-id", required=True, help="Job id under data/processed/json and data/processed/markdown.")
    parser.add_argument("--reference", type=Path, help="Optional gold/reference JSON for accuracy metrics.")
    parser.add_argument(
        "--keys",
        nargs="*",
        help="Optional keys to evaluate. Supports summary keys like paper_code and dot paths like exam.paper_code.",
    )
    args = parser.parse_args()

    job_id = args.job_id
    artifacts = load_artifacts(job_id)
    reference = load_json(args.reference) if args.reference else {}
    predicted_view = build_predicted_view(artifacts)
    keys = args.keys or sorted(reference.keys()) or default_keys(predicted_view)

    paper_text = artifacts["paper_text"]
    per_key = []
    for key in expand_keys(keys, reference, predicted_view):
        predicted = get_key(predicted_view, key)
        expected = get_key(reference, key)
        per_key.append(evaluate_key(key, predicted, expected, paper_text, required=True))

    summary = summarize(per_key)
    run_dir = RUNS_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{job_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    evidence = {
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "reference_path": str(args.reference) if args.reference else None,
            "keys": keys,
        },
        "prompts": artifacts["prompts"],
        "outputs": {
            "raw_model_response": artifacts["raw_model_response"],
            "raw_extraction": artifacts["raw_extraction"],
            "exam_structure": artifacts["exam_structure"],
            "comparison_report": artifacts["comparison_report"],
        },
        "reference": reference,
        "results": {
            "summary": summary,
            "per_key": per_key,
        },
    }
    write_json(run_dir / "eval_record.json", evidence)
    write_json(run_dir / "summary.json", summary)

    print(json.dumps({"run_dir": str(run_dir), "summary": summary}, indent=2))


def load_artifacts(job_id: str) -> dict[str, Any]:
    json_dir = DATA_DIR / "processed" / "json" / job_id
    markdown_path = DATA_DIR / "processed" / "markdown" / job_id / "exam.md"
    raw_model_response = load_json(json_dir / "raw_model_response.json")
    return {
        "raw_model_response": raw_model_response,
        "raw_extraction": load_json(json_dir / "raw_extraction.json"),
        "exam_structure": load_json(json_dir / "exam_structure.json"),
        "comparison_report": load_json(json_dir / "comparison_report.json"),
        "paper_text": markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else "",
        "prompts": extract_prompts(raw_model_response),
    }


def extract_prompts(raw_model_response: dict[str, Any]) -> list[dict[str, Any]]:
    prompt = raw_model_response.get("prompt")
    if prompt:
        return [
            {
                "name": "first_page_check",
                "prompt_version": raw_model_response.get("prompt_version"),
                "prompt": prompt,
                "raw_response": raw_model_response.get("raw_response"),
            }
        ]
    return [
        {
            "name": "first_page_check",
            "prompt_version": raw_model_response.get("prompt_version"),
            "prompt": None,
            "raw_response": raw_model_response.get("raw_response"),
            "warning": "Prompt text was not stored for this older output. Re-run the analysis to capture prompts.",
        }
    ]


def build_predicted_view(artifacts: dict[str, Any]) -> dict[str, Any]:
    exam = artifacts["exam_structure"]
    report = artifacts["comparison_report"]
    annotations = {item["question_id"]: item for item in report.get("annotations", [])}
    topic_weightage = {item["topic"]: {"required_marks": item.get("required_marks"), "offered_marks": item.get("offered_marks")} for item in report.get("topic_weightage", [])}
    section_a_marks = sum(q.get("marks") or 0 for q in exam.get("questions", []) if q.get("section") == "A")
    section_b_marks = sum(q.get("marks") or 0 for q in exam.get("questions", []) if q.get("section") == "B")
    return {
        "raw_model_response": artifacts["raw_model_response"],
        "raw_extraction": artifacts["raw_extraction"],
        "exam": exam,
        "report": report,
        "paper_code": exam.get("paper_code"),
        "total_marks": exam.get("total_marks"),
        "section_a_marks": section_a_marks,
        "section_b_candidate_marks": 20 if section_b_marks else None,
        "question_count": len(exam.get("questions", [])),
        "source_count": len(exam.get("sources", [])),
        "topics": {qid: item.get("predicted_topic") for qid, item in annotations.items()},
        "objectives": {qid: item.get("predicted_objectives") for qid, item in annotations.items()},
        "topic_weightage": topic_weightage,
    }


def default_keys(predicted_view: dict[str, Any]) -> list[str]:
    keys = ["paper_code", "total_marks", "question_count", "source_count"]
    keys.extend(f"topics.{qid}" for qid in predicted_view.get("topics", {}))
    keys.extend(f"objectives.{qid}" for qid in predicted_view.get("objectives", {}))
    return keys


def expand_keys(keys: list[str], reference: dict[str, Any], predicted_view: dict[str, Any]) -> list[str]:
    expanded: list[str] = []
    for key in keys:
        ref_value = get_key(reference, key)
        pred_value = get_key(predicted_view, key)
        if isinstance(ref_value, dict):
            expanded.extend(f"{key}.{child}" for child in sorted(ref_value))
        elif isinstance(pred_value, dict):
            expanded.extend(f"{key}.{child}" for child in sorted(pred_value))
        else:
            expanded.append(key)
    return expanded


def get_key(payload: Any, dotted_key: str) -> Any:
    current = payload
    for part in dotted_key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def summarize(per_key: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(per_key)
    exact_values = [item["accuracy"]["exact_match"] for item in per_key if item["accuracy"]["exact_match"] is not None]
    similarity_values = [
        item["accuracy"]["textual_similarity"]
        for item in per_key
        if item["accuracy"]["textual_similarity"] is not None
    ]
    return {
        "keys_evaluated": total,
        "accuracy_exact_match_rate": safe_rate(exact_values),
        "accuracy_avg_textual_similarity": round(sum(similarity_values) / len(similarity_values), 4) if similarity_values else None,
        "completeness_rate": safe_rate([item["completeness"]["present"] for item in per_key]),
        "hallucination_rate": safe_rate([item["hallucination"]["hallucinated"] for item in per_key]),
        "failed_keys": [item["key"] for item in per_key if item["completeness"]["failed_to_obtain"]],
        "hallucinated_keys": [item["key"] for item in per_key if item["hallucination"]["hallucinated"]],
    }


def safe_rate(values: list[bool], *, positive_value: bool = True) -> float | None:
    if not values:
        return None
    positives = sum(1 for value in values if value is positive_value)
    return round(positives / len(values), 4)


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
