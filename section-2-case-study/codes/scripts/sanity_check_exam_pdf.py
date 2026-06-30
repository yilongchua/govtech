#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.src.ingestion.first_page_classifier import classify_first_page
from backend.app.src.ingestion.model_client import LocalModelClient
from backend.app.src.ingestion.page_renderer import render_first_page


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--provider", default="mock", choices=["mock", "openai-compatible", "ollama"])
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--model", default="qwen/qwen3.6-35b-a3b")
    args = parser.parse_args()
    image = render_first_page(Path(args.pdf), ROOT / "data/processed/images/sanity_check")
    check = classify_first_page(image, LocalModelClient(args.provider, args.base_url, args.model))
    print(check.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
