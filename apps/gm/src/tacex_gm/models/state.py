"""Game state aggregate (GM spec §6-3)."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from .assessment import GrowthProposal, SessionScore
from .character import Character
from .event import GameEvent, TurnSummary
from .pending import DeathAvoidanceRequest, EvasionRequest
from .pressure import CombatPressure
from .scenario import Scenario

Coordinate = tuple[int, int]
PendingAction = EvasionRequest | DeathAvoidanceRequest

BarrierEffect = Literal["barrier_wall", "armor_dissolve", "evasion_block", "attack_opportunity"]


class Pillar(BaseModel):
    """祓串 (§6-5, Phase 5)."""

    id: str
    owner_id: str
    position: Coordinate
    is_active: bool = True


class Wire(BaseModel):
    """注連鋼縄 — connects two pillars (§6-5, Phase 5)."""

    id: str
    pillar_a_id: str
    pillar_b_id: str


class Barrier(BaseModel):
    """結界 — activated from a wire (§6-5, Phase 5)."""

    id: str
    wire_id: str
    effect: BarrierEffect
    owner_id: str
    is_active: bool = True


class MapObject(BaseModel):
    """Destructible map object (§6-5, Phase 5)."""

    id: str
    position: Coordinate
    strength: int = Field(ge=0)
    armor: int = Field(default=0, ge=0)
    label: str = ""


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

    # Phase 5 map entities
    pillars: list[Pillar] = Field(default_factory=list)
    wires: list[Wire] = Field(default_factory=list)
    barriers: list[Annotated[Barrier, Field()]] = Field(default_factory=list)
    objects: list[MapObject] = Field(default_factory=list)

    # Phase 6: hard mode escalation (§10-3, D35)
    combat_pressure: CombatPressure = Field(default_factory=CombatPressure)

    current_turn_summary: TurnSummary | None = None
    pending_actions: list[PendingAction] = Field(default_factory=list)

    event_log: list[GameEvent] = Field(default_factory=list)
    next_event_id: int = 1
    archived_event_count: int = 0

    scenario: Scenario

    # Phase 7: set when combat ends and the assessment phase begins
    assessment_result: SessionScore | None = None
    growth_proposals: list[GrowthProposal] = Field(default_factory=list)

    def find_character(self, character_id: str) -> Character | None:
        return next((c for c in self.characters if c.id == character_id), None)

    def current_actor(self) -> Character | None:
        if not self.turn_order:
            return None
        idx = self.current_turn_index % len(self.turn_order)
        return self.find_character(self.turn_order[idx])

    def find_pillar(self, pillar_id: str) -> Pillar | None:
        return next((p for p in self.pillars if p.id == pillar_id), None)

    def find_barrier(self, barrier_id: str) -> Barrier | None:
        return next((b for b in self.barriers if b.id == barrier_id), None)

    def find_wire(self, wire_id: str) -> Wire | None:
        return next((w for w in self.wires if w.id == wire_id), None)
