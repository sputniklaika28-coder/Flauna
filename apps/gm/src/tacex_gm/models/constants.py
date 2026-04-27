"""Game-wide constants defined by the GM spec v2.5 (§6-6, §6-7, §9-6)."""

from __future__ import annotations

from enum import StrEnum
from typing import Final

# §6-6 Difficulty values used as the success threshold for d6 pool rolls.
DIFFICULTY_KIDS: Final[int] = 2
DIFFICULTY_EASY: Final[int] = 3
DIFFICULTY_NORMAL: Final[int] = 4
DIFFICULTY_HARD: Final[int] = 5
DIFFICULTY_ULTRA_HARD: Final[int] = 6

DIFFICULTY_TABLE: Final[dict[str, int]] = {
    "KIDS": DIFFICULTY_KIDS,
    "EASY": DIFFICULTY_EASY,
    "NORMAL": DIFFICULTY_NORMAL,
    "HARD": DIFFICULTY_HARD,
    "ULTRA_HARD": DIFFICULTY_ULTRA_HARD,
}

DIFFICULTY_MIN: Final[int] = DIFFICULTY_KIDS
DIFFICULTY_MAX: Final[int] = DIFFICULTY_ULTRA_HARD


def clamp_difficulty(value: int) -> int:
    """Clamp a raw difficulty value into the KIDS..ULTRA_HARD band."""

    return max(DIFFICULTY_MIN, min(DIFFICULTY_MAX, value))


# §6-7 Attack styles. Keep the Japanese strings as-is; they double as protocol values.
class MeleeStyle(StrEnum):
    NONE = "none"
    RENGEKI = "連撃"
    SEIMITSU = "精密攻撃"
    KYOUKOUGEKI = "強攻撃"
    ZENRYOKU = "全力攻撃"


class RangedStyle(StrEnum):
    NONE = "none"
    NIKAI_SHAGEKI = "2回射撃"
    RENSHA = "連射"
    RENSHA_II = "連射II"
    SOGEKI = "狙撃"
    NUKIUCHI = "抜き撃ち"


class AdditionalStyle(StrEnum):
    RYOUTEKIKI = "両手利き"


# §9-6 Range-based difficulty per weapon class. Keys must match `Weapon.range_class`.
class RangeClass(StrEnum):
    SMALL_RANGED = "small_ranged"
    MEDIUM_RANGED = "medium_ranged"
    LARGE_RANGED = "large_ranged"
    PEG_RANGED = "peg_ranged"


# (range_class, distance) -> difficulty label. None for out-of-range.
RANGE_DIFFICULTY_TABLE: Final[dict[RangeClass, list[tuple[int, int, str | None]]]] = {
    RangeClass.SMALL_RANGED: [
        (0, 3, "NORMAL"),
        (4, 8, "HARD"),
        (9, 11, "ULTRA_HARD"),
    ],
    RangeClass.MEDIUM_RANGED: [
        (0, 3, "HARD"),
        (4, 8, "NORMAL"),
        (9, 11, "HARD"),
    ],
    RangeClass.LARGE_RANGED: [
        (0, 8, "HARD"),
        (9, 11, "NORMAL"),
    ],
    RangeClass.PEG_RANGED: [
        (0, 5, "NORMAL"),
        (6, 8, "HARD"),
        (9, 11, "ULTRA_HARD"),
    ],
}


def lookup_range_difficulty(range_class: RangeClass, distance: int) -> str | None:
    """Return the difficulty label or ``None`` if the distance is out of range."""

    bands = RANGE_DIFFICULTY_TABLE.get(range_class)
    if bands is None:
        return None
    for low, high, label in bands:
        if low <= distance <= high:
            return label
    return None


# §6-4 Memory budgets (interim values, real measurements happen in Phase 0/1).
EVENT_LOG_MAX_SIZE: Final[int] = 10_000
EVENT_LOG_TARGET_SIZE_AFTER_TRIM: Final[int] = 8_000
