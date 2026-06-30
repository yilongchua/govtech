#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx

from backend.app.core.storage import new_job_id
from backend.app.src.graph.workflow import run_analysis


def preflight_model(provider: str, base_url: str | None, model: str | None) -> None:
    if provider == "mock":
        return
    if not base_url:
        raise SystemExit("--base-url is required when --require-real-model is used.")
    endpoint = base_url.rstrip("/")
    if provider == "openai-compatible":
        url = f"{endpoint}/models"
        try:
            response = httpx.get(url, timeout=10)
        except httpx.HTTPError as exc:
            raise SystemExit(f"Could not reach LM Studio/OpenAI-compatible endpoint at {url}: {exc}") from exc
        response.raise_for_status()
        models = response.json().get("data", [])
        if model and models and not any(item.get("id") == model for item in models):
            print(f"warning: model {model!r} was not listed by {url}; continuing because some servers omit custom models.")
        return
    if provider == "ollama":
        url = f"{endpoint}/api/tags"
        try:
            response = httpx.get(url, timeout=10)
        except httpx.HTTPError as exc:
            raise SystemExit(f"Could not reach Ollama endpoint at {url}: {exc}") from exc
        response.raise_for_status()
        models = response.json().get("models", [])
        if model and models and not any(item.get("name") == model for item in models):
            print(f"warning: model {model!r} was not listed by {url}; continuing because Ollama aliases may vary.")
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the exam-paper pipeline end to end against a local model provider.")
    parser.add_argument("--pdf", required=True, help="Path to exam-paper PDF.")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai-compatible", "ollama"])
    parser.add_argument("--base-url", default=None, help="LM Studio OpenAI-compatible base URL or Ollama base URL.")
    parser.add_argument("--model", default=None, help="Local model name.")
    parser.add_argument("--require-real-model", action="store_true", help="Fail before analysis unless a real LM Studio/Ollama endpoint responds.")
    args = parser.parse_args()
    if args.require_real_model and args.provider == "mock":
        raise SystemExit("--require-real-model cannot be used with --provider mock.")
    if args.require_real_model:
        preflight_model(args.provider, args.base_url, args.model)
    job_id = new_job_id()
    report = run_analysis(Path(args.pdf), job_id, provider=args.provider, base_url=args.base_url, model=args.model)
    output = ROOT / "data" / "processed" / "json" / job_id / "comparison_report.json"
    print(f"job_id={job_id}")
    print(f"report={output}")
    print(f"provider={args.provider}")
    if args.base_url:
        print(f"base_url={args.base_url}")
    if args.model:
        print(f"model={args.model}")
    print(f"subject={report['exam_paper']['subject']}")
    print(f"total_marks={report['exam_paper']['total_marks']}")
    print(f"issues={len(report['issues'])}")
    print("topic_weightage:")
    for item in report["topic_weightage"]:
        print(f"- {item['topic']}: required={item['required_marks']} offered={item['offered_marks']}")


if __name__ == "__main__":
    main()
