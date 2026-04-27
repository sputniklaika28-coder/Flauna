"""AI integration: backend protocol, narration templating, concrete adapters."""

from .anthropic_backend import DEFAULT_MODEL as ANTHROPIC_DEFAULT_MODEL
from .anthropic_backend import AnthropicBackend
from .backend import (
    LLMBackend,
    LLMBackendError,
    LLMResponse,
    Message,
    MessageRole,
    StopReason,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)
from .mock_backend import MockCall, MockLLMBackend, text_response, tool_response
from .narration_engine import NarrationTemplateEngine, NarrationTemplateError

__all__ = [
    "ANTHROPIC_DEFAULT_MODEL",
    "AnthropicBackend",
    "LLMBackend",
    "LLMBackendError",
    "LLMResponse",
    "Message",
    "MessageRole",
    "MockCall",
    "MockLLMBackend",
    "NarrationTemplateEngine",
    "NarrationTemplateError",
    "StopReason",
    "TokenUsage",
    "ToolCall",
    "ToolDefinition",
    "text_response",
    "tool_response",
]
