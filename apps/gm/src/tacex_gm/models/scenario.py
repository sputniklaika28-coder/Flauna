"""Scenario data model (GM spec §14)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Coordinate = tuple[int, int]


class ScenarioCharacter(BaseModel):
    id: str
    name: str
    faction: Literal["pc", "enemy", "neutral"]
    template: str | None = None
    position: Coordinate
    is_boss: bool = False
    overrides: dict[str, Any] = Field(default_factory=dict)


class TriggerEnterZone(BaseModel):
    type: Literal["enter_zone"]
    zone: tuple[Coordinate, Coordinate]
    who: list[str] = Field(default_factory=lambda: ["any_pc"])


class TriggerCharacterDies(BaseModel):
    type: Literal["character_dies"]
    character_id: str


class TriggerRoundReached(BaseModel):
    """Fire when the round counter reaches the specified value (Phase 6)."""

    type: Literal["round_reached"]
    round: int = Field(ge=1)


class TriggerObjectDestroyed(BaseModel):
    """Fire when a MapObject's strength drops to 0 (Phase 6)."""

    type: Literal["object_destroyed"]
    object_id: str


Trigger = TriggerEnterZone | TriggerCharacterDies | TriggerRoundReached | TriggerObjectDestroyed


class ActionSpawnEnemy(BaseModel):
    type: Literal["spawn_enemy"]
    template: str
    count: int = Field(ge=1, default=1)
    positions: list[Coordinate] = Field(default_factory=list)


class ActionShowNarrative(BaseModel):
    type: Literal["show_narrative"]
    text: str


ScenarioAction = ActionSpawnEnemy | ActionShowNarrative


class ScenarioEvent(BaseModel):
    id: str
    trigger: Trigger
    actions: list[ScenarioAction]
    once: bool = True
    fired: bool = False  # True after a once=True event has been triggered.


class VictoryAllEnemiesDefeated(BaseModel):
    type: Literal["all_enemies_defeated"]


class VictoryReachZone(BaseModel):
    type: Literal["reach_zone"]
    zone: tuple[Coordinate, Coordinate]
    who: list[str] = Field(default_factory=lambda: ["any_pc"])


VictoryCondition = VictoryAllEnemiesDefeated | VictoryReachZone


class FailureAllPCsDefeated(BaseModel):
    type: Literal["all_pcs_defeated"]


class FailureRoundLimit(BaseModel):
    type: Literal["round_limit"]
    round: int = Field(ge=1)


FailureCondition = FailureAllPCsDefeated | FailureRoundLimit


class Scenario(BaseModel):
    scenario_id: str
    title: str
    map_size: tuple[int, int]
    respawn_point: Coordinate | None = None
    obstacles: list[Coordinate] = Field(default_factory=list)
    characters: list[ScenarioCharacter] = Field(default_factory=list)
    events: list[ScenarioEvent] = Field(default_factory=list)
    victory_conditions: list[VictoryCondition] = Field(default_factory=list)
    failure_conditions: list[FailureCondition] = Field(default_factory=list)
