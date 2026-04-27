from __future__ import annotations

from pathlib import Path

import pytest

from tacex_gm.ai.narration_engine import (
    NarrationTemplateEngine,
    NarrationTemplateError,
)


def _good_templates() -> dict[str, dict[str, object]]:
    return {
        "attack_hit": {
            "variables": ["actor", "target"],
            "template": "{{ actor }}が{{ target }}を斬りつけた。",
        },
        "miss": {
            "variables": ["actor"],
            "template": "{{ actor }}の攻撃は外れた。",
        },
    }


class TestNarrationTemplateEngine:
    def test_renders_known_template(self) -> None:
        engine = NarrationTemplateEngine(_good_templates())
        text = engine.render("attack_hit", actor="アリス", target="鬱黒揚羽")
        assert text == "アリスが鬱黒揚羽を斬りつけた。"

    def test_unknown_template_raises(self) -> None:
        engine = NarrationTemplateEngine(_good_templates())
        with pytest.raises(NarrationTemplateError):
            engine.render("does_not_exist", actor="x")

    def test_missing_variable_raises_at_render(self) -> None:
        engine = NarrationTemplateEngine(_good_templates())
        with pytest.raises(NarrationTemplateError):
            engine.render("attack_hit", actor="アリス")  # target not provided

    def test_invalid_jinja_aborts_construction(self) -> None:
        bad = {"broken": {"template": "{{ unclosed "}}
        with pytest.raises(NarrationTemplateError):
            NarrationTemplateEngine(bad)

    def test_template_field_required(self) -> None:
        with pytest.raises(NarrationTemplateError):
            NarrationTemplateEngine({"x": {"variables": ["a"]}})

    def test_declared_variables_exposed(self) -> None:
        engine = NarrationTemplateEngine(_good_templates())
        assert engine.declared_variables("attack_hit") == ("actor", "target")
        assert engine.declared_variables("missing") == ()
        assert "attack_hit" in engine.names

    def test_loads_real_yaml(self) -> None:
        path = Path(__file__).resolve().parents[2] / "data" / "narration_templates.yaml"
        engine = NarrationTemplateEngine.from_yaml(path)
        assert "attack_hit_melee" in engine.names
        # Render with a minimal context — attribute access is implied.

        class Ctx:
            def __init__(self, name: str) -> None:
                self.name = name

        text = engine.render(
            "attack_hit_melee",
            actor=Ctx("アリス"),
            target=Ctx("鬱黒揚羽"),
            weapon=Ctx("小刀"),
            damage=4,
        )
        assert "アリス" in text
        assert "鬱黒揚羽" in text
        assert "4" in text
