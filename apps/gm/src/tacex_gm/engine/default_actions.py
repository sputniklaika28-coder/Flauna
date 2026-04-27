"""Heuristic NPC default-action selector (GM spec §4-3, §10-5).

Used as the **fallback** when AI Phase 1 fails or returns an unparsable
``tool_call``. The decision tree follows ``DEFAULT_NPC_ACTIONS``:

1. ``has_enemy_in_range``     → ``do_simple_attack(target=nearest_enemy)``
2. ``can_approach_to_attack`` → ``do_movement_and_attack(target=nearest_pc, approach=mobility)``
3. ``default``                → ``skip_turn``

The selector is deliberately weapon-aware: it scans the actor's equipped
weapons and picks the first one that can reach the chosen target. This
mirrors the simplified §10-6 expansion done after a real AI tool call —
keeping the two paths consistent so test fixtures and golden masters
remain meaningful even when the LLM is unavailable.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from tacex_gm.models import (
    Character,
    GameState,
    MeleeAttack,
    Movement,
    RangedAttack,
    Skip,
    TurnAction,
    Weapon,
    lookup_range_difficulty,
)

from .geometry import calc_distance

Coordinate = tuple[int, int]


def select_default_action(
    actor: Character,
    state: GameState,
    weapon_catalog: Mapping[str, Weapon],
) -> TurnAction:
    """Return a safe ``TurnAction`` for the given actor.

    The returned action is always self-consistent — equipped weapons that
    were not present in ``weapon_catalog`` are silently skipped, and the
    function falls back to ``Skip`` whenever no viable plan exists.
    """

    targets = _living_opponents(actor, state)
    if not targets:
        return TurnAction(actor_id=actor.id, main_action=Skip(reason="no_targets"))

    weapons = _equipped_weapons(actor, weapon_catalog)
    if not weapons:
        return TurnAction(actor_id=actor.id, main_action=Skip(reason="no_weapon"))

    nearest = min(targets, key=lambda t: calc_distance(actor.position, t.position))
    distance = calc_distance(actor.position, nearest.position)

    # Branch 1: has_enemy_in_range — attack from current position.
    in_range_weapon = _pick_weapon_for_distance(weapons, distance)
    if in_range_weapon is not None:
        return TurnAction(
            actor_id=actor.id,
            main_action=_build_attack_main(in_range_weapon, nearest.id),
        )

    # Branch 2: can_approach_to_attack — try each weapon and take the first
    # plan whose post-move distance is reachable. Melee weapons use a target
    # of distance 1; ranged weapons aim for the closest band that hits.
    plan = _plan_approach(actor, nearest, weapons, state)
    if plan is not None:
        path, weapon = plan
        return TurnAction(
            actor_id=actor.id,
            first_move=Movement(path=path),
            main_action=_build_attack_main(weapon, nearest.id),
        )

    # Branch 3: default — skip with a diagnostic reason.
    return TurnAction(actor_id=actor.id, main_action=Skip(reason="cannot_reach"))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _living_opponents(actor: Character, state: GameState) -> list[Character]:
    rivals: list[Character] = []
    for character in state.characters:
        if character.id == actor.id or not character.is_alive:
            continue
        if _is_opponent(actor.faction, character.faction):
            rivals.append(character)
    return rivals


def _is_opponent(actor_faction: str, other_faction: str) -> bool:
    if actor_faction == "enemy":
        return other_faction == "pc"
    if actor_faction == "pc":
        return other_faction == "enemy"
    if actor_faction == "neutral":
        return other_faction != "neutral"
    return False


def _equipped_weapons(actor: Character, catalog: Mapping[str, Weapon]) -> list[Weapon]:
    found: list[Weapon] = []
    for weapon_id in actor.equipped_weapons:
        weapon = catalog.get(weapon_id)
        if weapon is not None:
            found.append(weapon)
    return found


def _can_hit(weapon: Weapon, distance: int) -> bool:
    if weapon.category == "melee":
        return distance <= 1
    if weapon.range_class is None:
        return False
    return lookup_range_difficulty(weapon.range_class, distance) is not None


def _pick_weapon_for_distance(weapons: Sequence[Weapon], distance: int) -> Weapon | None:
    """Prefer melee at adjacency, otherwise the first ranged weapon that hits."""

    if distance <= 1:
        for weapon in weapons:
            if weapon.category == "melee":
                return weapon
    for weapon in weapons:
        if _can_hit(weapon, distance):
            return weapon
    return None


def _plan_approach(
    actor: Character,
    target: Character,
    weapons: Sequence[Weapon],
    state: GameState,
) -> tuple[list[Coordinate], Weapon] | None:
    """Try to walk close enough that *some* equipped weapon can hit.

    For each weapon we compute the desired stand-off ``D``:
        - melee:     ``D = 1``
        - ranged:    smallest ``D`` such that ``lookup_range_difficulty`` ≠ None
                     and ``D <= max_movable_distance``.

    The path is built by stepping straight at the target via Chebyshev
    descent; if any step lands on an obstacle or another character we abort
    and try the next weapon. Phase 2 will replace this with an A* planner
    that respects line-of-sight — for the fallback table a greedy step is
    sufficient.
    """

    obstacles: set[Coordinate] = set(state.obstacles)
    occupied: set[Coordinate] = {
        c.position for c in state.characters if c.id != actor.id and c.is_alive
    }
    mobility = actor.mobility

    for weapon in weapons:
        desired_distance = _desired_stand_off(weapon)
        if desired_distance is None:
            continue
        path = _chebyshev_walk(
            start=actor.position,
            target=target.position,
            stop_at_distance=desired_distance,
            max_steps=mobility,
            obstacles=obstacles,
            occupied=occupied,
        )
        if path:
            return path, weapon
    return None


def _desired_stand_off(weapon: Weapon) -> int | None:
    if weapon.category == "melee":
        return 1
    if weapon.range_class is None:
        return None
    # Find the closest in-range distance band starting at 1 cell away.
    for distance in range(1, 12):
        if lookup_range_difficulty(weapon.range_class, distance) is not None:
            return distance
    return None


def _chebyshev_walk(
    *,
    start: Coordinate,
    target: Coordinate,
    stop_at_distance: int,
    max_steps: int,
    obstacles: set[Coordinate],
    occupied: set[Coordinate],
) -> list[Coordinate]:
    """Greedy Chebyshev descent toward ``target``.

    Stops once the walker is exactly ``stop_at_distance`` cells from the
    target or runs out of mobility. Returns an empty list if no path is
    available without stepping on obstacles or other characters.
    """

    if calc_distance(start, target) <= stop_at_distance:
        return []

    path: list[Coordinate] = []
    cursor = start
    for _ in range(max_steps):
        if calc_distance(cursor, target) <= stop_at_distance:
            break
        next_cell = _step_toward(cursor, target)
        if next_cell == cursor:
            break
        if next_cell in obstacles or next_cell in occupied:
            return []
        path.append(next_cell)
        cursor = next_cell
    if not path:
        return []
    if calc_distance(cursor, target) > stop_at_distance:
        return []
    return path


def _step_toward(cursor: Coordinate, target: Coordinate) -> Coordinate:
    cx, cy = cursor
    tx, ty = target
    dx = (tx > cx) - (tx < cx)
    dy = (ty > cy) - (ty < cy)
    return (cx + dx, cy + dy)


def _build_attack_main(
    weapon: Weapon,
    target_id: str,
) -> MeleeAttack | RangedAttack:
    dice = max(1, weapon.base_dice)
    if weapon.category == "melee":
        return MeleeAttack(
            weapon_id=weapon.id,
            dice_distribution=[dice],
            targets=[target_id],
        )
    return RangedAttack(
        weapon_id=weapon.id,
        dice_distribution=[dice],
        targets=[target_id],
    )


# Re-export the named decision tree so callers / metrics can reference it
# symbolically (matches the spec §4-3 table).
DEFAULT_NPC_ACTIONS: tuple[str, ...] = (
    "has_enemy_in_range",
    "can_approach_to_attack",
    "default",
)


__all__ = [
    "DEFAULT_NPC_ACTIONS",
    "select_default_action",
]
