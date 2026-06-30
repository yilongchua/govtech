#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.src.ingestion.pdf_to_markdown import convert_pdf_to_markdown  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    print(convert_pdf_to_markdown(Path(args.pdf), Path(args.out)))


if __name__ == "__main__":
    main()
