from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx


class LLMClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        provider: str = "openai-compatible",
        timeout: float = 60.0,
        mock_json_response: dict[str, Any] | str | None = None,
    ):
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.mock_json_response = mock_json_response
        self.last_raw_response: str | dict | None = None
        self.last_reasoning_content: str | None = None
        self.last_prompt: str | None = None

    def classify_first_page(self, image_path: Path, prompt: str) -> dict[str, Any]:
        self.last_prompt = prompt
        if self.provider == "mock":
            self.last_raw_response = "mock"
            return {
                "is_exam_paper": True,
                "subject": "History",
                "paper_code": "2174/01",
                "paper_title": "Paper 1 Extension of European control in Southeast Asia and challenges to European dominance",
                "exam_year": 2024,
                "reasons": ["Mock classifier for deterministic local testing."],
                "_raw_response": "mock",
            }
        if self.provider == "ollama":
            return self._ollama_vision(image_path, prompt)
        return self._openai_compatible_vision(image_path, prompt)

    def complete_image_json(self, image_path: Path, prompt: str) -> dict[str, Any]:
        self.last_prompt = prompt
        if self.provider == "mock":
            self.last_raw_response = "mock"
            raise ValueError("Configured LLM provider does not support vision interpretation in mock mode.")
        if self.provider == "ollama":
            return self._ollama_vision(image_path, prompt)
        return self._openai_compatible_vision(image_path, prompt)

    def complete_json(self, prompt: str) -> dict[str, Any]:
        self.last_prompt = prompt
        if self.provider == "mock":
            if isinstance(self.mock_json_response, list):
                self.last_raw_response = self.mock_json_response.pop(0) if self.mock_json_response else {}
            else:
                self.last_raw_response = self.mock_json_response if self.mock_json_response is not None else {}
            if isinstance(self.last_raw_response, str):
                return _json_from_text(self.last_raw_response)
            return dict(self.last_raw_response)
        if self.provider == "ollama":
            return self._ollama_text_json(prompt)
        return self._openai_compatible_text_json(prompt)

    def list_models(self) -> list[str]:
        if self.provider == "mock":
            return ["mock"]
        if self.provider == "ollama":
            response = httpx.get(f"{self.base_url}/api/tags", timeout=self.timeout)
            response.raise_for_status()
            return [item["name"] for item in response.json().get("models", []) if item.get("name")]
        response = httpx.get(f"{self.base_url}/models", timeout=self.timeout)
        response.raise_for_status()
        return [item["id"] for item in response.json().get("data", []) if item.get("id")]

    def test_connection(self) -> dict[str, Any]:
        models = self.list_models()
        return {
            "ok": True,
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "models": models,
            "model_available": not self.model or self.model in models,
        }

    def _openai_compatible_vision(self, image_path: Path, prompt: str) -> dict[str, Any]:
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{encoded}"},
                        },
                    ],
                }
            ],
            "temperature": 0,
        }
        response = httpx.post(f"{self.base_url}/chat/completions", json=payload, timeout=self.timeout)
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        content = message.get("content") or ""
        self.last_reasoning_content = message.get("reasoning_content")
        self.last_raw_response = {
            "content": content,
            "reasoning_content": self.last_reasoning_content,
            "finish_reason": response.json().get("choices", [{}])[0].get("finish_reason"),
        }
        if not content and self.last_reasoning_content:
            raise ValueError("Model response content was empty while reasoning_content was present. The local model likely exhausted its output budget before emitting JSON.")
        parsed = _json_from_text(content)
        parsed["_raw_response"] = content
        return parsed

    def _ollama_vision(self, image_path: Path, prompt: str) -> dict[str, Any]:
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        payload = {"model": self.model, "prompt": prompt, "images": [encoded], "stream": False, "format": "json"}
        response = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
        response.raise_for_status()
        content = response.json().get("response", "{}")
        self.last_raw_response = content
        parsed = _json_from_text(content)
        parsed["_raw_response"] = content
        return parsed

    def _openai_compatible_text_json(self, prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        response = httpx.post(f"{self.base_url}/chat/completions", json=payload, timeout=self.timeout)
        response.raise_for_status()
        response_json = response.json()
        choice = response_json["choices"][0]
        message = choice["message"]
        content = message.get("content") or ""
        self.last_reasoning_content = message.get("reasoning_content")
        self.last_raw_response = {
            "content": content,
            "reasoning_content": self.last_reasoning_content,
            "finish_reason": choice.get("finish_reason"),
        }
        if not content and self.last_reasoning_content:
            raise ValueError("Model response content was empty while reasoning_content was present. The local model likely exhausted its output budget before emitting JSON.")
        parsed = _json_from_text(content)
        parsed["_raw_response"] = content
        return parsed

    def _ollama_text_json(self, prompt: str) -> dict[str, Any]:
        payload = {"model": self.model, "prompt": prompt, "stream": False, "format": "json"}
        response = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
        response.raise_for_status()
        content = response.json().get("response", "{}")
        self.last_raw_response = content
        parsed = _json_from_text(content)
        parsed["_raw_response"] = content
        return parsed


def _json_from_text(text: str) -> dict[str, Any]:
    import json
    import re

    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        if text.strip():
            raise ValueError("Model response did not contain a JSON object.")
        raise ValueError("Model response was empty.")
    return json.loads(match.group(0))


class LocalModelClient(LLMClient):
    def __init__(
        self,
        provider: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
        mock_json_response: dict[str, Any] | str | None = None,
    ):
        super().__init__(
            base_url=base_url,
            model=model,
            provider=provider,
            timeout=timeout,
            mock_json_response=mock_json_response,
        )
