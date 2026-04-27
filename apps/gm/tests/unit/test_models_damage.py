from __future__ import annotations

import pytest

from tacex_gm.models.damage import AbilityBonus, DamageFormula, DamageSpec


class TestDamageFormula:
    @pytest.mark.parametrize(
        "raw, parsed",
        [
            ("1d6", (1, 6, 0)),
            ("2d6+1", (2, 6, 1)),
            ("3d6-2", (3, 6, -2)),
            ("4", (0, 0, 4)),
            ("-3", (0, 0, -3)),
        ],
    )
    def test_parse(self, raw: str, parsed: tuple[int, int, int]) -> None:
        assert DamageFormula(raw=raw).parse() == parsed

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            DamageFormula(raw="garbage")

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("2d6", 7.0),
            ("2d6+1", 8.0),
            ("4", 4.0),
        ],
    )
    def test_expected_value(self, raw: str, expected: float) -> None:
        assert DamageFormula(raw=raw).expected_value() == expected


class TestDamageSpec:
    def test_basic(self) -> None:
        spec = DamageSpec(base_formula=DamageFormula(raw="1d6"))
        assert spec.damage_type == "physical"
        assert spec.ability_bonus is None
        assert not spec.armor_piercing

    def test_with_ability_bonus(self) -> None:
        spec = DamageSpec(
            base_formula=DamageFormula(raw="2d6"),
            ability_bonus=AbilityBonus(ability="霊", multiplier=1.0),
            damage_type="spiritual",
        )
        assert spec.ability_bonus is not None
        assert spec.ability_bonus.ability == "霊"
        assert spec.damage_type == "spiritual"
