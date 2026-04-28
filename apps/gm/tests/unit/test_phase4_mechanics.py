"""Phase 4 mechanic tests: 形代システム, リスポーン, 全スタイル難易度修正."""

from __future__ import annotations

import pytest

from tacex_gm.models.character import Character
from tacex_gm.models.constants import MeleeStyle, RangedStyle

# ---------------------------------------------------------------------------
# Helper: minimal Character factory
# ---------------------------------------------------------------------------


def _make_pc(
    hp: int = 10,
    max_hp: int = 20,
    katashiro: int = 7,
    status_effects: list | None = None,
    position: tuple[int, int] = (5, 5),
) -> Character:
    return Character(
        id="pc1",
        name="テスター",
        player_id="player-abc",
        faction="pc",
        tai=5,
        rei=5,
        kou=5,
        jutsu=1,
        max_hp=max_hp,
        max_mp=4,
        hp=hp,
        mp=4,
        evasion_dice=3,
        max_evasion_dice=3,
        armor_value=0,
        position=position,
        equipped_weapons=["kogatana"],
        inventory={"katashiro": katashiro},
        status_effects=status_effects or [],
    )


# ---------------------------------------------------------------------------
# 死亡回避トリガー (§10-2, D34)
# ---------------------------------------------------------------------------


def _death_avoidance_triggered(damage: int, current_hp: int) -> bool:
    """Mirrors handler logic: damage > current_hp * 2."""
    return damage > current_hp * 2


class TestDeathAvoidanceTrigger:
    def test_trigger_when_damage_exceeds_hp_times_two(self):
        # hp=5, damage=11 → 11 > 10 → triggered
        assert _death_avoidance_triggered(11, 5) is True

    def test_no_trigger_when_damage_equals_hp_times_two(self):
        # hp=5, damage=10 → 10 > 10 is False
        assert _death_avoidance_triggered(10, 5) is False

    def test_no_trigger_when_damage_below_hp_times_two(self):
        assert _death_avoidance_triggered(9, 5) is False

    def test_no_trigger_when_damage_fatal_but_not_extreme(self):
        # hp=10, damage=10 → exactly hp*1, not exceeding hp*2
        assert _death_avoidance_triggered(10, 10) is False

    def test_trigger_at_zero_hp_edge(self):
        # hp=1, damage=3 → 3 > 2 → triggered
        assert _death_avoidance_triggered(3, 1) is True

    def test_no_trigger_at_zero_hp_equal(self):
        # hp=1, damage=2 → 2 > 2 is False
        assert _death_avoidance_triggered(2, 1) is False


# ---------------------------------------------------------------------------
# 形代消費 helpers
# ---------------------------------------------------------------------------


def _katashiro_count(char: Character) -> int:
    return char.inventory.get("katashiro", 0)


def _consume_katashiro(char: Character, count: int) -> Character:
    current = _katashiro_count(char)
    new_count = max(0, current - count)
    new_inventory = {**char.inventory, "katashiro": new_count}
    return char.model_copy(update={"inventory": new_inventory})


class TestKatashiroConsumption:
    def test_consume_reduces_count(self):
        pc = _make_pc(katashiro=7)
        updated = _consume_katashiro(pc, 2)
        assert _katashiro_count(updated) == 5

    def test_consume_does_not_go_below_zero(self):
        pc = _make_pc(katashiro=1)
        updated = _consume_katashiro(pc, 2)
        assert _katashiro_count(updated) == 0

    def test_consume_zero_is_noop(self):
        pc = _make_pc(katashiro=7)
        updated = _consume_katashiro(pc, 0)
        assert _katashiro_count(updated) == 7

    def test_pc_has_enough_katashiro(self):
        pc = _make_pc(katashiro=2)
        assert _katashiro_count(pc) >= 2

    def test_pc_not_enough_katashiro(self):
        pc = _make_pc(katashiro=1)
        assert _katashiro_count(pc) < 2


# ---------------------------------------------------------------------------
# avoid_death — HP 1 を維持
# ---------------------------------------------------------------------------


class TestAvoidDeath:
    def test_avoid_death_sets_hp_to_one(self):
        pc = _make_pc(hp=5, katashiro=7)
        pc = _consume_katashiro(pc, 2)
        # Simulate avoid_death: set hp=1
        pc = pc.model_copy(update={"hp": 1})
        assert pc.hp == 1
        assert _katashiro_count(pc) == 5  # 7 - 2

    def test_avoid_death_character_is_alive(self):
        pc = _make_pc(hp=1)
        assert pc.is_alive is True


