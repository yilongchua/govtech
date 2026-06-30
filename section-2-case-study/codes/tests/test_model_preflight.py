from backend.app.src.ingestion.model_client import LocalModelClient
from backend.app.src.ingestion.model_preflight import check_text_json_capability


def test_text_json_preflight_passes_for_mock_model() -> None:
    client = LocalModelClient(provider="mock", base_url="http://localhost:1234/v1", model="mock")

    issue, artifact = check_text_json_capability(client)

    assert issue is None
    assert artifact["ok"] is True


def test_text_json_preflight_warns_on_unexpected_response() -> None:
    client = LocalModelClient(
        provider="mock-like",
        base_url="http://localhost:1234/v1",
        model="mock",
        mock_json_response={"status": "wrong"},
    )
    client.complete_json = lambda prompt: {"status": "wrong"}

    issue, artifact = check_text_json_capability(client)

    assert issue is not None
    assert issue.code == "MODEL_TEXT_JSON_UNHEALTHY"
    assert artifact["ok"] is False
