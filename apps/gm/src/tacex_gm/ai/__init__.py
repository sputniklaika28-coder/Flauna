"""AI integration: narration templating now, LLM backends later."""

from .narration_engine import NarrationTemplateEngine, NarrationTemplateError

__all__ = [
    "NarrationTemplateEngine",
    "NarrationTemplateError",
]
