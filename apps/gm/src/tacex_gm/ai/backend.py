"""LLM backend abstraction (GM spec §3, §4-2, §15-2 item 4).

A *backend* is the adapter between the rule engine and a chat-completion
service. The protocol is intentionally narrow:

- ``chat_completion`` runs one round-trip and returns a structured
  :class:`LLMResponse`.
- All concrete backends (Anthropic, OpenAI-compatible, mock) emit the same
  shape so the orchestration layer never branches on provider.

Tool calls are represented as plain dictionaries — schema validation lives in
the higher-level ``ai.parser`` module (Phase 2).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

MessageRole = Literal["system", "user", "assistant", "tool"]
StopReason = Literal["end_turn", "tool_use", "max_tokens", "stop_sequence", "error"]


@dataclass(frozen=True)
class Message:
    """A single chat-completion message.

    ``content`` is left as ``str`` here; backends that support multi-modal
    payloads convert at the adapter boundary so the rule engine stays simple.
    """

    role: MessageRole
    content: str


@dataclass(frozen=True)
class ToolDefinition:
    """JSON-schema tool definition (§4-1, "1ツール=1ターン").

    ``input_schema`` is a JSON Schema object — backends translate to the
    provider-specific format (Anthropic: ``input_schema``; OpenAI: nested
    ``parameters``).
    """

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """A single tool-use record produced by the model."""

    id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class LLMResponse:
    """Normalised response shape across all backends."""

    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    stop_reason: StopReason = "end_turn"
    usage: TokenUsage = field(default_factory=TokenUsage)
    raw: Any = None  # Provider-native object for debugging / retries.


class LLMBackendError(RuntimeError):
    """Raised when the underlying provider returns an unrecoverable error.

    Callers should wrap retries (§11-1) around this; the backend itself does
    not retry — that policy lives in the orchestration layer.
    """


@runtime_checkable
class LLMBackend(Protocol):
    """Provider-agnostic chat-completion entry point.

    Implementations must be safe to call concurrently from multiple rooms;
    backends typically delegate to an HTTP client that already handles
    connection pooling.
    """

    name: str

    async def chat_completion(
        self,
        *,
        messages: Sequence[Message],
        tools: Sequence[ToolDefinition] = (),
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        tool_choice: Literal["auto", "any", "none"] = "auto",
    ) -> LLMResponse: ...
