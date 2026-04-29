"""Scenario trigger evaluation (GM spec §14-4).

Phase 2 supported: enter_zone, character_dies.
Phase 6 adds:    round_reached, object_destroyed.
Phase 7 adds:    hp_threshold, compound.

All evaluators are pure functions that accept the current GameState and
relevant context, returning a list of ScenarioEvent IDs that should fire.
Callers are responsible for applying actions and marking events as fired.
"""

from __future__ import annotations

from tacex_gm.models.scenario import (
    ScenarioEvent,
    Trigger,
    TriggerCharacterDies,
    TriggerCompound,
    TriggerEnterZone,
    TriggerHPThreshold,
    TriggerObjectDestroyed,
    TriggerRoundReached,
)
from tacex_gm.models.state import GameState

Coordinate = tuple[int, int]


# ---------------------------------------------------------------------------
# Per-trigger matchers
# ---------------------------------------------------------------------------


def _matches_enter_zone(
    trigger: TriggerEnterZone,
    state: GameState,
    moved_character_id: str,
) -> bool:
    char = state.find_character(moved_character_id)
    if char is None:
        return False

    # "any_pc" → any character with faction == "pc"
    who = trigger.who
    if "any_pc" in who:
        if char.faction != "pc":
            return False
    elif moved_character_id not in who:
        return False

    (x0, y0), (x1, y1) = trigger.zone
    x, y = char.position
    return min(x0, x1) <= x <= max(x0, x1) and min(y0, y1) <= y <= max(y0, y1)


def _matches_character_dies(
    trigger: TriggerCharacterDies,
    died_character_id: str,
) -> bool:
    return trigger.character_id == died_character_id


def _matches_round_reached(
    trigger: TriggerRoundReached,
    round_number: int,
) -> bool:
    return round_number >= trigger.round


def _matches_object_destroyed(
    trigger: TriggerObjectDestroyed,
    destroyed_object_id: str,
) -> bool:
    return trigger.object_id == destroyed_object_id


def _matches_hp_threshold(
    trigger: TriggerHPThreshold,
    state: GameState,
) -> bool:
    """True when the named character's HP fraction is at or below threshold_pct."""
    char = state.find_character(trigger.character_id)
    if char is None or char.max_hp == 0:
        return False
    return (char.hp / char.max_hp) <= trigger.threshold_pct


def _matches_trigger(trigger: Trigger, state: GameState, context: dict) -> bool:  # type: ignore[type-arg]
    """Dispatch to the appropriate matcher, including compound logic."""
    if isinstance(trigger, TriggerEnterZone):
        return _matches_enter_zone(trigger, state, context.get("character_id", ""))
    if isinstance(trigger, TriggerCharacterDies):
        return _matches_character_dies(trigger, context.get("character_id", ""))
    if isinstance(trigger, TriggerRoundReached):
        return _matches_round_reached(trigger, context.get("round_number", 0))
    if isinstance(trigger, TriggerObjectDestroyed):
        return _matches_object_destroyed(trigger, context.get("object_id", ""))
    if isinstance(trigger, TriggerHPThreshold):
        return _matches_hp_threshold(trigger, state)
    if isinstance(trigger, TriggerCompound):
        results = [_matches_trigger(c, state, context) for c in trigger.conditions]
        return all(results) if trigger.op == "and" else any(results)
    return False


# ---------------------------------------------------------------------------
# Batch evaluators
# ---------------------------------------------------------------------------


def events_for_zone_entry(
    state: GameState,
    moved_character_id: str,
) -> list[ScenarioEvent]:
    """Return matching unfired enter_zone events after a character moves."""
    result = []
    for ev in state.scenario.events:
        if ev.fired and ev.once:
            continue
        if isinstance(ev.trigger, TriggerEnterZone) and _matches_enter_zone(
            ev.trigger, state, moved_character_id
        ):
            result.append(ev)
    return result


def events_for_character_death(
    state: GameState,
    died_character_id: str,
) -> list[ScenarioEvent]:
    """Return matching unfired character_dies events."""
    result = []
    for ev in state.scenario.events:
        if ev.fired and ev.once:
            continue
        if isinstance(ev.trigger, TriggerCharacterDies) and _matches_character_dies(
            ev.trigger, died_character_id
        ):
            result.append(ev)
    return result


def events_for_round(
    state: GameState,
    round_number: int,
) -> list[ScenarioEvent]:
    """Return matching unfired round_reached events (Phase 6)."""
    result = []
    for ev in state.scenario.events:
        if ev.fired and ev.once:
            continue
        if isinstance(ev.trigger, TriggerRoundReached) and _matches_round_reached(
            ev.trigger, round_number
        ):
            result.append(ev)
    return result


def events_for_object_destroyed(
    state: GameState,
    destroyed_object_id: str,
) -> list[ScenarioEvent]:
    """Return matching unfired object_destroyed events (Phase 6)."""
    result = []
    for ev in state.scenario.events:
        if ev.fired and ev.once:
            continue
        if isinstance(ev.trigger, TriggerObjectDestroyed) and _matches_object_destroyed(
            ev.trigger, destroyed_object_id
        ):
            result.append(ev)
    return result


def events_for_hp_threshold(
    state: GameState,
) -> list[ScenarioEvent]:
    """Return matching unfired hp_threshold events given current state (Phase 7)."""
    result = []
    for ev in state.scenario.events:
        if ev.fired and ev.once:
            continue
        if isinstance(ev.trigger, TriggerHPThreshold) and _matches_hp_threshold(
            ev.trigger, state
        ):
            result.append(ev)
    return result


def events_for_compound(
    state: GameState,
    context: dict,  # type: ignore[type-arg]
) -> list[ScenarioEvent]:
    """Return matching unfired compound events (Phase 7)."""
    result = []
    for ev in state.scenario.events:
        if ev.fired and ev.once:
            continue
        if isinstance(ev.trigger, TriggerCompound) and _matches_trigger(
            ev.trigger, state, context
        ):
            result.append(ev)
    return result


# ---------------------------------------------------------------------------
# State mutation helpers
# ---------------------------------------------------------------------------


def mark_event_fired(state: GameState, event_id: str) -> GameState:
    """Return a new GameState with the named scenario event marked as fired."""
    new_events = []
    for ev in state.scenario.events:
        if ev.id == event_id and ev.once:
            new_events.append(ev.model_copy(update={"fired": True}))
        else:
            new_events.append(ev)
    new_scenario = state.scenario.model_copy(update={"events": new_events})
    return state.model_copy(update={"scenario": new_scenario})


def apply_map_object_damage(
    state: GameState,
    object_id: str,
    damage: int,
) -> tuple[GameState, bool]:
    """Apply damage to a MapObject.  Returns (new_state, destroyed).

    ``destroyed`` is True when the object's strength reaches 0.
    Armor on the object reduces incoming damage (mirroring character rules).
    """
    new_objects = []
    destroyed = False
    for obj in state.objects:
        if obj.id == object_id:
            effective = max(0, damage - obj.armor)
            new_strength = max(0, obj.strength - effective)
            if new_strength == 0:
                destroyed = True
            new_objects.append(obj.model_copy(update={"strength": new_strength}))
        else:
            new_objects.append(obj)
    return state.model_copy(update={"objects": new_objects}), destroyed
