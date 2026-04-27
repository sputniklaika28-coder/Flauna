"""Weapon (祭具) data model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .constants import RangeClass
from .damage import DamageSpec

WeaponCategory = Literal["melee", "ranged", "peg"]


class Weapon(BaseModel):
    id: str
    name: str
    category: WeaponCategory
    range_class: RangeClass | None = None
    base_dice: int = Field(ge=0, description="Default attack dice pool size")
    damage: DamageSpec
    tags: list[str] = Field(default_factory=list)
    description: str = ""
