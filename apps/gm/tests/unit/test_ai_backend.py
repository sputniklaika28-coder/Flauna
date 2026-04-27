"""Unit tests for the LLMBackend protocol and the in-memory mock."""

from __future__ import annotations

import pytest

from tacex_gm.ai import (
    LLMBackend,
    LLMResponse,
    Message,
    MockLLMBackend,
    ToolCall,
    ToolDefinition,
    text_response,
    tool_response,
)


def sample_tool() -> ToolDefinition:
    return ToolDefinition(
        name="do_simple_attack",
        description="Attack the given target with a basic weapon strike.",
        input_schema={
            "type": "object",
            "properties": {"target_id": {"type": "string"}},
            "required": ["target_id"],
        },
    )


class TestProtocolConformance:
    def test_mock_backend_satisfies_protocol(self) -> None:
        backend: LLMBackend = MockLLMBackend()
        assert isinstance(backend, LLMBackend)
        assert backend.name == "mock"


class TestScriptedResponses:
    @pytest.mark.asyncio
    async def test_replays_in_order(self) -> None:
        backend = MockLLMBackend([text_response("hello"), text_response("world")])
        first = await backend.chat_completion(messages=[Message("user", "hi")])
        second = await backend.chat_completion(messages=[Message("user", "again")])
        assert first.text == "hello"
        assert second.text == "world"

    @pytest.mark.asyncio
    async def test_records_calls(self) -> None:
        backend = MockLLMBackend([text_response("ok")])
        await backend.chat_completion(
            messages=[Message("user", "go")],
            tools=[sample_tool()],
            system="be terse",
            max_tokens=64,
            temperature=0.1,
            tool_choice="any",
        )
        assert len(backend.calls) == 1
        call = backend.calls[0]
        assert call.system == "be terse"
        assert call.max_tokens == 64
        assert call.tool_choice == "any"
        assert call.tools[0].name == "do_simple_attack"

    @pytest.mark.asyncio
    async def test_raises_when_exhausted(self) -> None:
        backend = MockLLMBackend()
        with pytest.raises(RuntimeError, match="exhausted"):
            await backend.chat_completion(messages=[Message("user", "x")])

    @pytest.mark.asyncio
    async def test_raises_scripted_exception(self) -> None:
        backend = MockLLMBackend([RuntimeError("provider down")])
        with pytest.raises(RuntimeError, match="provider down"):
            await backend.chat_completion(messages=[Message("user", "x")])

    @pytest.mark.asyncio
    async def test_callable_response(self) -> None:
        def reply(**kwargs: object) -> LLMResponse:
            messages = kwargs["messages"]
            assert isinstance(messages, tuple)
            return text_response(f"saw {len(messages)} messages")

        backend = MockLLMBackend([reply])
        response = await backend.chat_completion(
            messages=[Message("user", "a"), Message("assistant", "b")]
        )
        assert response.text == "saw 2 messages"

    @pytest.mark.asyncio
    async def test_callable_can_raise(self) -> None:
        def reply(**_: object) -> BaseException:
            return RuntimeError("simulated rate limit")

        backend = MockLLMBackend([reply])
        with pytest.raises(RuntimeError, match="rate limit"):
            await backend.chat_completion(messages=[Message("user", "x")])

    @pytest.mark.asyncio
    async def test_callable_must_return_llm_response(self) -> None:
        def reply(**_: object) -> str:
            return "oops"

        backend = MockLLMBackend([reply])  # type: ignore[list-item]
        with pytest.raises(TypeError):
            await backend.chat_completion(messages=[Message("user", "x")])

    @pytest.mark.asyncio
    async def test_reset_clears_state(self) -> None:
        backend = MockLLMBackend([text_response("a")])
        await backend.chat_completion(messages=[Message("user", "x")])
        backend.reset()
        assert backend.calls == []
        backend.queue(text_response("b"))
        result = await backend.chat_completion(messages=[Message("user", "x")])
        assert result.text == "b"


class TestToolResponseFactories:
    def test_text_response_default_stop_reason(self) -> None:
        resp = text_response("ok")
        assert resp.stop_reason == "end_turn"
        assert resp.tool_calls == ()

    def test_tool_response_carries_call(self) -> None:
        resp = tool_response("do_simple_attack", {"target_id": "alice"}, call_id="c1")
        assert resp.stop_reason == "tool_use"
        assert resp.tool_calls == (
            ToolCall(id="c1", name="do_simple_attack", input={"target_id": "alice"}),
        )
