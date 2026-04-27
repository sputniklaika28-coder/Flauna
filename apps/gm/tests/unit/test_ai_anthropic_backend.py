"""Unit tests for the AnthropicBackend adapter.

Anthropic API is **not** called — we stub ``anthropic.AsyncAnthropic`` with a
fake whose ``messages.create`` returns canned response objects so the
translation logic is tested deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import anthropic
import httpx
import pytest

from tacex_gm.ai import AnthropicBackend, Message, ToolDefinition
from tacex_gm.ai.backend import LLMBackendError


@dataclass
class _FakeBlock:
    type: str
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict[str, Any] | None = None


@dataclass
class _FakeUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class _FakeAnthropicMessage:
    content: list[_FakeBlock]
    stop_reason: str | None
    usage: _FakeUsage


class _FakeMessages:
    def __init__(self, response: _FakeAnthropicMessage | Exception) -> None:
        self._response = response
        self.last_request: dict[str, Any] | None = None

    async def create(self, **kwargs: Any) -> _FakeAnthropicMessage:
        self.last_request = kwargs
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class _FakeClient:
    def __init__(self, response: _FakeAnthropicMessage | Exception) -> None:
        self.messages = _FakeMessages(response)


def make_backend(response: _FakeAnthropicMessage | Exception) -> AnthropicBackend:
    fake = _FakeClient(response)
    return AnthropicBackend(api_key="test", client=fake)  # type: ignore[arg-type]


class TestConstruction:
    def test_requires_api_key_when_no_client(self) -> None:
        with pytest.raises(ValueError, match="api_key"):
            AnthropicBackend(api_key="")


class TestRequestTranslation:
    @pytest.mark.asyncio
    async def test_extracts_system_message(self) -> None:
        backend = make_backend(
            _FakeAnthropicMessage(
                content=[_FakeBlock(type="text", text="ok")],
                stop_reason="end_turn",
                usage=_FakeUsage(input_tokens=1, output_tokens=2),
            )
        )
        await backend.chat_completion(
            messages=[
                Message("system", "you are a strict GM"),
                Message("user", "hello"),
            ]
        )
        client = backend._client  # type: ignore[attr-defined]
        request = client.messages.last_request
        assert request is not None
        assert request["system"] == "you are a strict GM"
        assert request["messages"] == [{"role": "user", "content": "hello"}]

    @pytest.mark.asyncio
    async def test_explicit_system_overrides_embedded(self) -> None:
        backend = make_backend(
            _FakeAnthropicMessage(
                content=[],
                stop_reason="end_turn",
                usage=_FakeUsage(),
            )
        )
        await backend.chat_completion(
            messages=[Message("system", "embedded"), Message("user", "hi")],
            system="explicit",
        )
        request = backend._client.messages.last_request  # type: ignore[attr-defined]
        assert request["system"] == "explicit"

    @pytest.mark.asyncio
    async def test_translates_tools(self) -> None:
        backend = make_backend(
            _FakeAnthropicMessage(
                content=[],
                stop_reason="end_turn",
                usage=_FakeUsage(),
            )
        )
        tool = ToolDefinition(
            name="do_simple_attack",
            description="Strike the target.",
            input_schema={
                "type": "object",
                "properties": {"target_id": {"type": "string"}},
            },
        )
        await backend.chat_completion(
            messages=[Message("user", "act")],
            tools=[tool],
            tool_choice="any",
        )
        request = backend._client.messages.last_request  # type: ignore[attr-defined]
        assert request["tools"] == [
            {
                "name": "do_simple_attack",
                "description": "Strike the target.",
                "input_schema": {
                    "type": "object",
                    "properties": {"target_id": {"type": "string"}},
                },
            }
        ]
        assert request["tool_choice"] == {"type": "any"}


class TestResponseTranslation:
    @pytest.mark.asyncio
    async def test_text_only(self) -> None:
        backend = make_backend(
            _FakeAnthropicMessage(
                content=[
                    _FakeBlock(type="text", text="hello"),
                    _FakeBlock(type="text", text=" world"),
                ],
                stop_reason="end_turn",
                usage=_FakeUsage(input_tokens=10, output_tokens=4),
            )
        )
        response = await backend.chat_completion(messages=[Message("user", "hi")])
        assert response.text == "hello world"
        assert response.tool_calls == ()
        assert response.stop_reason == "end_turn"
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 4

    @pytest.mark.asyncio
    async def test_tool_use(self) -> None:
        backend = make_backend(
            _FakeAnthropicMessage(
                content=[
                    _FakeBlock(type="text", text="thinking..."),
                    _FakeBlock(
                        type="tool_use",
                        id="toolu_1",
                        name="do_simple_attack",
                        input={"target_id": "alice"},
                    ),
                ],
                stop_reason="tool_use",
                usage=_FakeUsage(input_tokens=10, output_tokens=4),
            )
        )
        response = await backend.chat_completion(messages=[Message("user", "act")])
        assert response.text == "thinking..."
        assert response.stop_reason == "tool_use"
        assert response.tool_calls[0].name == "do_simple_attack"
        assert response.tool_calls[0].input == {"target_id": "alice"}
        assert response.tool_calls[0].id == "toolu_1"

    @pytest.mark.asyncio
    async def test_unknown_stop_reason_normalises_to_error(self) -> None:
        backend = make_backend(
            _FakeAnthropicMessage(
                content=[],
                stop_reason="weird_reason",
                usage=_FakeUsage(),
            )
        )
        response = await backend.chat_completion(messages=[Message("user", "x")])
        assert response.stop_reason == "error"


class TestErrorPath:
    @pytest.mark.asyncio
    async def test_api_error_raises_llm_backend_error(self) -> None:
        request = httpx.Request("POST", "https://api.anthropic.test")
        backend = make_backend(anthropic.APIError("boom", request=request, body=None))
        with pytest.raises(LLMBackendError, match="anthropic"):
            await backend.chat_completion(messages=[Message("user", "x")])
