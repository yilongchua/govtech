from __future__ import annotations

from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.core.config import get_model_settings, save_model_settings
from backend.app.src.ingestion.model_client import LLMClient
from backend.app.src.ingestion.model_preflight import check_text_json_capability

router = APIRouter(prefix="/api/model-settings", tags=["model-settings"])

Provider = Literal["lm-studio", "openai-compatible", "ollama", "mock"]


class ModelSettingsPayload(BaseModel):
    provider: Provider = "lm-studio"
    base_url: str = Field(..., min_length=1)
    model: str = Field("", min_length=0)
    timeout_seconds: float = Field(60.0, gt=0)


def _client_from_payload(payload: ModelSettingsPayload) -> LLMClient:
    return LLMClient(provider=payload.provider, base_url=payload.base_url, model=payload.model, timeout=payload.timeout_seconds)


def _connection_error(exc: Exception) -> HTTPException:
    if isinstance(exc, httpx.HTTPStatusError):
        detail = f"Model server returned HTTP {exc.response.status_code}."
    elif isinstance(exc, httpx.RequestError):
        detail = f"Could not reach model server: {exc}"
    else:
        detail = str(exc)
    return HTTPException(status_code=400, detail=detail)


@router.get("")
def get_settings() -> dict:
    model_settings = get_model_settings()
    return {
        "provider": model_settings.provider,
        "base_url": model_settings.base_url,
        "model": model_settings.model,
        "timeout_seconds": model_settings.timeout_seconds,
    }


@router.put("")
def update_settings(payload: ModelSettingsPayload) -> dict:
    model_settings = save_model_settings(payload.provider, payload.base_url, payload.model, payload.timeout_seconds)
    return {
        "provider": model_settings.provider,
        "base_url": model_settings.base_url,
        "model": model_settings.model,
        "timeout_seconds": model_settings.timeout_seconds,
    }


@router.post("/models")
def list_models(payload: ModelSettingsPayload) -> dict:
    try:
        return {"models": _client_from_payload(payload).list_models()}
    except Exception as exc:
        raise _connection_error(exc) from exc


@router.post("/test")
def test_connection(payload: ModelSettingsPayload) -> dict:
    try:
        client = _client_from_payload(payload)
        result = client.test_connection()
        issue, artifact = check_text_json_capability(client)
        result["text_json_preflight"] = artifact
        result["text_json_ok"] = issue is None
        if issue is not None:
            result["text_json_issue"] = issue.model_dump(mode="json")
        return result
    except Exception as exc:
        raise _connection_error(exc) from exc
