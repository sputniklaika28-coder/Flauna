"""OpenAI-compatible adapter for :class:`LLMBackend` (GM spec §3-2, Phase 5).

This backend uses the ``openai`` Python SDK so it works with any service that
exposes an OpenAI-compatible chat-completions endpoint (e.g. a local vLLM
server, Ollama, LM Studio).  The interface is identical to
:class:`~tacex_gm.ai.anthropic_backend.AnthropicBackend` from the caller's
perspective — only the concrete HTTP client differs.

Tool definitions are translated from the provider-agnostic
:class:`~tacex_gm.ai.backend.ToolDefinition` format (``input_schema`` key) into
OpenAI's ``function`` sub-object format (``parameters`` key).

Errors surface as :class:`~tacex_gm.ai.backend.LLMBackendError` so the
retry / fallback logic in the orchestration layer needs no provider-specific
branches.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Literal

try:
    from openai import APIError as OpenAIAPIError
    from openai import AsyncOpenAI
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "openai package is required for OpenAICompatBackend. Install it with: pip install openai"
    ) from exc

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

DEFAULT_MODEL = "gpt-4o"


class OpenAICompatBackend(LLMBackend):
    """Backend wrapping the ``openai.AsyncOpenAI`` client.

    Compatible with any OpenAI-API endpoint including vLLM and Ollama.
    Set *base_url* to point at the custom endpoint.
    """

    name = "openai_compat"

    def __init__(
        self,
        *,
        api_key: str = "EMPTY",
        model: str = DEFAULT_MODEL,
        base_url: str | None = None,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.model = model
        self._client = client or AsyncOpenAI(api_key=api_key, base_url=base_url)

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
        oai_messages: list[dict[str, Any]] = []

        # System prompt: prefer explicit parameter; fall back to embedded message.
        explicit_system = system
        embedded_system = next((m.content for m in messages if m.role == "system"), None)
        merged_system = explicit_system or embedded_system
        if merged_system:
            oai_messages.append({"role": "system", "content": merged_system})

        for msg in messages:
            if msg.role == "system":
                continue
            oai_messages.append({"role": msg.role, "content": msg.content})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": oai_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if tools:
            kwargs["tools"] = [_to_openai_tool(t) for t in tools]
            # OpenAI tool_choice: "auto" | "none" | {"type": "function", ...}
            # "any" (Anthropic-specific) → "auto" for OpenAI
            oai_tc = "none" if tool_choice == "none" else "auto"
            kwargs["tool_choice"] = oai_tc

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except OpenAIAPIError as exc:
            raise LLMBackendError(f"OpenAI-compat API error: {exc}") from exc

        return _from_openai_response(response)


def _to_openai_tool(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }


def _from_openai_response(response: Any) -> LLMResponse:  # noqa: ANN401
    choice = response.choices[0]
    message = choice.message

    text = message.content or ""
    tool_calls: list[ToolCall] = []

    if message.tool_calls:
        for tc in message.tool_calls:
            try:
                input_data: dict[str, Any] = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                input_data = {}
            tool_calls.append(
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input=input_data,
                )
            )

    stop_reason = _normalise_stop_reason(choice.finish_reason)

    usage_obj = getattr(response, "usage", None)
    usage = TokenUsage(
        input_tokens=getattr(usage_obj, "prompt_tokens", 0) or 0,
        output_tokens=getattr(usage_obj, "completion_tokens", 0) or 0,
    )

    return LLMResponse(
        text=text,
        tool_calls=tuple(tool_calls),
        stop_reason=stop_reason,
        usage=usage,
        raw=response,
    )


def _normalise_stop_reason(value: str | None) -> StopReason:
    mapping: dict[str, StopReason] = {
        "stop": "end_turn",
        "tool_calls": "tool_use",
        "length": "max_tokens",
        "content_filter": "stop_sequence",
    }
    if value is None:
        return "end_turn"
    return mapping.get(value, "error")


__all__ = ["DEFAULT_MODEL", "OpenAICompatBackend"]
