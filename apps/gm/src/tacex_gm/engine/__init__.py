"""Core rule-engine primitives (Phase 1)."""

from .combat import (
    CombatResolutionError,
    DamageBreakdown,
    EvasionOutcome,
    HitOutcome,
    apply_damage,
    build_incoming_attacks,
    compute_damage,
    melee_attack_difficulty,
    ranged_attack_difficulty,
    resolve_attack,
    resolve_evasion,
)
from .dice import DiceEngine, DiceResult, PythonDiceEngine
from .geometry import (
    PathValidationError,
    calc_distance,
    has_line_of_sight,
    in_bounds,
    validate_movement_path,
)

__all__ = [
    "CombatResolutionError",
    "DamageBreakdown",
    "DiceEngine",
    "DiceResult",
    "EvasionOutcome",
    "HitOutcome",
    "PathValidationError",
    "PythonDiceEngine",
    "apply_damage",
    "build_incoming_attacks",
    "calc_distance",
    "compute_damage",
    "has_line_of_sight",
    "in_bounds",
    "melee_attack_difficulty",
    "ranged_attack_difficulty",
    "resolve_attack",
    "resolve_evasion",
    "validate_movement_path",
]
