from __future__ import annotations

from types import SimpleNamespace

from app.config import OpenAIConfig
from app.llm.openai_responses import OpenAIResponsesAdapter


class FakeConversations:
    def __init__(self) -> None:
        self.calls = 0

    def create(self):
        self.calls += 1
        return SimpleNamespace(id="conv_openai_001")


class FakeResponses:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def create(self, **payload):
        self.payloads.append(payload)
        return SimpleNamespace(id="resp_openai_001", output_text="Respuesta con [evd_001].")


class FakeOpenAI:
    def __init__(self) -> None:
        self.conversations = FakeConversations()
        self.responses = FakeResponses()


def test_openai_adapter_creates_and_uses_conversation() -> None:
    client = FakeOpenAI()
    adapter = OpenAIResponsesAdapter(
        client=client,  # type: ignore[arg-type]
        config=OpenAIConfig(api_key="test", model="gpt-5.4", reasoning_effort="medium"),
    )

    conversation_id = adapter.create_conversation()
    output = adapter.answer_conversation(
        prompt="Explica AAPL.",
        instructions="Usa evidencia.",
        fallback_content="Fallback.",
        provider_conversation_id=conversation_id,
    )

    assert conversation_id == "conv_openai_001"
    assert output.content == "Respuesta con [evd_001]."
    assert output.response_id == "resp_openai_001"
    assert client.responses.payloads[0]["conversation"] == "conv_openai_001"
    assert client.responses.payloads[0]["model"] == "gpt-5.4"
