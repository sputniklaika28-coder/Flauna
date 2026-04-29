"""Phase 6 mechanics tests: CombatPressure, scenario triggers, multi-player helpers."""

from __future__ import annotations

from tacex_gm.engine.pressure import accumulate_pressure, advance_pressure_round
from tacex_gm.engine.scenario_triggers import (
    apply_map_object_damage,
    events_for_character_death,
    events_for_object_destroyed,
    events_for_round,
    events_for_zone_entry,
    mark_event_fired,
)
from tacex_gm.models.event import TurnSummary
from tacex_gm.models.pressure import CombatPressure, PressureLevel
from tacex_gm.models.scenario import (
    ActionShowNarrative,
    Scenario,
    ScenarioEvent,
    TriggerCharacterDies,
    TriggerEnterZone,
    TriggerObjectDestroyed,
    TriggerRoundReached,
)
from tacex_gm.models.state import GameState, MapObject

# ---------------------------------------------------------------------------
# CombatPressure model
# ---------------------------------------------------------------------------


def test_pressure_defaults():
    p = CombatPressure()
    assert p.level == PressureLevel.NORMAL
    assert p.zero_damage_rounds == 0
    assert p.pc_to_boss_damage == 0
    assert p.boss_to_pc_damage == 0


def test_accumulate_pressure_pc_hits_boss():
    p = CombatPressure()
    summary = TurnSummary(actor_id="pc1", damage_dealt={"boss1": 10})
    p2 = accumulate_pressure(
        p,
        summary,
        actor_is_boss=False,
        target_is_boss={"boss1": True},
        target_is_pc={"boss1": False},
    )
    assert p2.pc_to_boss_damage == 10
    assert p2.boss_to_pc_damage == 0


def test_accumulate_pressure_boss_hits_pc():
    p = CombatPressure()
    summary = TurnSummary(actor_id="boss1", damage_dealt={"pc1": 5})
    p2 = accumulate_pressure(
        p,
        summary,
        actor_is_boss=True,
        target_is_boss={"pc1": False},
        target_is_pc={"pc1": True},
    )
    assert p2.boss_to_pc_damage == 5
    assert p2.pc_to_boss_damage == 0


def test_accumulate_pressure_both_deal_damage():
    p = CombatPressure()
    summary_pc = TurnSummary(actor_id="pc1", damage_dealt={"boss1": 3})
    summary_boss = TurnSummary(actor_id="boss1", damage_dealt={"pc1": 7})

    p = accumulate_pressure(
        p,
        summary_pc,
        actor_is_boss=False,
        target_is_boss={"boss1": True, "pc1": False},
        target_is_pc={"boss1": False, "pc1": True},
    )
    p = accumulate_pressure(
        p,
        summary_boss,
        actor_is_boss=True,
        target_is_boss={"boss1": True, "pc1": False},
        target_is_pc={"boss1": False, "pc1": True},
    )
    assert p.pc_to_boss_damage == 3
    assert p.boss_to_pc_damage == 7


# ---------------------------------------------------------------------------
# advance_pressure_round — stalemate escalation
# ---------------------------------------------------------------------------


def test_advance_round_with_damage_resets_counter():
    p = CombatPressure(zero_damage_rounds=1, pc_to_boss_damage=5, boss_to_pc_damage=0)
    p2, escalated = advance_pressure_round(p)
    assert not escalated
    assert p2.zero_damage_rounds == 0
    assert p2.pc_to_boss_damage == 0


def test_advance_round_stalemate_increments_counter():
    p = CombatPressure(zero_damage_rounds=0)
    p2, escalated = advance_pressure_round(p)
    assert not escalated
    assert p2.zero_damage_rounds == 1
    assert p2.level == PressureLevel.NORMAL


def test_advance_round_two_stalemates_escalate_to_hard():
    p = CombatPressure(zero_damage_rounds=1, level=PressureLevel.NORMAL)
    p2, escalated = advance_pressure_round(p)
    assert escalated
    assert p2.level == PressureLevel.HARD
    assert p2.zero_damage_rounds == 0


def test_advance_round_hard_two_stalemates_escalate_to_ultra_hard():
    p = CombatPressure(zero_damage_rounds=1, level=PressureLevel.HARD)
    p2, escalated = advance_pressure_round(p)
    assert escalated
    assert p2.level == PressureLevel.ULTRA_HARD
    assert p2.zero_damage_rounds == 0


