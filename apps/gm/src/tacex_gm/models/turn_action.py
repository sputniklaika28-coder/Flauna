"""TurnAction and the simplified MainAction discriminated union (GM spec §5)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from .constants import AdditionalStyle, MeleeStyle, RangedStyle

Coordinate = tuple[int, int]


class Movement(BaseModel):
    path: list[Coordinate] = Field(default_factory=list)
    mode: Literal["normal", "tactical_maneuver", "attack_focus"] = "normal"

    @model_validator(mode="after")
    def _path_not_empty(self) -> Movement:
        if not self.path:
            raise ValueError("movement path must not be empty")
        return self


class _AttackBase(BaseModel):
    weapon_id: str
    dice_distribution: list[int]
    targets: list[str]

    @model_validator(mode="after")
    def _len_match(self) -> _AttackBase:
        if len(self.targets) != len(self.dice_distribution):
            raise ValueError("targets length must match dice_distribution length")
        if any(d < 0 for d in self.dice_distribution):
            raise ValueError("dice_distribution entries must be non-negative")
        return self


class MeleeAttack(_AttackBase):
    type: Literal["melee_attack"] = "melee_attack"
    style: MeleeStyle = MeleeStyle.NONE
    additional_style: AdditionalStyle | None = None


class RangedAttack(_AttackBase):
    type: Literal["ranged_attack"] = "ranged_attack"
    style: RangedStyle = RangedStyle.NONE
    additional_style: AdditionalStyle | None = None


class PegAttack(_AttackBase):
    """祓串遠隔。MVP では中型遠隔と同じ枠に近い扱い。"""

    type: Literal["peg_attack"] = "peg_attack"
    style: RangedStyle = RangedStyle.NONE


class OtherAction(BaseModel):
    type: Literal["other_action"] = "other_action"
    description: str


class Skip(BaseModel):
    type: Literal["skip"] = "skip"
    reason: str = ""


MainAction = Annotated[
    MeleeAttack | RangedAttack | PegAttack | OtherAction | Skip,
    Field(discriminator="type"),
]


class TurnAction(BaseModel):
    """1手番分の行動 (GM spec §5-2)."""

    actor_id: str
    first_move: Movement | None = None
    main_action: MainAction
    second_move: Movement | None = None
    sub_actions: list[dict[str, str]] = Field(default_factory=list)
