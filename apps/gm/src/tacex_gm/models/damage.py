"""Damage formulas and ability bonuses (GM spec §6-8)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Pattern: NdM, NdM+K, NdM-K, or a bare integer constant.
_FORMULA_RE = re.compile(r"^\s*(?:(\d+)d(\d+)\s*([+-]\s*\d+)?|([+-]?\d+))\s*$")


class DamageFormula(BaseModel):
    """``NdM(+K)`` style damage formula (GM spec §6-8)."""

    raw: str

    @field_validator("raw")
    @classmethod
    def _check_format(cls, raw: str) -> str:
        if not _FORMULA_RE.match(raw):
            raise ValueError(f"invalid damage formula: {raw!r}")
        return raw.strip()

    def parse(self) -> tuple[int, int, int]:
        """Return ``(count, sides, modifier)``. A bare constant is ``(0, 0, K)``."""

        match = _FORMULA_RE.match(self.raw)
        assert match is not None  # validated on construction
        n_str, m_str, mod_str, const_str = match.groups()
        if const_str is not None:
            return 0, 0, int(const_str)
        count = int(n_str or "0")
        sides = int(m_str or "0")
        modifier = int((mod_str or "0").replace(" ", ""))
        return count, sides, modifier

    def expected_value(self) -> float:
        """Expected damage assuming uniform dice."""

        count, sides, modifier = self.parse()
        if count == 0:
            return float(modifier)
        per_die = (sides + 1) / 2
        return count * per_die + modifier


AbilityName = Literal["体", "霊", "巧"]
AbilityCondition = Literal["always", "on_six", "on_double_six"]


class AbilityBonus(BaseModel):
    ability: AbilityName
    multiplier: float = 1.0
    condition: AbilityCondition = "always"


class DamageSpec(BaseModel):
    base_formula: DamageFormula
    ability_bonus: AbilityBonus | None = None
    damage_type: Literal["physical", "spiritual"] = "physical"
    armor_piercing: bool = False
    notes: str | None = Field(default=None, description="Free-form designer note")
