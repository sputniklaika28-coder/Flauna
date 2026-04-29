"""Phase 7 mechanics tests: hp_threshold/compound triggers, assessment, growth, ally_npc."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tacex_gm.engine.assessment import enter_assessment, score_session
from tacex_gm.engine.growth import GrowthProposal, apply_growth, propose_growth
from tacex_gm.engine.scenario_triggers import (
    events_for_compound,
    events_for_hp_threshold,
)
from tacex_gm.engine.victory import check_combat_outcome
from tacex_gm.models.character import Character
from tacex_gm.models.scenario import (
    ActionShowNarrative,
    FailureRoundLimit,
    Scenario,
    ScenarioEvent,
    TriggerCharacterDies,
    TriggerCompound,
    TriggerHPThreshold,
    TriggerRoundReached,
    VictoryAllEnemiesDefeated,
    VictoryReachZone,
)
from tacex_gm.models.state import GameState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pc(
    char_id: str = "pc1",
    hp: int = 20,
    max_hp: int = 20,
    position: tuple[int, int] = (0, 0),
) -> Character:
    return Character(
        id=char_id,
        name="テスター",
        player_id="player1",
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
        position=position,
    )


def _make_enemy(
    char_id: str = "enemy1", hp: int = 10, position: tuple[int, int] = (5, 5)
) -> Character:
    return Character(
        id=char_id,
        name="鬱黒揚羽",
        faction="enemy",
        tai=3,
        rei=3,
        kou=3,
        jutsu=0,
        max_hp=10,
        max_mp=0,
        hp=hp,
        mp=0,
        evasion_dice=1,
        max_evasion_dice=1,
        position=position,
    )


def _make_ally_npc(char_id: str = "ally1", hp: int = 15) -> Character:
    return Character(
        id=char_id,
        name="味方キャラ",
        faction="ally_npc",
        tai=4,
        rei=4,
        kou=4,
        jutsu=0,
        max_hp=15,
        max_mp=2,
        hp=hp,
        mp=2,
        evasion_dice=2,
        max_evasion_dice=2,
        position=(1, 1),
    )


def _make_state(
    characters: list[Character],
    events: list[ScenarioEvent] | None = None,
    round_number: int = 1,
    victory_conditions=None,
    failure_conditions=None,
) -> GameState:
    scenario = Scenario(
        scenario_id="test",
        title="test",
        map_size=(20, 20),
        events=events or [],
        victory_conditions=victory_conditions or [],
        failure_conditions=failure_conditions or [],
    )
    return GameState(
        room_id="room1",
        seed=42,
        map_size=(20, 20),
        characters=characters,
        round_number=round_number,
        scenario=scenario,
    )


# ---------------------------------------------------------------------------
# TriggerHPThreshold model
# ---------------------------------------------------------------------------


def test_hp_threshold_valid():
    t = TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=0.5)
    assert t.threshold_pct == 0.5


def test_hp_threshold_boundary_zero():
    t = TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=0.0)
    assert t.threshold_pct == 0.0


def test_hp_threshold_boundary_one():
    t = TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=1.0)
    assert t.threshold_pct == 1.0


def test_hp_threshold_invalid_above_one():
    with pytest.raises(ValidationError):
        TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=1.5)


def test_hp_threshold_invalid_below_zero():
    with pytest.raises(ValidationError):
        TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=-0.1)


# ---------------------------------------------------------------------------
# events_for_hp_threshold
# ---------------------------------------------------------------------------


def _hp_threshold_event(char_id: str, threshold_pct: float) -> ScenarioEvent:
    return ScenarioEvent(
        id=f"ev_hp_{char_id}",
        trigger=TriggerHPThreshold(
            type="hp_threshold", character_id=char_id, threshold_pct=threshold_pct
        ),
        actions=[ActionShowNarrative(type="show_narrative", text="threshold hit")],
    )


def test_events_for_hp_threshold_fires_when_hp_at_threshold():
    # PC has 10/20 HP = 0.5 exactly → threshold 0.5 should fire
    pc = _make_pc(hp=10, max_hp=20)
    ev = _hp_threshold_event("pc1", 0.5)
    state = _make_state([pc], events=[ev])
    assert events_for_hp_threshold(state) == [ev]


def test_events_for_hp_threshold_fires_when_hp_below_threshold():
    # PC has 5/20 HP = 0.25 < 0.5
    pc = _make_pc(hp=5, max_hp=20)
    ev = _hp_threshold_event("pc1", 0.5)
    state = _make_state([pc], events=[ev])
    assert events_for_hp_threshold(state) == [ev]


def test_events_for_hp_threshold_no_fire_when_hp_above():
    # PC has 15/20 HP = 0.75 > 0.5
    pc = _make_pc(hp=15, max_hp=20)
    ev = _hp_threshold_event("pc1", 0.5)
    state = _make_state([pc], events=[ev])
    assert events_for_hp_threshold(state) == []


def test_events_for_hp_threshold_skips_fired_once_event():
    pc = _make_pc(hp=5, max_hp=20)
    ev = ScenarioEvent(
        id="ev_hp",
        trigger=TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=0.5),
        actions=[],
        once=True,
        fired=True,
    )
    state = _make_state([pc], events=[ev])
    assert events_for_hp_threshold(state) == []


def test_events_for_hp_threshold_repeating_fires_again():
    pc = _make_pc(hp=5, max_hp=20)
    ev = ScenarioEvent(
        id="ev_hp",
        trigger=TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=0.5),
        actions=[],
        once=False,
        fired=True,
    )
    state = _make_state([pc], events=[ev])
    assert events_for_hp_threshold(state) == [ev]


def test_events_for_hp_threshold_unknown_character_no_fire():
    pc = _make_pc(char_id="pc1", hp=5, max_hp=20)
    ev = _hp_threshold_event("unknown_char", 0.5)
    state = _make_state([pc], events=[ev])
    assert events_for_hp_threshold(state) == []


# ---------------------------------------------------------------------------
# TriggerCompound model
# ---------------------------------------------------------------------------


def test_compound_and_two_conditions():
    t = TriggerCompound(
        type="compound",
        op="and",
        conditions=[
            TriggerRoundReached(type="round_reached", round=3),
            TriggerCharacterDies(type="character_dies", character_id="enemy1"),
        ],
    )
    assert t.op == "and"
    assert len(t.conditions) == 2


def test_compound_or_two_conditions():
    t = TriggerCompound(
        type="compound",
        op="or",
        conditions=[
            TriggerRoundReached(type="round_reached", round=3),
            TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=0.25),
        ],
    )
    assert t.op == "or"


def test_compound_requires_at_least_two_conditions():
    with pytest.raises(ValidationError):
        TriggerCompound(
            type="compound",
            op="and",
            conditions=[TriggerRoundReached(type="round_reached", round=1)],
        )


def test_compound_max_depth_3_valid():
    inner = TriggerCompound(
        type="compound",
        op="or",
        conditions=[
            TriggerRoundReached(type="round_reached", round=1),
            TriggerCharacterDies(type="character_dies", character_id="e1"),
        ],
    )
    outer = TriggerCompound(
        type="compound",
        op="and",
        conditions=[
            inner,
            TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=0.5),
        ],
    )
    assert len(outer.conditions) == 2


def test_compound_exceeds_max_depth_raises():
    simple = TriggerRoundReached(type="round_reached", round=1)
    simple2 = TriggerCharacterDies(type="character_dies", character_id="e1")
    # depth=1
    depth1 = TriggerCompound(type="compound", op="or", conditions=[simple, simple2])
    # depth=2
    depth2 = TriggerCompound(type="compound", op="and", conditions=[depth1, simple])
    # depth=3 — valid at maximum
    depth3 = TriggerCompound(type="compound", op="or", conditions=[depth2, simple])
    # depth=4 — should raise
    with pytest.raises(ValidationError):
        TriggerCompound(type="compound", op="and", conditions=[depth3, simple])


# ---------------------------------------------------------------------------
# events_for_compound
# ---------------------------------------------------------------------------


def _compound_event(trigger: TriggerCompound, event_id: str = "ev_compound") -> ScenarioEvent:
    return ScenarioEvent(
        id=event_id,
        trigger=trigger,
        actions=[ActionShowNarrative(type="show_narrative", text="compound hit")],
    )


def test_compound_and_fires_when_all_match():
    pc = _make_pc(hp=5, max_hp=20)
    trigger = TriggerCompound(
        type="compound",
        op="and",
        conditions=[
            TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=0.5),
            TriggerRoundReached(type="round_reached", round=3),
        ],
    )
    ev = _compound_event(trigger)
    state = _make_state([pc], events=[ev], round_number=3)
    result = events_for_compound(state, {"round_number": 3})
    assert result == [ev]


def test_compound_and_does_not_fire_when_one_fails():
    pc = _make_pc(hp=15, max_hp=20)  # HP above threshold
    trigger = TriggerCompound(
        type="compound",
        op="and",
        conditions=[
            TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=0.5),
            TriggerRoundReached(type="round_reached", round=3),
        ],
    )
    ev = _compound_event(trigger)
    state = _make_state([pc], events=[ev], round_number=3)
    result = events_for_compound(state, {"round_number": 3})
    assert result == []


def test_compound_or_fires_when_any_matches():
    pc = _make_pc(hp=15, max_hp=20)  # HP above threshold
    trigger = TriggerCompound(
        type="compound",
        op="or",
        conditions=[
            TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=0.5),
            TriggerRoundReached(type="round_reached", round=3),
        ],
    )
    ev = _compound_event(trigger)
    # round=3 matches even though hp doesn't
    state = _make_state([pc], events=[ev], round_number=3)
    result = events_for_compound(state, {"round_number": 3})
    assert result == [ev]


def test_compound_or_does_not_fire_when_none_matches():
    pc = _make_pc(hp=15, max_hp=20)
    trigger = TriggerCompound(
        type="compound",
        op="or",
        conditions=[
            TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=0.5),
            TriggerRoundReached(type="round_reached", round=5),
        ],
    )
    ev = _compound_event(trigger)
    state = _make_state([pc], events=[ev], round_number=3)
    result = events_for_compound(state, {"round_number": 3})
    assert result == []


def test_compound_skips_fired_once_event():
    pc = _make_pc(hp=5, max_hp=20)
    trigger = TriggerCompound(
        type="compound",
        op="or",
        conditions=[
            TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=0.5),
            TriggerRoundReached(type="round_reached", round=1),
        ],
    )
    ev = ScenarioEvent(
        id="ev_compound",
        trigger=trigger,
        actions=[],
        once=True,
        fired=True,
    )
    state = _make_state([pc], events=[ev], round_number=1)
    assert events_for_compound(state, {"round_number": 1}) == []


def test_nested_compound_and_fires():
    """Depth-2 compound: outer AND (inner OR, hp_threshold)."""
    pc = _make_pc(hp=5, max_hp=20)
    inner = TriggerCompound(
        type="compound",
        op="or",
        conditions=[
            TriggerRoundReached(type="round_reached", round=3),
            TriggerCharacterDies(type="character_dies", character_id="enemy1"),
        ],
    )
    outer = TriggerCompound(
        type="compound",
        op="and",
        conditions=[
            inner,
            TriggerHPThreshold(type="hp_threshold", character_id="pc1", threshold_pct=0.5),
        ],
    )
    ev = _compound_event(outer)
    state = _make_state([pc], events=[ev], round_number=3)
    result = events_for_compound(state, {"round_number": 3, "character_id": "enemy1"})
    assert result == [ev]


# ---------------------------------------------------------------------------
# ally_npc faction
# ---------------------------------------------------------------------------


def test_ally_npc_character_creation():
    ally = _make_ally_npc()
    assert ally.faction == "ally_npc"
    assert ally.player_id is None


def test_ally_npc_with_player_id_raises():
    with pytest.raises(ValidationError):
        Character(
            id="ally1",
            name="味方",
            player_id="player1",  # not allowed for non-pc
            faction="ally_npc",
            tai=4,
            rei=4,
            kou=4,
            jutsu=0,
            max_hp=15,
            max_mp=2,
            hp=15,
            mp=2,
            evasion_dice=2,
            max_evasion_dice=2,
            position=(1, 1),
        )


def test_ally_npc_not_counted_as_enemy_in_victory():
    ally = _make_ally_npc()
    state = _make_state(
        [ally],
        victory_conditions=[VictoryAllEnemiesDefeated(type="all_enemies_defeated")],
    )
    # No enemies → victory condition is not satisfied (enemies list is empty)
    assert check_combat_outcome(state) is None


def test_ally_npc_not_counted_as_pc_in_defeat():
    from tacex_gm.models.scenario import FailureAllPCsDefeated

    ally = _make_ally_npc(hp=0)
    state = _make_state(
        [ally],
        failure_conditions=[FailureAllPCsDefeated(type="all_pcs_defeated")],
    )
    # ally_npc is not a PC → defeat condition not triggered
    assert check_combat_outcome(state) is None


# ---------------------------------------------------------------------------
# VictoryReachZone
# ---------------------------------------------------------------------------


def test_victory_reach_zone_pc_in_zone():
    pc = _make_pc(position=(12, 12))
    vc = VictoryReachZone(type="reach_zone", zone=((10, 10), (15, 15)), who=["any_pc"])
    state = _make_state([pc], victory_conditions=[vc])
    assert check_combat_outcome(state) == "victory"


def test_victory_reach_zone_pc_outside_zone():
    pc = _make_pc(position=(5, 5))
    vc = VictoryReachZone(type="reach_zone", zone=((10, 10), (15, 15)), who=["any_pc"])
    state = _make_state([pc], victory_conditions=[vc])
    assert check_combat_outcome(state) is None


def test_victory_reach_zone_dead_pc_ignored():
    pc = _make_pc(hp=0, position=(12, 12))
    vc = VictoryReachZone(type="reach_zone", zone=((10, 10), (15, 15)), who=["any_pc"])
    state = _make_state([pc], victory_conditions=[vc])
    assert check_combat_outcome(state) is None


def test_victory_reach_zone_enemy_ignored():
    enemy = _make_enemy(position=(12, 12))
    vc = VictoryReachZone(type="reach_zone", zone=((10, 10), (15, 15)), who=["any_pc"])
    state = _make_state([enemy], victory_conditions=[vc])
    assert check_combat_outcome(state) is None


# ---------------------------------------------------------------------------
# FailureRoundLimit
# ---------------------------------------------------------------------------


def test_failure_round_limit_exceeded():
    pc = _make_pc()
    fc = FailureRoundLimit(type="round_limit", round=5)
    state = _make_state([pc], failure_conditions=[fc], round_number=6)
    assert check_combat_outcome(state) == "defeat"


def test_failure_round_limit_at_limit_no_failure():
    pc = _make_pc()
    fc = FailureRoundLimit(type="round_limit", round=5)
    state = _make_state([pc], failure_conditions=[fc], round_number=5)
    assert check_combat_outcome(state) is None


def test_failure_round_limit_below_limit():
    pc = _make_pc()
    fc = FailureRoundLimit(type="round_limit", round=5)
    state = _make_state([pc], failure_conditions=[fc], round_number=3)
    assert check_combat_outcome(state) is None


# ---------------------------------------------------------------------------
# Assessment phase — score_session
# ---------------------------------------------------------------------------


def test_score_session_victory_all_alive_fast():
    pc = _make_pc()
    enemy = _make_enemy(hp=0)
    state = _make_state([pc, enemy], round_number=3)
    score = score_session(state, "victory")
    assert score.outcome == "victory"
    assert score.pcs_alive == 1
    assert score.pcs_total == 1
    assert score.enemies_defeated == 1
    assert score.enemies_total == 1
    assert score.rounds_taken == 3
    assert score.grade == "S"


def test_score_session_victory_all_alive_slow():
    pc = _make_pc()
    enemy = _make_enemy(hp=0)
    state = _make_state([pc, enemy], round_number=10)
    score = score_session(state, "victory")
    assert score.grade == "A"


def test_score_session_victory_half_pcs_alive():
    pc1 = _make_pc(char_id="pc1", hp=10)
    pc2 = _make_pc(char_id="pc2", hp=0)
    enemy = _make_enemy(hp=0)
    state = _make_state([pc1, pc2, enemy], round_number=5)
    score = score_session(state, "victory")
    assert score.pcs_alive == 1
    assert score.grade == "B"


def test_score_session_defeat():
    pc = _make_pc(hp=0)
    state = _make_state([pc])
    score = score_session(state, "defeat")
    assert score.outcome == "defeat"
    assert score.grade == "D"


# ---------------------------------------------------------------------------
# Assessment phase — enter_assessment
# ---------------------------------------------------------------------------


def test_enter_assessment_transitions_phase():
    pc = _make_pc()
    enemy = _make_enemy(hp=0)
    state = _make_state([pc, enemy], round_number=4)
    new_state, score = enter_assessment(state, "victory")
    assert new_state.phase == "assessment"
    assert new_state.assessment_result is not None
    assert new_state.assessment_result.outcome == "victory"


def test_enter_assessment_does_not_mutate_original():
    pc = _make_pc()
    state = _make_state([pc])
    original_phase = state.phase
    enter_assessment(state, "defeat")
    assert state.phase == original_phase


# ---------------------------------------------------------------------------
# Growth — propose_growth
# ---------------------------------------------------------------------------


def test_propose_growth_s_grade_has_candidates():
    pc = _make_pc()
    from tacex_gm.models.assessment import SessionScore

    score = SessionScore(
        outcome="victory",
        rounds_taken=3,
        pcs_alive=1,
        pcs_total=1,
        enemies_defeated=1,
        enemies_total=1,
        grade="S",
    )
    proposals = propose_growth(pc, score)
    assert len(proposals) > 0
    assert all(p.character_id == "pc1" for p in proposals)


def test_propose_growth_d_grade_empty():
    pc = _make_pc()
    from tacex_gm.models.assessment import SessionScore

    score = SessionScore(
        outcome="defeat",
        rounds_taken=10,
        pcs_alive=0,
        pcs_total=1,
        enemies_defeated=0,
        enemies_total=1,
        grade="D",
    )
    proposals = propose_growth(pc, score)
    assert proposals == []


def test_propose_growth_excludes_already_known_skill():
    pc = Character(
        id="pc1",
        name="テスター",
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
        position=(0, 0),
        skills=["回避強化"],
    )
    from tacex_gm.models.assessment import SessionScore

    score = SessionScore(
        outcome="victory",
        rounds_taken=3,
        pcs_alive=1,
        pcs_total=1,
        enemies_defeated=1,
        enemies_total=1,
        grade="A",
    )
    proposals = propose_growth(pc, score)
    skill_names = [p.name for p in proposals if p.grow_type == "skill"]
    assert "回避強化" not in skill_names


def test_propose_growth_only_pc_eligible():
    enemy = _make_enemy()
    from tacex_gm.models.assessment import SessionScore

    score = SessionScore(
        outcome="victory",
        rounds_taken=3,
        pcs_alive=1,
        pcs_total=1,
        enemies_defeated=1,
        enemies_total=1,
        grade="S",
    )
    proposals = propose_growth(enemy, score)
    assert proposals == []


def test_propose_growth_dead_pc_not_eligible():
    pc = _make_pc(hp=0)
    from tacex_gm.models.assessment import SessionScore

    score = SessionScore(
        outcome="victory",
        rounds_taken=3,
        pcs_alive=0,
        pcs_total=1,
        enemies_defeated=1,
        enemies_total=1,
        grade="B",
    )
    proposals = propose_growth(pc, score)
    assert proposals == []


# ---------------------------------------------------------------------------
# Growth — apply_growth
# ---------------------------------------------------------------------------


def test_apply_growth_adds_skill():
    pc = _make_pc()
    proposal = GrowthProposal(character_id="pc1", grow_type="skill", name="踏み込み")
    new_pc = apply_growth(pc, proposal)
    assert "踏み込み" in new_pc.skills
    assert "踏み込み" not in pc.skills


def test_apply_growth_adds_art():
    pc = _make_pc()
    proposal = GrowthProposal(character_id="pc1", grow_type="art", name="霊力放出")
    new_pc = apply_growth(pc, proposal)
    assert "霊力放出" in new_pc.arts


def test_apply_growth_duplicate_skill_is_noop():
    pc = Character(
        id="pc1",
        name="テスター",
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
        position=(0, 0),
        skills=["踏み込み"],
    )
    proposal = GrowthProposal(character_id="pc1", grow_type="skill", name="踏み込み")
    new_pc = apply_growth(pc, proposal)
    assert new_pc.skills.count("踏み込み") == 1


def test_apply_growth_wrong_character_raises():
    pc = _make_pc()
    proposal = GrowthProposal(character_id="other_pc", grow_type="skill", name="踏み込み")
    with pytest.raises(ValueError, match="other_pc"):
        apply_growth(pc, proposal)
