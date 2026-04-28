"""Phase 3 mechanic tests: 攻撃集中, 戦術機動, 連撃, evasion dice tracking."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tacex_gm.models.constants import MeleeStyle
from tacex_gm.models.turn_action import MeleeAttack, Movement, Skip, TurnAction

# ---------------------------------------------------------------------------
# Movement model — attack_focus / tactical_maneuver / normal
# ---------------------------------------------------------------------------


class TestMovementModel:
    def test_normal_movement_requires_non_empty_path(self):
        with pytest.raises(ValidationError, match="movement path must not be empty"):
            Movement(path=[], mode="normal")

    def test_tactical_maneuver_requires_non_empty_path(self):
        with pytest.raises(ValidationError, match="movement path must not be empty"):
            Movement(path=[], mode="tactical_maneuver")

    def test_attack_focus_requires_empty_path(self):
        with pytest.raises(ValidationError, match="attack_focus movement must have an empty path"):
            Movement(path=[(1, 0)], mode="attack_focus")

    def test_attack_focus_with_empty_path_is_valid(self):
        m = Movement(path=[], mode="attack_focus")
        assert m.mode == "attack_focus"
        assert m.path == []

    def test_normal_movement_with_path_is_valid(self):
        m = Movement(path=[(1, 0), (2, 0)], mode="normal")
        assert len(m.path) == 2

    def test_tactical_maneuver_with_path_is_valid(self):
        m = Movement(path=[(0, 1)], mode="tactical_maneuver")
        assert m.mode == "tactical_maneuver"


# ---------------------------------------------------------------------------
# TurnAction with attack_focus first_move
# ---------------------------------------------------------------------------


class TestTurnActionAttackFocus:
    def test_attack_focus_first_move_accepted(self):
        ta = TurnAction(
            actor_id="pc1",
            first_move=Movement(path=[], mode="attack_focus"),
            main_action=MeleeAttack(
                weapon_id="sword",
                style=MeleeStyle.NONE,
                dice_distribution=[3],
                targets=["enemy1"],
            ),
        )
        assert ta.first_move is not None
        assert ta.first_move.mode == "attack_focus"

    def test_no_first_move_is_valid(self):
        ta = TurnAction(
            actor_id="pc1",
            main_action=Skip(),
        )
        assert ta.first_move is None


# ---------------------------------------------------------------------------
# 連撃 even distribution validation helper (logic from ws/handler.py)
# ---------------------------------------------------------------------------


def _validate_rengeki_distribution(dice_distribution: list[int]) -> str | None:
    """Return an error message if the distribution is not even, else None."""
    if len(dice_distribution) <= 1:
        return None
    total = sum(dice_distribution)
    if total == 0:
        return None
    n = len(dice_distribution)
    expected = total // n
    remainder = total % n
    for i, d in enumerate(dice_distribution):
        expected_i = expected + (1 if i < remainder else 0)
        if d != expected_i:
            return "not even"
    return None


class TestRengekiDistribution:
    def test_even_split_two_targets(self):
        assert _validate_rengeki_distribution([2, 2]) is None

    def test_even_split_three_targets(self):
        assert _validate_rengeki_distribution([2, 2, 2]) is None

    def test_uneven_two_targets_fails(self):
        assert _validate_rengeki_distribution([3, 1]) is not None

    def test_single_target_always_valid(self):
        # Single target has no distribution requirement.
        assert _validate_rengeki_distribution([4]) is None

    def test_zero_total_is_valid(self):
        assert _validate_rengeki_distribution([0, 0]) is None

    def test_remainder_distributed_front(self):
        # total=5 split among 3: [2, 2, 1] is valid (first slots get extra)
        assert _validate_rengeki_distribution([2, 2, 1]) is None

    def test_remainder_wrong_position_fails(self):
        # [1, 2, 2] would be invalid for 5/3 (remainder must go to first slots)
        assert _validate_rengeki_distribution([1, 2, 2]) is not None


# ---------------------------------------------------------------------------
# Evasion dice tracking helpers (from ws/handler.py logic)
# ---------------------------------------------------------------------------


def _restore_evasion_dice(char_dict: dict) -> dict:
    return {**char_dict, "evasion_dice": char_dict["max_evasion_dice"]}


def _consume_evasion_dice(char_dict: dict, used: int) -> dict:
    new_val = max(0, char_dict["evasion_dice"] - used)
    return {**char_dict, "evasion_dice": new_val}


class TestEvasionDiceTracking:
    def _make_char(self, evasion_dice: int = 3, max_evasion_dice: int = 3) -> dict:
        return {"evasion_dice": evasion_dice, "max_evasion_dice": max_evasion_dice}

    def test_restore_resets_to_max(self):
        char = self._make_char(evasion_dice=1, max_evasion_dice=3)
        restored = _restore_evasion_dice(char)
        assert restored["evasion_dice"] == 3

    def test_restore_noop_when_already_max(self):
        char = self._make_char(evasion_dice=3, max_evasion_dice=3)
        restored = _restore_evasion_dice(char)
        assert restored["evasion_dice"] == 3

    def test_consume_reduces_dice(self):
        char = self._make_char(evasion_dice=3)
        updated = _consume_evasion_dice(char, 2)
        assert updated["evasion_dice"] == 1

    def test_consume_does_not_go_below_zero(self):
        char = self._make_char(evasion_dice=1)
        updated = _consume_evasion_dice(char, 5)
        assert updated["evasion_dice"] == 0

    def test_consume_zero_is_noop(self):
        char = self._make_char(evasion_dice=3)
        updated = _consume_evasion_dice(char, 0)
        assert updated["evasion_dice"] == 3

    def test_restore_then_consume_cycle(self):
        char = self._make_char(evasion_dice=0, max_evasion_dice=2)
        restored = _restore_evasion_dice(char)
        assert restored["evasion_dice"] == 2
        consumed = _consume_evasion_dice(restored, 1)
        assert consumed["evasion_dice"] == 1
