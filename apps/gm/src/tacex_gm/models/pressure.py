"""CombatPressure model (GM spec §6-3, §10-3, Phase 6)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class PressureLevel(StrEnum):
    NORMAL = "normal"
    HARD = "hard"
    ULTRA_HARD = "ultra_hard"


class CombatPressure(BaseModel):
    """Round-level stalemate tracker (§10-3).

    Tracks cumulative damage between PCs and boss characters during a round.
    If both sides deal 0 damage for 2 consecutive rounds → HARD.
    2 more consecutive 0-damage rounds → ULTRA_HARD.
    """

    level: PressureLevel = PressureLevel.NORMAL
    zero_damage_rounds: int = Field(default=0, ge=0)

    # Running totals for the current round (reset each round).
    pc_to_boss_damage: int = Field(default=0, ge=0)
    boss_to_pc_damage: int = Field(default=0, ge=0)
