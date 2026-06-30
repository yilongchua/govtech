from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a PDF paper to the local backend for analysis.")
    parser.add_argument("filename", type=Path, help="Path to the PDF paper, e.g. python test_send_paper.py filename.pdf")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL.")
    parser.add_argument("--timeout", type=float, default=180.0, help="Request timeout in seconds.")
    args = parser.parse_args()

    pdf_path = args.filename.expanduser().resolve()
    if not pdf_path.exists():
        raise SystemExit(f"File not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise SystemExit(f"Only PDF files are supported: {pdf_path}")

    url = f"{args.base_url.rstrip('/')}/api/uploads"
    try:
        with pdf_path.open("rb") as handle:
            response = httpx.post(
                url,
                files={"file": (pdf_path.name, handle, "application/pdf")},
                timeout=args.timeout,
            )
        response.raise_for_status()
    except httpx.ConnectError as exc:
        raise SystemExit(f"Could not connect to {url}. Start the backend first, then retry.") from exc
    except httpx.HTTPStatusError as exc:
        raise SystemExit(f"Upload failed with HTTP {exc.response.status_code}: {exc.response.text}") from exc

    payload = response.json()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    job_id = payload.get("job_id")
    if job_id:
        print(f"\nReport JSON: {args.base_url.rstrip('/')}/api/jobs/{job_id}/report")
        print(f"Report Markdown: {args.base_url.rstrip('/')}/api/jobs/{job_id}/report.md")
        print(f"Report DOCX: {args.base_url.rstrip('/')}/api/jobs/{job_id}/report.docx")


if __name__ == "__main__":
    main()
