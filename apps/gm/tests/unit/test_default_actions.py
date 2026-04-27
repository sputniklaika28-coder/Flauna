"""Unit tests for the default-action selector (GM spec §4-3, §10-5)."""

from __future__ import annotations

from typing import Any

from tacex_gm.engine import select_default_action
from tacex_gm.models import (
    Character,
    DamageFormula,
    DamageSpec,
    GameState,
    MeleeAttack,
    RangeClass,
    RangedAttack,
    Scenario,
    Skip,
    Weapon,
)


def make_character(
    cid: str,
    *,
    faction: str = "enemy",
    position: tuple[int, int] = (0, 0),
    weapons: list[str] | None = None,
    hp: int = 20,
    tai: int = 4,
    kou: int = 4,
) -> Character:
    return Character(
        id=cid,
        name=cid,
        player_id="p1" if faction == "pc" else None,
        faction=faction,  # type: ignore[arg-type]
        tai=tai,
        rei=4,
        kou=kou,
        jutsu=0,
        max_hp=hp,
        max_mp=0,
        hp=hp,
        mp=0,
        evasion_dice=3,
        max_evasion_dice=3,
        position=position,
        equipped_weapons=weapons or [],
    )


def melee_weapon(wid: str = "kogatana", base_dice: int = 4) -> Weapon:
    return Weapon(
        id=wid,
        name=wid,
        category="melee",
        base_dice=base_dice,
        damage=DamageSpec(base_formula=DamageFormula(raw="1d6+1")),
    )


def ranged_weapon(
    wid: str = "ofuda",
    range_class: RangeClass = RangeClass.SMALL_RANGED,
    base_dice: int = 3,
) -> Weapon:
    return Weapon(
        id=wid,
        name=wid,
        category="ranged",
        range_class=range_class,
        base_dice=base_dice,
        damage=DamageSpec(base_formula=DamageFormula(raw="1d6")),
    )


def make_state(characters: list[Character], **overrides: Any) -> GameState:
    obstacles = overrides.pop("obstacles", [])
    map_size = overrides.pop("map_size", (12, 12))
    scenario = Scenario(
        scenario_id="t",
        title="t",
        map_size=map_size,
        obstacles=list(obstacles),
        characters=[],
    )
    return GameState(
        room_id="r",
        seed=42,
        map_size=map_size,
        characters=characters,
        obstacles=list(obstacles),
        scenario=scenario,
        **overrides,
    )


class TestNoTargets:
    def test_no_living_opponents_skips(self) -> None:
        actor = make_character("npc", faction="enemy", position=(0, 0), weapons=["kogatana"])
        state = make_state([actor])
        action = select_default_action(actor, state, {"kogatana": melee_weapon()})
        assert isinstance(action.main_action, Skip)
        assert action.main_action.reason == "no_targets"

    def test_only_dead_opponents_skips(self) -> None:
        actor = make_character("npc", faction="enemy", position=(0, 0), weapons=["kogatana"])
        pc = make_character("alice", faction="pc", position=(2, 0), hp=20)
        # Force HP to zero via model_copy to bypass validator (max_hp=20, hp=0 OK).
        pc = pc.model_copy(update={"hp": 0})
        state = make_state([actor, pc])
        action = select_default_action(actor, state, {"kogatana": melee_weapon()})
        assert isinstance(action.main_action, Skip)
        assert action.main_action.reason == "no_targets"


class TestNoWeapon:
    def test_actor_without_weapons_skips(self) -> None:
        actor = make_character("npc", faction="enemy", position=(0, 0), weapons=[])
        pc = make_character("alice", faction="pc", position=(1, 0))
        state = make_state([actor, pc])
        action = select_default_action(actor, state, {})
        assert isinstance(action.main_action, Skip)
        assert action.main_action.reason == "no_weapon"