def test_advance_round_ultra_hard_no_further_escalation():
    p = CombatPressure(zero_damage_rounds=5, level=PressureLevel.ULTRA_HARD)
    p2, escalated = advance_pressure_round(p)
    assert not escalated
    assert p2.level == PressureLevel.ULTRA_HARD


# ---------------------------------------------------------------------------
# Scenario trigger: round_reached
# ---------------------------------------------------------------------------


def _make_simple_state(events: list[ScenarioEvent]) -> GameState:
    from tacex_gm.models.character import Character

    scenario = Scenario(
        scenario_id="test",
        title="test",
        map_size=(10, 10),
        events=events,
    )
    pc = Character(
        id="pc1",
        name="PC",
        player_id="player1",
        faction="pc",
        tai=5,
        rei=5,
        kou=5,
        jutsu=1,
        max_hp=20,
        max_mp=4,
        hp=20,
        mp=4,
        evasion_dice=3,
        max_evasion_dice=3,
        position=(0, 0),
    )
    return GameState(
        room_id="room1",
        seed=42,
        map_size=(10, 10),
        characters=[pc],
        scenario=scenario,
    )


def test_events_for_round_fires_at_matching_round():
    ev = ScenarioEvent(
        id="ev1",
        trigger=TriggerRoundReached(type="round_reached", round=3),
        actions=[ActionShowNarrative(type="show_narrative", text="Round 3!")],
    )
    state = _make_simple_state([ev])
    assert events_for_round(state, 3) == [ev]


def test_events_for_round_fires_at_or_after():
    ev = ScenarioEvent(
        id="ev1",
        trigger=TriggerRoundReached(type="round_reached", round=2),
        actions=[],
    )
    state = _make_simple_state([ev])
    assert events_for_round(state, 5) == [ev]


def test_events_for_round_does_not_fire_early():
    ev = ScenarioEvent(
        id="ev1",
        trigger=TriggerRoundReached(type="round_reached", round=5),
        actions=[],
    )
    state = _make_simple_state([ev])
    assert events_for_round(state, 3) == []


def test_events_for_round_skips_fired_once_events():
    ev = ScenarioEvent(
        id="ev1",
        trigger=TriggerRoundReached(type="round_reached", round=1),
        actions=[],
        once=True,
        fired=True,
    )
    state = _make_simple_state([ev])
    assert events_for_round(state, 1) == []


def test_events_for_round_repeating_event_fires_again():
    ev = ScenarioEvent(
        id="ev1",
        trigger=TriggerRoundReached(type="round_reached", round=1),
        actions=[],
        once=False,
        fired=True,  # fired=True but once=False → still fires
    )
    state = _make_simple_state([ev])
    assert events_for_round(state, 1) == [ev]


# ---------------------------------------------------------------------------
# Scenario trigger: character_dies
# ---------------------------------------------------------------------------


def test_events_for_character_death_matches_id():
    ev = ScenarioEvent(
        id="ev_death",
        trigger=TriggerCharacterDies(type="character_dies", character_id="enemy1"),
        actions=[],
    )
    state = _make_simple_state([ev])
    assert events_for_character_death(state, "enemy1") == [ev]
    assert events_for_character_death(state, "enemy2") == []


# ---------------------------------------------------------------------------
# Scenario trigger: enter_zone
# ---------------------------------------------------------------------------


def test_events_for_zone_entry_pc_in_zone():
    from tacex_gm.models.character import Character

    ev = ScenarioEvent(
        id="ev_zone",
        trigger=TriggerEnterZone(
            type="enter_zone",
            zone=((5, 5), (10, 10)),
            who=["any_pc"],
        ),
        actions=[],
    )
    scenario = Scenario(scenario_id="t", title="t", map_size=(20, 20), events=[ev])
    pc = Character(
        id="pc1",
        name="PC",
        player_id="p1",
        faction="pc",
        tai=5,
        rei=5,
        kou=5,
        jutsu=1,
        max_hp=20,
        max_mp=4,
        hp=20,
        mp=4,
        evasion_dice=3,
        max_evasion_dice=3,
        position=(7, 8),
    )
    state = GameState(room_id="r", seed=1, map_size=(20, 20), characters=[pc], scenario=scenario)
    assert events_for_zone_entry(state, "pc1") == [ev]


