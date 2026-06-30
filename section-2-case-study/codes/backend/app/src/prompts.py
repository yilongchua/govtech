from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Type

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel

from backend.app.core.config import settings


PROMPT_DIR = settings.root_dir / "backend" / "app" / "prompts"


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(PROMPT_DIR),
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def schema_json(model: Type[BaseModel]) -> str:
    return json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False)


def render_prompt(template_name: str, output_model: Type[BaseModel], **context: Any) -> str:
    template = _environment().get_template(template_name)
    return template.render(output_schema=schema_json(output_model), **context)


def prompt_path(template_name: str) -> Path:
    return PROMPT_DIR / template_name
