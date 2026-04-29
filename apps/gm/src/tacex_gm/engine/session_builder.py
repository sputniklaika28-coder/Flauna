"""Build the initial :class:`GameState` for a room (Phase 2).

Converts a :class:`Scenario` + enemy-catalog templates into a fully-hydrated
``GameState`` ready to enter the ``"combat"`` phase.

Design constraints (from spec §15-2 / §15-3):
- One PC slot (player_id supplied at call time).
- Enemy characters materialised from ``enemies.yaml`` templates.
- MVP: no aptitude/skill transfer beyond basic Character fields.
"""

from __future__ import annotations

import random
from typing import Any

from tacex_gm.models import Character, GameState, NPCEvasionPolicy
from tacex_gm.models.scenario import Scenario

Coordinate = tuple[int, int]

# Default PC starting stats for Phase 2 MVP (§15-3).
_DEFAULT_PC = {
    "tai": 5,
    "rei": 5,
    "kou": 5,
    "jutsu": 1,
    "max_hp": 20,
    "max_mp": 4,
    "hp": 20,
    "mp": 4,
    "evasion_dice": 3,
    "max_evasion_dice": 3,
    "armor_value": 0,
    "equipped_weapons": ["kogatana"],
    "inventory": {"katashiro": 7},
    "skills": [],
    "arts": [],
    "aptitudes": [],
}

# Fallback PC start position when scenario does not define one.
_DEFAULT_PC_POSITION: Coordinate = (5, 10)


def build_initial_state(
    room_id: str,
    scenario: Scenario,
    enemy_catalog: dict[str, dict[str, Any]],
    player_id: str,
    player_name: str,
    pc_position: Coordinate | None = None,
    seed: int | None = None,
) -> tuple[GameState, str]:
    """Return ``(GameState, pc_character_id)`` ready for combat.

    The returned state has ``phase="combat"`` and a valid ``turn_order``
    so that combat can begin immediately after the first WebSocket handshake.
    """

    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    pc_id = f"pc-{player_id[:8]}"
    pc_start = pc_position or _DEFAULT_PC_POSITION

    pc = Character(
        id=pc_id,
        name=player_name,
        player_id=player_id,
        faction="pc",
        position=pc_start,
        **_DEFAULT_PC,
    )

    enemies: list[Character] = []
    for sc_char in scenario.characters:
        if sc_char.faction != "enemy":
            continue
        template_id = sc_char.template
        if template_id is None:
            continue
        template = enemy_catalog.get(template_id)
        if template is None:
            continue
        base = dict(template)
        base.update(sc_char.overrides)
        # Mandatory fields from ScenarioCharacter override template.
        base["id"] = sc_char.id
        base["name"] = sc_char.name
        base["faction"] = sc_char.faction
        base["position"] = sc_char.position
        base["is_boss"] = sc_char.is_boss

        # Parse evasion_policy if dict present.
        if "evasion_policy" in base and isinstance(base["evasion_policy"], dict):
            base["evasion_policy"] = NPCEvasionPolicy(**base["evasion_policy"])

        # Remove keys not in Character.
        base.pop("aptitudes", None)
        base.pop("description", None)

        enemies.append(Character.model_validate(base))

    characters = [pc, *enemies]

    # Turn order: PCs first in Phase 2 (simplified — full initiative in Phase 3).
    turn_order = [c.id for c in characters]

    next_event_id = 1
    state = GameState(
        room_id=room_id,
        version=1,
        seed=seed,
        phase="combat",
        turn_order=turn_order,
        current_turn_index=0,
        round_number=1,
        characters=characters,
        map_size=scenario.map_size,
        obstacles=scenario.obstacles,
        scenario=scenario,
        next_event_id=next_event_id,
    )
    return state, pc_id


def build_character_from_template(
    template: dict[str, Any],
    *,
    char_id: str,
    position: Coordinate,
) -> Character:
    """Build a Character from an enemy-catalog template dict.

    Used by spawn_enemy scenario actions (Phase 6).
    """
    from tacex_gm.models import NPCEvasionPolicy

    base = dict(template)
    base["id"] = char_id
    base["faction"] = base.get("faction", "enemy")
    base["position"] = position

    if "evasion_policy" in base and isinstance(base["evasion_policy"], dict):
        base["evasion_policy"] = NPCEvasionPolicy(**base["evasion_policy"])

    base.pop("aptitudes", None)
    base.pop("description", None)
    return Character.model_validate(base)
