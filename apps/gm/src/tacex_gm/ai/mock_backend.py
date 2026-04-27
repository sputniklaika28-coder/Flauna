"""In-memory ``LLMBackend`` for tests and golden masters (GM spec §16-7).

The mock is *scripted*: configure a sequence of responses (or per-call
callables) and the backend replays them in order. Three response shapes are
supported so callers can exercise the retry / fallback paths:

- Pre-built :class:`LLMResponse` instances are returned as-is.
- Bare exceptions are raised at call time, simulating provider errors.
- A callable is invoked with the call kwargs and may return a response
  or raise; this lets tests build context-sensitive replies.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .backend import LLMBackend, LLMResponse, Message, ToolCall, ToolDefinition

ScriptedResponse = (
    LLMResponse
    | BaseException
    | Callable[..., LLMResponse | BaseException | Awaitable[LLMResponse]]
)


@dataclass
class MockCall:
    """Recorded chat_completion invocation, useful for assertions."""

    messages: tuple[Message, ...]
    tools: tuple[ToolDefinition, ...]
    system: str | None
    max_tokens: int
    temperature: float
    tool_choice: Literal["auto", "any", "none"]


class MockLLMBackend(LLMBackend):
    """Replays a deterministic script of responses."""

    name = "mock"

    def __init__(self, responses: Sequence[ScriptedResponse] | None = None) -> None:
        self._responses: list[ScriptedResponse] = list(responses or [])
        self.calls: list[MockCall] = []

    def queue(self, response: ScriptedResponse) -> None:
        self._responses.append(response)

    def reset(self) -> None:
        self._responses.clear()
        self.calls.clear()

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
        self.calls.append(
            MockCall(
                messages=tuple(messages),
                tools=tuple(tools),
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                tool_choice=tool_choice,
            )
        )
        if not self._responses:
            raise RuntimeError("MockLLMBackend exhausted: no scripted response available")
        item = self._responses.pop(0)

        if callable(item) and not isinstance(item, BaseException):
            kwargs: dict[str, Any] = {
                "messages": tuple(messages),
                "tools": tuple(tools),
                "system": system,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "tool_choice": tool_choice,
            }
            result = item(**kwargs)
            if hasattr(result, "__await__"):
                result = await result
            if isinstance(result, BaseException):
                raise result
            if not isinstance(result, LLMResponse):
                raise TypeError(
                    f"MockLLMBackend callable must return LLMResponse, got {type(result).__name__}"
                )
            return result

        if isinstance(item, BaseException):
            raise item
        return item


def text_response(text: str) -> LLMResponse:
    """Convenience factory for a plain-text completion."""

    return LLMResponse(text=text, stop_reason="end_turn")


def tool_response(
    name: str,
    input_payload: dict[str, Any],
    *,
    call_id: str = "call_1",
) -> LLMResponse:
    """Convenience factory for a single-tool response."""

    return LLMResponse(
        tool_calls=(ToolCall(id=call_id, name=name, input=input_payload),),
        stop_reason="tool_use",
    )


__all__ = [
    "MockCall",
    "MockLLMBackend",
    "ScriptedResponse",
    "text_response",
    "tool_response",
]
