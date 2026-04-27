"""Narrative templating with Jinja2 (GM spec §11-3, §15-2).

Loaded once at startup from ``data/narration_templates.yaml``. Every template
is compiled and validated eagerly so a malformed template aborts boot rather
than crashing mid-session.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, select_autoescape

from tacex_gm.scenario.loader import load_narration_templates


class NarrationTemplateError(ValueError):
    """Raised on missing/invalid templates (boot-time or render-time)."""


class NarrationTemplateEngine:
    """Compiled Jinja2 template registry."""

    def __init__(self, templates: Mapping[str, Mapping[str, Any]]) -> None:
        self._env = Environment(
            autoescape=select_autoescape(disabled_extensions=("txt", "md", "yaml")),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._compiled: dict[str, Any] = {}
        self._declared_variables: dict[str, tuple[str, ...]] = {}
        errors: list[str] = []
        for name, body in templates.items():
            raw = body.get("template")
            if not isinstance(raw, str):
                errors.append(f"template '{name}' missing 'template' string")
                continue
            try:
                self._compiled[name] = self._env.from_string(raw)
            except TemplateSyntaxError as exc:
                errors.append(f"template '{name}' syntax error: {exc.message}")
                continue
            declared = body.get("variables", [])
            if isinstance(declared, list):
                self._declared_variables[name] = tuple(str(v) for v in declared)
        if errors:
            raise NarrationTemplateError("; ".join(errors))

    @classmethod
    def from_yaml(cls, path: Path) -> NarrationTemplateEngine:
        return cls(load_narration_templates(path))

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._compiled.keys())

    def declared_variables(self, name: str) -> tuple[str, ...]:
        return self._declared_variables.get(name, ())

    def render(self, name: str, /, **context: Any) -> str:
        template = self._compiled.get(name)
        if template is None:
            raise NarrationTemplateError(f"unknown narration template '{name}'")
        try:
            text = template.render(**context)
        except Exception as exc:  # jinja2 raises a wide variety; surface uniformly
            raise NarrationTemplateError(f"template '{name}' render failed: {exc}") from exc
        return str(text).rstrip("\n")
