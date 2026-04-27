"""GameEvent log entry."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(UTC)


class GameEvent(BaseModel):
    event_id: int = Field(ge=0)
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_now)


class TurnSummary(BaseModel):
    actor_id: str
    damage_dealt: dict[str, int] = Field(default_factory=dict)
    damage_taken: dict[str, int] = Field(default_factory=dict)
    movement_used: int = 0
    notes: list[str] = Field(default_factory=list)
