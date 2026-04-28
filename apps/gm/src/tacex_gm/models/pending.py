"""Pending interrupt requests (GM spec §7-4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field

DamageType = Literal["physical", "spiritual"]


def _now() -> datetime:
    return datetime.now(UTC)


class IncomingAttack(BaseModel):
    attacker_id: str
    weapon_id: str
    successes: int = Field(ge=0)
    damage_formula: str
    damage_type: DamageType = "physical"


class EvasionRequest(BaseModel):
    pending_id: str
    target_character_id: str
    target_player_id: str | None = None
    incoming_attacks: list[IncomingAttack]
    can_batch: bool = True
    max_evasion_dice: int = Field(ge=0)
    created_at: datetime = Field(default_factory=_now)
    deadline_at: datetime

    @classmethod
    def with_default_deadline(
        cls,
        *,
        pending_id: str,
        target_character_id: str,
        target_player_id: str | None,
        incoming_attacks: list[IncomingAttack],
        max_evasion_dice: int,
        timeout_seconds: int = 60,
        can_batch: bool = True,
    ) -> EvasionRequest:
        created = _now()
        return cls(
            pending_id=pending_id,
            target_character_id=target_character_id,
            target_player_id=target_player_id,
            incoming_attacks=incoming_attacks,
            can_batch=can_batch,
            max_evasion_dice=max_evasion_dice,
            created_at=created,
            deadline_at=created + timedelta(seconds=timeout_seconds),
        )


class DeathAvoidanceRequest(BaseModel):
    """Phase 4 以降。形代システムによる死亡回避要求 (§10-2)."""

    pending_id: str
    target_character_id: str
    target_player_id: str
    incoming_damage: int = Field(gt=0)
    damage_type: DamageType
    katashiro_required: int = Field(gt=0)
    katashiro_remaining: int = Field(ge=0)
    created_at: datetime = Field(default_factory=_now)
    deadline_at: datetime

    @classmethod
    def with_default_deadline(
        cls,
        *,
        pending_id: str,
        target_character_id: str,
        target_player_id: str,
        incoming_damage: int,
        damage_type: DamageType,
        katashiro_required: int,
        katashiro_remaining: int,
        timeout_seconds: int = 60,
    ) -> DeathAvoidanceRequest:
        created = _now()
        return cls(
            pending_id=pending_id,
            target_character_id=target_character_id,
            target_player_id=target_player_id,
            incoming_damage=incoming_damage,
            damage_type=damage_type,
            katashiro_required=katashiro_required,
            katashiro_remaining=katashiro_remaining,
            created_at=created,
            deadline_at=created + timedelta(seconds=timeout_seconds),
        )
