from __future__ import annotations

from pathlib import Path

import fitz


def render_first_page(pdf_path: Path, output_dir: Path) -> Path:
    return render_page(pdf_path, 1, output_dir)


def render_page(pdf_path: Path, page_number: int, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    if page_number < 1 or page_number > len(doc):
        raise ValueError(f"Page {page_number} is outside PDF page range 1-{len(doc)}.")
    page = doc[page_number - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    output_path = output_dir / f"page_{page_number:03d}.png"
    pix.save(output_path)
    return output_path
