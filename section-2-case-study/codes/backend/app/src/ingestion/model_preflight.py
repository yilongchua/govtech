from __future__ import annotations

from typing import Any

from backend.app.schemas.base import ValidationIssue
from backend.app.src.ingestion.model_client import LLMClient


MODEL_TEXT_JSON_UNHEALTHY = "MODEL_TEXT_JSON_UNHEALTHY"


def check_text_json_capability(model_client: LLMClient) -> tuple[ValidationIssue | None, dict[str, Any]]:
    prompt = (
        "Return JSON only. Reply with exactly this object and no Markdown: "
        '{"status":"ok","answer":42}'
    )
    artifact: dict[str, Any] = {
        "stage": "model_text_json_preflight",
        "prompt": prompt,
        "raw_response": None,
        "parsed_response": None,
        "ok": False,
    }
    if model_client.provider == "mock":
        artifact.update({"raw_response": "mock", "parsed_response": {"status": "ok", "answer": 42}, "ok": True})
        return None, artifact
    try:
        response = model_client.complete_json(prompt)
        response.pop("_raw_response", None)
        artifact["raw_response"] = model_client.last_raw_response
        artifact["parsed_response"] = response
        if response.get("status") != "ok" or response.get("answer") != 42:
            raise ValueError(f"Unexpected text preflight response: {response}")
        artifact["ok"] = True
        return None, artifact
    except Exception as exc:
        artifact["raw_response"] = model_client.last_raw_response
        artifact["reason"] = str(exc)
        return (
            ValidationIssue(
                code=MODEL_TEXT_JSON_UNHEALTHY,
                severity="WARNING",
                stage="model_preflight",
                message="Configured LLM failed a basic text JSON preflight check.",
                reason=str(exc),
                evidence={
                    "provider": model_client.provider,
                    "base_url": model_client.base_url,
                    "model": model_client.model,
                },
            ),
            artifact,
        )
