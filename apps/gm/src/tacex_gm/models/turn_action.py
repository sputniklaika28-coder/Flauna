"""TurnAction and the simplified MainAction discriminated union (GM spec §5)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from .constants import AdditionalStyle, MeleeStyle, RangedStyle

Coordinate = tuple[int, int]

ArtName = Literal["加護防壁", "反閃歩法", "霊力放出", "霊弾発射", "呪祝詛詞", "式神使役"]
BarrierEffect = Literal["barrier_wall", "armor_dissolve", "evasion_block", "attack_opportunity"]


class Movement(BaseModel):
    path: list[Coordinate] = Field(default_factory=list)
    mode: Literal["normal", "tactical_maneuver", "attack_focus"] = "normal"

    @model_validator(mode="after")
    def _path_valid(self) -> Movement:
        if self.mode == "attack_focus":
            if self.path:
                raise ValueError("attack_focus movement must have an empty path")
        else:
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


class CastArt(BaseModel):
    """祓魔術の発動 (Phase 5, §5-2)."""

    type: Literal["cast_art"] = "cast_art"
    art_name: ArtName
    target: str | None = None
    center_position: Coordinate | None = None
    options: dict[str, str | int | bool] = Field(default_factory=dict)


class DeployWire(BaseModel):
    """注連鋼縄の展開 — connects two pillars (Phase 5, §5-2)."""

    type: Literal["deploy_wire"] = "deploy_wire"
    pillar_id: str


class DispelBarrier(BaseModel):
    """結界の解除 (Phase 5, §5-2)."""

    type: Literal["dispel_barrier"] = "dispel_barrier"
    barrier_id: str


class UseItem(BaseModel):
    """アイテム使用 (Phase 5, §5-2)."""

    type: Literal["use_item"] = "use_item"
    item_name: str
    target: str | None = None
    center_position: Coordinate | None = None


class OtherAction(BaseModel):
    type: Literal["other_action"] = "other_action"
    description: str
    target_object_id: str | None = None


class Skip(BaseModel):
    type: Literal["skip"] = "skip"
    reason: str = ""


MainAction = Annotated[
    MeleeAttack
    | RangedAttack
    | PegAttack
    | CastArt
    | DeployWire
    | DispelBarrier
    | UseItem
    | OtherAction
    | Skip,
    Field(discriminator="type"),
]


# Sub-actions executed after the main action (Phase 5+)
class PlacePillar(BaseModel):
    """祓串を設置する (Phase 5 sub-action)."""

    type: Literal["place_pillar"] = "place_pillar"
    position: Coordinate


class ActivateBarrier(BaseModel):
    """結界を起動する — wire two pillars and assign an effect (Phase 5 sub-action)."""

    type: Literal["activate_barrier"] = "activate_barrier"
    pillar_id: str
    effect: BarrierEffect


class ConsumeKatashiroForMP(BaseModel):
    """形代を消費してMP回復する (Phase 5 sub-action)."""

    type: Literal["consume_katashiro_mp"] = "consume_katashiro_mp"


SubAction = Annotated[
    PlacePillar | ActivateBarrier | ConsumeKatashiroForMP,
    Field(discriminator="type"),
]


class TurnAction(BaseModel):
    """1手番分の行動 (GM spec §5-2)."""

    actor_id: str
    first_move: Movement | None = None
    main_action: MainAction
    second_move: Movement | None = None
    sub_actions: list[SubAction] = Field(default_factory=list)
