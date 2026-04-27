"""Attack / evasion / damage resolution (GM spec §9-1, §9-6, §10-1).

This module is rule-engine only — it does not mutate room state directly.
Callers receive structured outcome dataclasses describing what would happen,
and apply mutations via the higher-level state-machine layer.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from tacex_gm.models.character import Character
from tacex_gm.models.constants import (
    DIFFICULTY_NORMAL,
    DIFFICULTY_TABLE,
    RangeClass,
    clamp_difficulty,
    lookup_range_difficulty,
)
from tacex_gm.models.damage import AbilityBonus, DamageSpec
from tacex_gm.models.pending import IncomingAttack
from tacex_gm.models.weapon import Weapon

from .dice import DiceEngine, DiceResult
from .geometry import calc_distance, has_line_of_sight

Coordinate = tuple[int, int]


class CombatResolutionError(ValueError):
    """Raised when an attack inputs are inconsistent (e.g. mismatched targets)."""


@dataclass(frozen=True)
class HitOutcome:
    """Per-target outcome of an attack pool roll (§9-1)."""

    weapon_id: str
    attacker_id: str
    target_id: str
    distance: int
    difficulty: int
    dice_used: int
    roll: DiceResult
    successes: int
    hit: bool
    out_of_range: bool = False
    line_of_sight_blocked: bool = False


@dataclass(frozen=True)
class EvasionOutcome:
    """Result of resolving a single ``EvasionRequest`` (§9-1)."""

    pending_id: str
    target_id: str
    dice_used: int
    difficulty: int
    roll: DiceResult
    successes: int
    succeeded: bool


@dataclass(frozen=True)
class DamageBreakdown:
    """Detailed damage computation for one incoming attack (§6-8)."""

    attacker_id: str
    target_id: str
    weapon_id: str
    damage_type: str
    base_roll: DiceResult | None
    base_damage: int
    ability_bonus: int
    raw_total: int
    armor_reduction: int
    final_damage: int
    hp_before: int
    hp_after: int
    notes: list[str] = field(default_factory=list)


def melee_attack_difficulty(*, style_modifier: int = 0) -> int:
    """Melee attacks use NORMAL by default; style modifier shifts the threshold.

    A ``style_modifier`` of ``-1`` means *easier* (e.g. 攻撃集中). The result is
    always clamped to ``KIDS..ULTRA_HARD``.
    """

    return clamp_difficulty(DIFFICULTY_NORMAL + style_modifier)


def ranged_attack_difficulty(
    range_class: RangeClass,
    distance: int,
    *,
    style_modifier: int = 0,
) -> int | None:
    """Return the threshold for a ranged attack, or ``None`` if out of range."""

    label = lookup_range_difficulty(range_class, distance)
    if label is None:
        return None
    return clamp_difficulty(DIFFICULTY_TABLE[label] + style_modifier)


async def resolve_attack(
    *,
    attacker: Character,
    weapon: Weapon,
    targets: Sequence[Character],
    dice_distribution: Sequence[int],
    dice_engine: DiceEngine,
    obstacles: Iterable[Coordinate] = (),
    style_modifier: int = 0,
) -> list[HitOutcome]:
    """Run one attack action.

    Each ``(target, dice_count)`` pair becomes an independent ``roll_pool``
    (§9-1: 攻撃判定と回避判定は完全独立). Out-of-range or LoS-blocked targets
    short-circuit to a zero-success outcome without rolling — callers can use
    the flags to render appropriate narration.
    """

    if len(targets) != len(dice_distribution):
        raise CombatResolutionError("targets and dice_distribution length mismatch")

    obstacle_list = list(obstacles)
    outcomes: list[HitOutcome] = []
    for target, dice_count in zip(targets, dice_distribution, strict=True):
        if dice_count < 0:
            raise CombatResolutionError(f"dice_count for {target.id} must be >= 0")
        distance = calc_distance(attacker.position, target.position)

        out_of_range = False
        los_blocked = False
        difficulty: int

        if weapon.category == "melee":
            difficulty = melee_attack_difficulty(style_modifier=style_modifier)
            if distance > 1:
                out_of_range = True
        else:
            if weapon.range_class is None:
                raise CombatResolutionError(
                    f"weapon {weapon.id} is {weapon.category} but has no range_class"
                )
            difficulty_or_none = ranged_attack_difficulty(
                weapon.range_class, distance, style_modifier=style_modifier
            )
            if difficulty_or_none is None:
                out_of_range = True
                difficulty = clamp_difficulty(6 + style_modifier)
            else:
                difficulty = difficulty_or_none
            if not out_of_range and not has_line_of_sight(
                attacker.position, target.position, obstacle_list
            ):
                los_blocked = True

        if out_of_range or los_blocked or dice_count == 0:
            empty = DiceResult(
                command=f"{dice_count}d6>={difficulty}",
                rolls=[],
                successes=0,
                sum=0,
                success=False,
            )
            outcomes.append(
                HitOutcome(
                    weapon_id=weapon.id,
                    attacker_id=attacker.id,
                    target_id=target.id,
                    distance=distance,
                    difficulty=difficulty,
                    dice_used=dice_count,
                    roll=empty,
                    successes=0,
                    hit=False,
                    out_of_range=out_of_range,
                    line_of_sight_blocked=los_blocked,
                )
            )
            continue

        roll = await dice_engine.roll_pool(count=dice_count, threshold=difficulty)
        outcomes.append(
            HitOutcome(
                weapon_id=weapon.id,
                attacker_id=attacker.id,
                target_id=target.id,
                distance=distance,
                difficulty=difficulty,
                dice_used=dice_count,
                roll=roll,
                successes=roll.successes,
                hit=roll.successes >= 1,
            )
        )
    return outcomes


def build_incoming_attacks(
    *,
    attacker: Character,
    weapon: Weapon,
    hit_outcomes: Sequence[HitOutcome],
) -> dict[str, list[IncomingAttack]]:
    """Group landed hits by target for ``EvasionRequest`` construction."""

    grouped: dict[str, list[IncomingAttack]] = {}
    for hit in hit_outcomes:
        if not hit.hit:
            continue
        grouped.setdefault(hit.target_id, []).append(
            IncomingAttack(
                attacker_id=attacker.id,
                weapon_id=weapon.id,
                successes=hit.successes,
                damage_formula=weapon.damage.base_formula.raw,
                damage_type=weapon.damage.damage_type,
            )
        )
    return grouped


async def resolve_evasion(
    *,
    pending_id: str,
    target: Character,
    dice_used: int,
    dice_engine: DiceEngine,
    difficulty: int = DIFFICULTY_NORMAL,
) -> EvasionOutcome:
    """Roll the defender's evasion pool (§9-1).

    Evasion is an independent d6 pool: any single success cancels the attack
    bundle. Caller is responsible for clamping ``dice_used`` to the character's
    available evasion dice — passing more than ``target.evasion_dice`` raises.
    """

    if dice_used < 0:
        raise CombatResolutionError("dice_used must be >= 0")
    if dice_used > target.evasion_dice:
        raise CombatResolutionError(
            f"target {target.id} has only {target.evasion_dice} evasion dice "
            f"but {dice_used} were requested"
        )

    if dice_used == 0:
        roll = DiceResult(
            command=f"0d6>={difficulty}",
            rolls=[],
            successes=0,
            sum=0,
            success=False,
        )
    else:
        roll = await dice_engine.roll_pool(count=dice_used, threshold=difficulty)

    return EvasionOutcome(
        pending_id=pending_id,
        target_id=target.id,
        dice_used=dice_used,
        difficulty=difficulty,
        roll=roll,
        successes=roll.successes,
        succeeded=roll.successes >= 1,
    )


def _ability_value(character: Character, name: str) -> int:
    if name == "体":
        return character.tai
    if name == "霊":
        return character.rei
    if name == "巧":
        return character.kou
    raise CombatResolutionError(f"unknown ability '{name}'")


def _condition_satisfied(
    bonus: AbilityBonus,
    *,
    base_roll: DiceResult | None,
) -> bool:
    if bonus.condition == "always":
        return True
    if base_roll is None:
        return False
    if bonus.condition == "on_six":
        return any(r == 6 for r in base_roll.rolls)
    if bonus.condition == "on_double_six":
        return sum(1 for r in base_roll.rolls if r == 6) >= 2
    raise CombatResolutionError(f"unknown condition '{bonus.condition}'")


async def compute_damage(
    *,
    attacker: Character,
    target: Character,
    weapon: Weapon,
    dice_engine: DiceEngine,
) -> DamageBreakdown:
    """Compute (and apply) damage for a landed attack (§6-8).

    The ``target`` Character is *not* mutated — the caller updates HP after
    inspecting the breakdown so events can be emitted in order. ``hp_after``
    is provided for convenience.
    """

    spec = weapon.damage
    base_roll = await _roll_damage_formula(spec, dice_engine)
    base_damage = base_roll.sum if base_roll is not None else _formula_constant(spec)

    notes: list[str] = []
    ability_bonus = 0
    if spec.ability_bonus is not None and _condition_satisfied(
        spec.ability_bonus, base_roll=base_roll
    ):
        ability_value = _ability_value(attacker, spec.ability_bonus.ability)
        ability_bonus = int(round(ability_value * spec.ability_bonus.multiplier))
        notes.append(
            f"+{ability_bonus} from {spec.ability_bonus.ability} ({spec.ability_bonus.condition})"
        )

    raw_total = base_damage + ability_bonus
    armor_reduction = 0 if spec.armor_piercing else min(target.armor_value, raw_total)
    final_damage = max(0, raw_total - armor_reduction)
    hp_after = max(0, target.hp - final_damage)

    return DamageBreakdown(
        attacker_id=attacker.id,
        target_id=target.id,
        weapon_id=weapon.id,
        damage_type=spec.damage_type,
        base_roll=base_roll,
        base_damage=base_damage,
        ability_bonus=ability_bonus,
        raw_total=raw_total,
        armor_reduction=armor_reduction,
        final_damage=final_damage,
        hp_before=target.hp,
        hp_after=hp_after,
        notes=notes,
    )


def apply_damage(target: Character, breakdown: DamageBreakdown) -> Character:
    """Return a new ``Character`` with HP reduced (Pydantic models are immutable enough)."""

    if breakdown.target_id != target.id:
        raise CombatResolutionError(
            f"breakdown target {breakdown.target_id} != character {target.id}"
        )
    return target.model_copy(update={"hp": breakdown.hp_after})


async def _roll_damage_formula(spec: DamageSpec, dice_engine: DiceEngine) -> DiceResult | None:
    count, sides, modifier = spec.base_formula.parse()
    if count == 0:
        return None
    return await dice_engine.roll_sum(count=count, sides=sides, modifier=modifier)


def _formula_constant(spec: DamageSpec) -> int:
    count, _sides, modifier = spec.base_formula.parse()
    if count != 0:
        # Should not happen — formula contains dice.
        return 0
    return modifier
