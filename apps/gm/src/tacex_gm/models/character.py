"""Character model (GM spec §6-2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

Faction = Literal["pc", "ally_npc", "enemy", "neutral"]
FirstMoveMode = Literal["normal", "tactical_maneuver", "attack_focus"]


class StatusEffect(BaseModel):
    name: str
    duration: int = Field(ge=0, description="Remaining rounds, 0 = expires this turn")
    payload: dict[str, int | str | bool] = Field(default_factory=dict)


class NPCEvasionPolicy(BaseModel):
    """Tunable knobs for NPC evasion heuristics (used by §10-4)."""

    aggression: float = Field(default=0.5, ge=0.0, le=1.0)
    save_dice_threshold: int = Field(
        default=2,
        ge=0,
        description="Reserve at least this many dice for follow-up evasion attempts.",
    )


class Character(BaseModel):
    id: str
    name: str
    player_id: str | None = None
    faction: Faction
    is_boss: bool = False

    tai: int = Field(ge=1, le=12)
    rei: int = Field(ge=1, le=12)
    kou: int = Field(ge=1, le=12)
    jutsu: int = Field(ge=0, le=3)

    max_hp: int = Field(gt=0)
    max_mp: int = Field(ge=0)
    hp: int = Field(ge=0)
    mp: int = Field(ge=0)

    evasion_dice: int = Field(ge=0)
    max_evasion_dice: int = Field(ge=0)

    position: tuple[int, int]
    equipped_weapons: list[str] = Field(default_factory=list)
    equipped_jacket: str | None = None
    armor_value: int = Field(default=0, ge=0)
    inventory: dict[str, int] = Field(default_factory=dict)

    skills: list[str] = Field(default_factory=list)
    arts: list[str] = Field(default_factory=list)
    aptitudes: list[str] = Field(default_factory=list)

    status_effects: list[StatusEffect] = Field(default_factory=list)

    has_acted_this_turn: bool = False
    movement_used_this_turn: int = 0
    first_move_mode: FirstMoveMode | None = None

    evasion_policy: NPCEvasionPolicy | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def mobility(self) -> int:
        """max(tai, kou)/2 切り上げ、最低2 (§6-2)."""

        raw = max(self.tai, self.kou)
        value = -(-raw // 2)  # ceil division for positive ints
        return max(2, value)

    @model_validator(mode="after")
    def _check_resources(self) -> Character:
        if self.hp > self.max_hp:
            raise ValueError("hp cannot exceed max_hp")
        if self.mp > self.max_mp:
            raise ValueError("mp cannot exceed max_mp")
        if self.evasion_dice > self.max_evasion_dice:
            raise ValueError("evasion_dice cannot exceed max_evasion_dice")
        if self.faction == "pc" and self.player_id is None:
            raise ValueError("PC characters must have a player_id")
        if self.faction != "pc" and self.player_id is not None:
            raise ValueError("non-PC characters must not carry a player_id")
        return self

    @property
    def is_alive(self) -> bool:
        return self.hp > 0
