"""Anthropic SDK adapter for :class:`LLMBackend` (GM spec §3-2, §15-2 item 4).

Maps the provider-agnostic backend protocol onto ``anthropic.AsyncAnthropic``:

- ``Message`` / ``ToolDefinition`` are translated at the call boundary.
- The provider-native ``Message`` object is preserved on
  :attr:`LLMResponse.raw` for debugging.
- Errors surface as :class:`LLMBackendError` so the orchestration layer can
  apply the simplified retry policy (§11-1, max 2 attempts) without
  importing provider-specific exception types.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal, cast

import anthropic

from .backend import (
    LLMBackend,
    LLMBackendError,
    LLMResponse,
    Message,
    StopReason,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)

DEFAULT_MODEL = "claude-sonnet-4-5"


class AnthropicBackend(LLMBackend):
    """Concrete backend wrapping ``anthropic.AsyncAnthropic``."""

    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("AnthropicBackend requires either api_key or a client")
        self.model = model
        self._client = client or anthropic.AsyncAnthropic(api_key=api_key)

    async def chat_completion(
        self,
        *,
        messages: Sequence[Message],
        tools: Sequence[ToolDefinition] = (),
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        tool_choice: Literal["auto", "any", "none"] = "auto",
    ) -> LLMResponse:
        request: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [_to_anthropic_message(m) for m in messages if m.role != "system"],
        }

        # Anthropic accepts the system prompt as a top-level argument; if the
        # caller embedded a system message we honour it but prefer the explicit
        # ``system`` parameter when both are supplied.
        explicit_system = system
        embedded_system = next((m.content for m in messages if m.role == "system"), None)
        merged_system = explicit_system or embedded_system
        if merged_system is not None:
            request["system"] = merged_system

        if tools:
            request["tools"] = [_to_anthropic_tool(t) for t in tools]
            request["tool_choice"] = {"type": tool_choice}

        try:
            response = await self._client.messages.create(**request)
        except anthropic.APIError as exc:
            raise LLMBackendError(f"anthropic API error: {exc}") from exc

        return _from_anthropic_response(response)


def _to_anthropic_message(message: Message) -> dict[str, Any]:
    if message.role == "system":
        # Should not happen — the caller filters system messages out — but
        # guard anyway so a misuse fails loudly instead of silently dropping.
        raise ValueError("system messages must be passed via the 'system' argument")
    return {"role": message.role, "content": message.content}


def _to_anthropic_tool(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }


def _from_anthropic_response(response: anthropic.types.Message) -> LLMResponse:
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=block.id,
                    name=block.name,
                    input=cast(dict[str, Any], block.input or {}),
                )
            )

    stop_reason = _normalise_stop_reason(response.stop_reason)

    usage = TokenUsage(
        input_tokens=getattr(response.usage, "input_tokens", 0) or 0,
        output_tokens=getattr(response.usage, "output_tokens", 0) or 0,
    )

    return LLMResponse(
        text="".join(text_parts),
        tool_calls=tuple(tool_calls),
        stop_reason=stop_reason,
        usage=usage,
        raw=response,
    )


def _normalise_stop_reason(value: str | None) -> StopReason:
    mapping: dict[str, StopReason] = {
        "end_turn": "end_turn",
        "tool_use": "tool_use",
        "max_tokens": "max_tokens",
        "stop_sequence": "stop_sequence",
    }
    if value is None:
        return "end_turn"
    return mapping.get(value, "error")


__all__ = ["DEFAULT_MODEL", "AnthropicBackend"]
