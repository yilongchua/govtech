from __future__ import annotations

from pathlib import Path

from backend.app.schemas.exam import FirstPageCheck
from backend.app.src.ingestion.model_client import LLMClient
from backend.app.src.prompts import render_prompt


def classify_first_page(image_path: Path, model_client: LLMClient) -> FirstPageCheck:
    prompt = render_prompt("classify_first_page.j2", FirstPageCheck)
    raw = model_client.classify_first_page(image_path, prompt)
    return FirstPageCheck(**raw)