class TestInRange:
    def test_melee_attack_when_adjacent(self) -> None:
        actor = make_character("npc", faction="enemy", position=(2, 2), weapons=["kogatana"])
        pc = make_character("alice", faction="pc", position=(3, 2))
        state = make_state([actor, pc])
        action = select_default_action(actor, state, {"kogatana": melee_weapon()})
        assert action.first_move is None
        assert isinstance(action.main_action, MeleeAttack)
        assert action.main_action.weapon_id == "kogatana"
        assert action.main_action.targets == ["alice"]
        assert action.main_action.dice_distribution == [4]

    def test_ranged_attack_within_band(self) -> None:
        actor = make_character("npc", faction="enemy", position=(0, 0), weapons=["ofuda"])
        pc = make_character("alice", faction="pc", position=(3, 0))
        state = make_state([actor, pc])
        action = select_default_action(actor, state, {"ofuda": ranged_weapon()})
        assert action.first_move is None
        assert isinstance(action.main_action, RangedAttack)
        assert action.main_action.weapon_id == "ofuda"

    def test_picks_nearest_enemy(self) -> None:
        actor = make_character("npc", faction="enemy", position=(0, 0), weapons=["kogatana"])
        far = make_character("bob", faction="pc", position=(10, 10))
        near = make_character("alice", faction="pc", position=(1, 0))
        state = make_state([actor, far, near])
        action = select_default_action(actor, state, {"kogatana": melee_weapon()})
        assert isinstance(action.main_action, MeleeAttack)
        assert action.main_action.targets == ["alice"]


class TestApproachAndAttack:
    def test_walks_into_melee_range(self) -> None:
        actor = make_character(
            "npc", faction="enemy", position=(0, 0), weapons=["kogatana"], tai=6, kou=6
        )
        pc = make_character("alice", faction="pc", position=(4, 0))
        state = make_state([actor, pc])
        action = select_default_action(actor, state, {"kogatana": melee_weapon()})
        assert action.first_move is not None
        # Mobility = ceil(max(6,6)/2) = 3 — actor should land on (3, 0).
        assert action.first_move.path[-1] == (3, 0)
        assert isinstance(action.main_action, MeleeAttack)

    def test_skips_if_obstacle_blocks_path(self) -> None:
        actor = make_character(
            "npc", faction="enemy", position=(0, 0), weapons=["kogatana"], tai=2, kou=2
        )
        pc = make_character("alice", faction="pc", position=(4, 0))
        # Obstacle on the only diagonal step.
        state = make_state([actor, pc], obstacles=[(1, 0)])
        action = select_default_action(actor, state, {"kogatana": melee_weapon()})
        assert isinstance(action.main_action, Skip)
        assert action.main_action.reason == "cannot_reach"

    def test_skips_if_target_too_far_for_mobility(self) -> None:
        actor = make_character(
            "npc", faction="enemy", position=(0, 0), weapons=["kogatana"], tai=2, kou=2
        )
        pc = make_character("alice", faction="pc", position=(10, 10))
        state = make_state([actor, pc])
        action = select_default_action(actor, state, {"kogatana": melee_weapon()})
        assert isinstance(action.main_action, Skip)
        assert action.main_action.reason == "cannot_reach"

    def test_prefers_melee_over_ranged_at_close_range(self) -> None:
        actor = make_character(
            "npc",
            faction="enemy",
            position=(0, 0),
            weapons=["kogatana", "ofuda"],
            tai=4,
            kou=4,
        )
        pc = make_character("alice", faction="pc", position=(1, 0))
        state = make_state([actor, pc])
        action = select_default_action(
            actor, state, {"kogatana": melee_weapon(), "ofuda": ranged_weapon()}
        )
        assert isinstance(action.main_action, MeleeAttack)


class TestCatalogMissing:
    def test_unknown_weapon_id_is_skipped(self) -> None:
        actor = make_character("npc", faction="enemy", position=(0, 0), weapons=["nonexistent"])
        pc = make_character("alice", faction="pc", position=(1, 0))
        state = make_state([actor, pc])
        # Empty catalog — all equipped weapons are filtered out.
        action = select_default_action(actor, state, {})
        assert isinstance(action.main_action, Skip)
        assert action.main_action.reason == "no_weapon"
