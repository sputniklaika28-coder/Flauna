"""Core rule-engine primitives (Phase 1)."""

from .dice import DiceEngine, DiceResult, PythonDiceEngine
from .geometry import (
    PathValidationError,
    calc_distance,
    has_line_of_sight,
    in_bounds,
    validate_movement_path,
)

__all__ = [
    "DiceEngine",
    "DiceResult",
    "PathValidationError",
    "PythonDiceEngine",
    "calc_distance",
    "has_line_of_sight",
    "in_bounds",
    "validate_movement_path",
]
