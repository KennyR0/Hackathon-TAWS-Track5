"""OpenAI client helpers for the NexoMercado agents."""

from __future__ import annotations

from openai import OpenAI

from .config import OpenAIConfig, get_openai_config


def build_openai_client(config: OpenAIConfig | None = None) -> OpenAI:
    """Create an OpenAI SDK client from the current runtime config."""

    resolved_config = config or get_openai_config()
    return OpenAI(api_key=resolved_config.api_key)


def build_responses_request(
    prompt: str,
    *,
    config: OpenAIConfig | None = None,
    system_prompt: str | None = None,
) -> dict[str, object]:
    """Build a standard Responses API payload for agentic text generation."""

    resolved_config = config or get_openai_config()
    input_items: list[dict[str, object]] = []
    if system_prompt:
        input_items.append(
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}],
            }
        )
    input_items.append(
        {
            "role": "user",
            "content": [{"type": "input_text", "text": prompt}],
        }
    )
    return {
        "model": resolved_config.model,
        "store": False,
        "reasoning": {"effort": resolved_config.reasoning_effort},
        "input": input_items,
    }
