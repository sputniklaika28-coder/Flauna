"""Mock LLMBackend for deterministic tests."""
from __future__ import annotations

from typing import Any


class MockLLMBackend:
    """Returns pre-canned responses in sequence. Raises IndexError when exhausted."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = responses
        self._index = 0

    async def chat_completion(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        response = self._responses[self._index]
        self._index += 1
        return response

    @staticmethod
    def tool_use_response(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Helper to build a fake tool-use response."""
        return {
            "id": "mock-msg-001",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "mock-tool-001",
                    "name": tool_name,
                    "input": tool_input,
                }
            ],
            "stop_reason": "tool_use",
        }

    @staticmethod
    def text_response(text: str) -> dict[str, Any]:
        """Helper to build a fake text (narration) response."""
        return {
            "id": "mock-msg-002",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
        }
