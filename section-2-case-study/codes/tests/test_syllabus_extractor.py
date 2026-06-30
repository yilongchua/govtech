from pathlib import Path

import pytest

from backend.app.core import config as config_module
from backend.app.src.ingestion import model_client
from backend.app.src.ingestion.model_client import LLMClient, LocalModelClient
from backend.app.src.syllabus.llm_syllabus_extractor import SyllabusExtractionError, extract_syllabus_with_llm


def _valid_chunked_payloads(subject_code: str = "2174") -> list[dict]:
    return [
        {"subject": "History", "subject_code": subject_code, "year": 2026},
        {
            "objectives": [
                {
                    "ao_id": "AO1",
                    "name": "Deploy Knowledge",
                    "description": "select, organise and use relevant historical knowledge in context.",
                    "skills": ["select", "organise"],
                    "source_page": 5,
                }
            ],
        },
        {
            "components": [
                {
                    "paper": "2174/01",
                    "section": "A",
                    "name": "Source-Based Case Study",
                    "marks": 30,
                    "objectives": ["AO1"],
                    "rules": ["Maximum of 6 sources"],
                    "source_page": 6,
                }
            ],
        },
        {
            "topics": [
                {
                    "topic_id": "p1_wwii_europe",
                    "paper": "2174/01",
                    "unit": "War in Europe and the Asia-Pacific",
                    "topic": "Key developments leading to the outbreak of World War II in Europe",
                    "subtopics": ["appeasement"],
                    "key_concepts": ["Expansionism"],
                    "source_page": 14,
                }
            ],
        },
    ]


def _mock_client(response):
    return LocalModelClient(
        provider="mock",
        base_url="http://localhost:1234/v1",
        model="mock",
        mock_json_response=response,
    )


def test_llm_syllabus_extractor_accepts_valid_mock_output(tmp_path) -> None:
    md = tmp_path / "2174_y26_sy.md"
    pdf = tmp_path / "2174_y26_sy.pdf"
    md.write_text("## Page 5\nASSESSMENT OBJECTIVES\n", encoding="utf-8")
    pdf.write_bytes(b"not used")

    syllabus, artifact = extract_syllabus_with_llm(
        md,
        pdf,
        "https://example.test/2174_y26_sy.pdf",
        _mock_client(_valid_chunked_payloads()),
    )

    assert syllabus.subject_code == "2174"
    assert syllabus.source_url == "https://example.test/2174_y26_sy.pdf"
    assert syllabus.pdf_path == str(pdf)
    assert syllabus.markdown_path == str(md)
    assert {objective.ao_id for objective in syllabus.objectives} == {"AO1"}
    assert artifact["provider"] == "mock"
    assert [call["call"] for call in artifact["calls"]] == ["metadata", "objectives", "components", "topics"]
    assert artifact["parsed_json"]["topics"][0]["topic_id"] == "p1_wwii_europe"


@pytest.mark.parametrize("response", ["", "not json"])
def test_llm_syllabus_extractor_rejects_malformed_output(tmp_path, response) -> None:
    md = tmp_path / "2174_y26_sy.md"
    pdf = tmp_path / "2174_y26_sy.pdf"
    md.write_text("## Page 1\n", encoding="utf-8")
    pdf.write_bytes(b"not used")

    with pytest.raises(SyllabusExtractionError):
        extract_syllabus_with_llm(md, pdf, "https://example.test/2174_y26_sy.pdf", _mock_client(response))


def test_llm_syllabus_extractor_rejects_incomplete_output(tmp_path) -> None:
    md = tmp_path / "2174_y26_sy.md"
    pdf = tmp_path / "2174_y26_sy.pdf"
    md.write_text("## Page 1\n", encoding="utf-8")
    pdf.write_bytes(b"not used")
    payload = _valid_chunked_payloads()
    payload[-1] = {"topics": []}

    with pytest.raises(SyllabusExtractionError, match="topics"):
        extract_syllabus_with_llm(md, pdf, "https://example.test/2174_y26_sy.pdf", _mock_client(payload))


def test_reasoning_only_model_response_reports_clear_error(monkeypatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {"content": "", "reasoning_content": "I am still thinking."},
                        "finish_reason": "length",
                    }
                ]
            }

    monkeypatch.setattr(model_client.httpx, "post", lambda *args, **kwargs: Response())
    client = LLMClient(provider="openai-compatible", base_url="http://localhost:1234/v1", model="mock")

    with pytest.raises(ValueError, match="reasoning_content"):
        client.complete_json("Return JSON")


def test_model_settings_preserve_timeout_seconds(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.yaml")

    saved = config_module.save_model_settings("lm-studio", "http://localhost:1234/v1", "mock-model", 240)
    loaded = config_module.get_model_settings()

    assert saved.timeout_seconds == 240
    assert loaded.timeout_seconds == 240