def test_events_for_zone_entry_pc_outside_zone():
    from tacex_gm.models.character import Character

    ev = ScenarioEvent(
        id="ev_zone",
        trigger=TriggerEnterZone(type="enter_zone", zone=((5, 5), (10, 10)), who=["any_pc"]),
        actions=[],
    )
    scenario = Scenario(scenario_id="t", title="t", map_size=(20, 20), events=[ev])
    pc = Character(
        id="pc1",
        name="PC",
        player_id="p1",
        faction="pc",
        tai=5,
        rei=5,
        kou=5,
        jutsu=1,
        max_hp=20,
        max_mp=4,
        hp=20,
        mp=4,
        evasion_dice=3,
        max_evasion_dice=3,
        position=(1, 1),
    )
    state = GameState(room_id="r", seed=1, map_size=(20, 20), characters=[pc], scenario=scenario)
    assert events_for_zone_entry(state, "pc1") == []


# ---------------------------------------------------------------------------
# Scenario trigger: object_destroyed
# ---------------------------------------------------------------------------


def test_events_for_object_destroyed_matches():
    ev = ScenarioEvent(
        id="ev_obj",
        trigger=TriggerObjectDestroyed(type="object_destroyed", object_id="pillar_a"),
        actions=[],
    )
    state = _make_simple_state([ev])
    assert events_for_object_destroyed(state, "pillar_a") == [ev]
    assert events_for_object_destroyed(state, "pillar_b") == []


# ---------------------------------------------------------------------------
# apply_map_object_damage
# ---------------------------------------------------------------------------


def _state_with_object(obj_id: str, strength: int, armor: int = 0) -> GameState:
    obj = MapObject(id=obj_id, position=(3, 3), strength=strength, armor=armor)
    base = _make_simple_state([])
    return base.model_copy(update={"objects": [obj]})


def test_apply_map_object_damage_reduces_strength():
    state = _state_with_object("wall1", strength=10)
    new_state, destroyed = apply_map_object_damage(state, "wall1", 4)
    assert not destroyed
    assert new_state.objects[0].strength == 6


def test_apply_map_object_damage_destroys_at_zero():
    state = _state_with_object("wall1", strength=5)
    new_state, destroyed = apply_map_object_damage(state, "wall1", 5)
    assert destroyed
    assert new_state.objects[0].strength == 0


def test_apply_map_object_damage_armor_reduces_damage():
    state = _state_with_object("wall1", strength=10, armor=3)
    new_state, destroyed = apply_map_object_damage(state, "wall1", 5)
    # effective = 5 - 3 = 2
    assert new_state.objects[0].strength == 8
    assert not destroyed


def test_apply_map_object_damage_no_negative_strength():
    state = _state_with_object("wall1", strength=3)
    new_state, destroyed = apply_map_object_damage(state, "wall1", 100)
    assert destroyed
    assert new_state.objects[0].strength == 0


# ---------------------------------------------------------------------------
# mark_event_fired
# ---------------------------------------------------------------------------


def test_mark_event_fired_sets_flag():
    ev = ScenarioEvent(
        id="ev1",
        trigger=TriggerRoundReached(type="round_reached", round=1),
        actions=[],
        once=True,
        fired=False,
    )
    state = _make_simple_state([ev])
    new_state = mark_event_fired(state, "ev1")
    assert new_state.scenario.events[0].fired is True


def test_mark_event_fired_only_marks_once_events():
    ev = ScenarioEvent(
        id="ev1",
        trigger=TriggerRoundReached(type="round_reached", round=1),
        actions=[],
        once=False,
        fired=False,
    )
    state = _make_simple_state([ev])
    new_state = mark_event_fired(state, "ev1")
    # once=False events are not marked fired
    assert new_state.scenario.events[0].fired is False


def test_mark_event_fired_unknown_id_is_noop():
    ev = ScenarioEvent(
        id="ev1",
        trigger=TriggerRoundReached(type="round_reached", round=1),
        actions=[],
    )
    state = _make_simple_state([ev])
    new_state = mark_event_fired(state, "nonexistent")
    assert new_state.scenario.events[0].fired is False
