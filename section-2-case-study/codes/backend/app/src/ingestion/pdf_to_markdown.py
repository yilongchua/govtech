from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader


def convert_pdf_to_markdown(pdf_path: Path, output_path: Path) -> Path:
    reader = PdfReader(str(pdf_path))
    lines = [
        f"# {pdf_path.stem}",
        "",
        f"Source PDF: `{pdf_path.name}`",
        "",
        f"Pages: {len(reader.pages)}",
        "",
    ]
    for index, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        lines.extend([f"## Page {index}", "", text or "_No extractable text found on this page._", ""])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path
