"""Game state aggregate (GM spec §6-3)."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from .character import Character
from .event import GameEvent, TurnSummary
from .pending import DeathAvoidanceRequest, EvasionRequest
from .scenario import Scenario

Coordinate = tuple[int, int]
PendingAction = EvasionRequest | DeathAvoidanceRequest


class MachineState(StrEnum):
    """§7-1."""

    IDLE = "IDLE"
    RESOLVING_ACTION = "RESOLVING_ACTION"
    AWAITING_PLAYER_INPUT = "AWAITING_PLAYER_INPUT"
    NARRATING = "NARRATING"
    PAUSED = "PAUSED"


GamePhase = Literal["briefing", "exploration", "combat", "assessment"]


class GameState(BaseModel):
    room_id: str
    version: int = 0
    seed: int
    phase: GamePhase = "briefing"
    machine_state: MachineState = MachineState.IDLE

    turn_order: list[str] = Field(default_factory=list)
    current_turn_index: int = 0
    round_number: int = 1

    characters: list[Character] = Field(default_factory=list)
    map_size: tuple[int, int]
    obstacles: list[Coordinate] = Field(default_factory=list)

    current_turn_summary: TurnSummary | None = None
    pending_actions: list[PendingAction] = Field(default_factory=list)

    event_log: list[GameEvent] = Field(default_factory=list)
    next_event_id: int = 1
    archived_event_count: int = 0

    scenario: Scenario

    def find_character(self, character_id: str) -> Character | None:
        return next((c for c in self.characters if c.id == character_id), None)

    def current_actor(self) -> Character | None:
        if not self.turn_order:
            return None
        idx = self.current_turn_index % len(self.turn_order)
        return self.find_character(self.turn_order[idx])
