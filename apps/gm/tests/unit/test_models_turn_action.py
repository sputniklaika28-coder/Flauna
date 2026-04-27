from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from tacex_gm.models import (
    MainAction,
    MeleeAttack,
    MeleeStyle,
    Movement,
    OtherAction,
    PegAttack,
    RangedAttack,
    RangedStyle,
    Skip,
    TurnAction,
)


class TestMovement:
    def test_path_required(self) -> None:
        with pytest.raises(ValidationError):
            Movement(path=[])

    def test_default_mode_is_normal(self) -> None:
        mv = Movement(path=[(1, 1)])
        assert mv.mode == "normal"


class TestAttackValidators:
    def test_dice_distribution_must_match_targets(self) -> None:
        with pytest.raises(ValidationError):
            MeleeAttack(weapon_id="w", dice_distribution=[3], targets=["a", "b"])

    def test_dice_distribution_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            MeleeAttack(weapon_id="w", dice_distribution=[-1], targets=["a"])

    def test_melee_default_style(self) -> None:
        atk = MeleeAttack(weapon_id="w", dice_distribution=[3], targets=["a"])
        assert atk.style == MeleeStyle.NONE
        assert atk.type == "melee_attack"

    def test_ranged_default_style(self) -> None:
        atk = RangedAttack(weapon_id="w", dice_distribution=[2], targets=["a"])
        assert atk.style == RangedStyle.NONE
        assert atk.type == "ranged_attack"


class TestDiscriminatedUnion:
    def test_main_action_discriminator(self) -> None:
        adapter = TypeAdapter(MainAction)
        for payload, expected_cls in [
            (
                {
                    "type": "melee_attack",
                    "weapon_id": "kogatana",
                    "dice_distribution": [3],
                    "targets": ["enemy1"],
                },
                MeleeAttack,
            ),
            (
                {
                    "type": "ranged_attack",
                    "weapon_id": "ofuda",
                    "dice_distribution": [2],
                    "targets": ["enemy1"],
                },
                RangedAttack,
            ),
            (
                {
                    "type": "peg_attack",
                    "weapon_id": "harae_gushi",
                    "dice_distribution": [3],
                    "targets": ["enemy1"],
                },
                PegAttack,
            ),
            ({"type": "other_action", "description": "祈祷"}, OtherAction),
            ({"type": "skip", "reason": "待機"}, Skip),
        ]:
            obj = adapter.validate_python(payload)
            assert isinstance(obj, expected_cls), payload


class TestTurnAction:
    def test_minimal(self) -> None:
        ta = TurnAction(
            actor_id="char-1",
            main_action=Skip(reason="様子見"),
        )
        assert ta.first_move is None
        assert ta.second_move is None
        assert isinstance(ta.main_action, Skip)