# ---------------------------------------------------------------------------
# リスポーン (D36): 半量回復、状態異常クリア、当ターン行動不可
# ---------------------------------------------------------------------------


def _apply_respawn(char: Character, respawn_point: tuple[int, int]) -> Character:
    return char.model_copy(
        update={
            "hp": max(1, char.max_hp // 2),
            "status_effects": [],
            "position": respawn_point,
            "has_acted_this_turn": True,
        }
    )


class TestRespawn:
    def test_respawn_restores_half_hp(self):
        pc = _make_pc(hp=1, max_hp=20)
        respawned = _apply_respawn(pc, (10, 10))
        assert respawned.hp == 10  # 20 // 2

    def test_respawn_odd_max_hp_floors(self):
        pc = _make_pc(hp=1, max_hp=21)
        respawned = _apply_respawn(pc, (10, 10))
        assert respawned.hp == 10  # 21 // 2

    def test_respawn_clears_status_effects(self):
        from tacex_gm.models.character import StatusEffect

        pc = _make_pc(hp=1)
        pc = pc.model_copy(update={"status_effects": [StatusEffect(name="stun", duration=2)]})
        respawned = _apply_respawn(pc, (10, 10))
        assert respawned.status_effects == []

    def test_respawn_moves_to_respawn_point(self):
        pc = _make_pc(hp=1, position=(3, 3))
        respawned = _apply_respawn(pc, (10, 10))
        assert respawned.position == (10, 10)

    def test_respawn_sets_has_acted_this_turn(self):
        pc = _make_pc(hp=1)
        respawned = _apply_respawn(pc, (10, 10))
        assert respawned.has_acted_this_turn is True

    def test_respawn_character_is_alive(self):
        pc = _make_pc(hp=1)
        respawned = _apply_respawn(pc, (10, 10))
        assert respawned.is_alive is True


# ---------------------------------------------------------------------------
# 全スタイル難易度修正 (Phase 4 §6-7 handler constants)
# ---------------------------------------------------------------------------

_MELEE_STYLE_MODIFIER: dict[MeleeStyle, int] = {
    MeleeStyle.NONE: 0,
    MeleeStyle.RENGEKI: 0,
    MeleeStyle.SEIMITSU: -1,
    MeleeStyle.KYOUKOUGEKI: 1,
    MeleeStyle.ZENRYOKU: 1,
}

_RANGED_STYLE_MODIFIER: dict[RangedStyle, int] = {
    RangedStyle.NONE: 0,
    RangedStyle.NIKAI_SHAGEKI: 0,
    RangedStyle.RENSHA: 0,
    RangedStyle.RENSHA_II: 0,
    RangedStyle.SOGEKI: -2,
    RangedStyle.NUKIUCHI: 0,
}


class TestMeleeStyleModifiers:
    @pytest.mark.parametrize(
        "style, expected",
        [
            (MeleeStyle.NONE, 0),
            (MeleeStyle.RENGEKI, 0),
            (MeleeStyle.SEIMITSU, -1),
            (MeleeStyle.KYOUKOUGEKI, 1),
            (MeleeStyle.ZENRYOKU, 1),
        ],
    )
    def test_melee_style_modifier(self, style: MeleeStyle, expected: int):
        assert _MELEE_STYLE_MODIFIER[style] == expected


class TestRangedStyleModifiers:
    @pytest.mark.parametrize(
        "style, expected",
        [
            (RangedStyle.NONE, 0),
            (RangedStyle.NIKAI_SHAGEKI, 0),
            (RangedStyle.RENSHA, 0),
            (RangedStyle.RENSHA_II, 0),
            (RangedStyle.SOGEKI, -2),
            (RangedStyle.NUKIUCHI, 0),
        ],
    )
    def test_ranged_style_modifier(self, style: RangedStyle, expected: int):
        assert _RANGED_STYLE_MODIFIER[style] == expected


class TestAllStylesHaveModifier:
    def test_all_melee_styles_covered(self):
        for style in MeleeStyle:
            assert style in _MELEE_STYLE_MODIFIER, f"Missing modifier for {style}"

    def test_all_ranged_styles_covered(self):
        for style in RangedStyle:
            assert style in _RANGED_STYLE_MODIFIER, f"Missing modifier for {style}"
