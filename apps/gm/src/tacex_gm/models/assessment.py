"""Assessment phase data models (Phase 7, GM spec §15)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Grade = Literal["S", "A", "B", "C", "D"]
GrowthType = Literal["skill", "art"]


class SessionScore(BaseModel):
    """Numeric summary of a completed combat session."""

    outcome: Literal["victory", "defeat"]
    rounds_taken: int = Field(ge=0)
    pcs_alive: int = Field(ge=0)
    pcs_total: int = Field(ge=0)
    enemies_defeated: int = Field(ge=0)
    enemies_total: int = Field(ge=0)
    grade: Grade


class GrowthProposal(BaseModel):
    """A suggested growth award for one PC character."""

    character_id: str
    grow_type: GrowthType
    name: str
