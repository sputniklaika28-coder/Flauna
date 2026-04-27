from __future__ import annotations

import pytest

from tacex_gm.models.constants import (
    DIFFICULTY_MAX,
    DIFFICULTY_MIN,
    DIFFICULTY_TABLE,
    AdditionalStyle,
    MeleeStyle,
    RangeClass,
    RangedStyle,
    clamp_difficulty,
    lookup_range_difficulty,
)


class TestDifficulty:
    def test_table_values(self) -> None:
        assert DIFFICULTY_TABLE == {
            "KIDS": 2,
            "EASY": 3,
            "NORMAL": 4,
            "HARD": 5,
            "ULTRA_HARD": 6,
        }

    @pytest.mark.parametrize(
        "value, expected",
        [
            (-5, DIFFICULTY_MIN),
            (DIFFICULTY_MIN, DIFFICULTY_MIN),
            (4, 4),
            (DIFFICULTY_MAX, DIFFICULTY_MAX),
            (99, DIFFICULTY_MAX),
        ],
    )
    def test_clamp(self, value: int, expected: int) -> None:
        assert clamp_difficulty(value) == expected


class TestRangeDifficulty:
    @pytest.mark.parametrize(
        "rc, distance, expected",
        [
            (RangeClass.SMALL_RANGED, 0, "NORMAL"),
            (RangeClass.SMALL_RANGED, 4, "HARD"),
            (RangeClass.SMALL_RANGED, 11, "ULTRA_HARD"),
            (RangeClass.SMALL_RANGED, 12, None),
            (RangeClass.MEDIUM_RANGED, 5, "NORMAL"),
            (RangeClass.LARGE_RANGED, 8, "HARD"),
            (RangeClass.LARGE_RANGED, 10, "NORMAL"),
            (RangeClass.PEG_RANGED, 5, "NORMAL"),
            (RangeClass.PEG_RANGED, 6, "HARD"),
            (RangeClass.PEG_RANGED, 11, "ULTRA_HARD"),
        ],
    )
    def test_lookup(self, rc: RangeClass, distance: int, expected: str | None) -> None:
        assert lookup_range_difficulty(rc, distance) == expected


class TestStyleEnums:
    def test_melee_style_values(self) -> None:
        assert MeleeStyle.RENGEKI.value == "連撃"
        assert MeleeStyle.NONE.value == "none"

    def test_ranged_style_values(self) -> None:
        assert RangedStyle.SOGEKI.value == "狙撃"

    def test_additional_style_values(self) -> None:
        assert AdditionalStyle.RYOUTEKIKI.value == "両手利き"
