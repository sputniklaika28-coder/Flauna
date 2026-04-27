from __future__ import annotations

import pytest

from tacex_gm.engine.geometry import (
    PathValidationError,
    calc_distance,
    has_line_of_sight,
    in_bounds,
    validate_movement_path,
)


class TestDistance:
    @pytest.mark.parametrize(
        "p1, p2, expected",
        [
            ((0, 0), (0, 0), 0),
            ((0, 0), (3, 0), 3),
            ((0, 0), (0, 4), 4),
            ((0, 0), (3, 4), 4),
            ((1, 1), (-2, 5), 4),
        ],
    )
    def test_chebyshev(self, p1: tuple[int, int], p2: tuple[int, int], expected: int) -> None:
        assert calc_distance(p1, p2) == expected


class TestBounds:
    def test_in_bounds(self) -> None:
        assert in_bounds((0, 0), (5, 5))
        assert in_bounds((4, 4), (5, 5))

    def test_out_of_bounds(self) -> None:
        assert not in_bounds((5, 5), (5, 5))
        assert not in_bounds((-1, 0), (5, 5))


class TestLineOfSight:
    def test_clear_line(self) -> None:
        assert has_line_of_sight((0, 0), (5, 0), obstacles=[])

    def test_blocked_in_middle(self) -> None:
        assert not has_line_of_sight((0, 0), (4, 0), obstacles=[(2, 0)])

    def test_endpoint_blocked(self) -> None:
        assert not has_line_of_sight((0, 0), (3, 0), obstacles=[(3, 0)])

    def test_diagonal_corner_one_side_passes(self) -> None:
        # Only one of the two corners is blocked → still LoS (player-friendly).
        assert has_line_of_sight((0, 0), (2, 2), obstacles=[(1, 0)])

    def test_diagonal_corner_both_sides_blocks(self) -> None:
        assert not has_line_of_sight((0, 0), (2, 2), obstacles=[(1, 0), (0, 1)])


class TestPathValidation:
    def test_simple_two_step(self) -> None:
        validate_movement_path(
            [(1, 0), (2, 0)],
            start=(0, 0),
            max_distance=3,
            map_size=(10, 10),
            obstacles=[],
        )

    def test_diagonal_step_allowed(self) -> None:
        validate_movement_path(
            [(1, 1)],
            start=(0, 0),
            max_distance=2,
            map_size=(5, 5),
            obstacles=[],
        )

    def test_non_adjacent_step_fails(self) -> None:
        with pytest.raises(PathValidationError):
            validate_movement_path(
                [(2, 0)],
                start=(0, 0),
                max_distance=3,
                map_size=(5, 5),
                obstacles=[],
            )

    def test_obstacle_blocks(self) -> None:
        with pytest.raises(PathValidationError):
            validate_movement_path(
                [(1, 0), (2, 0)],
                start=(0, 0),
                max_distance=3,
                map_size=(5, 5),
                obstacles=[(2, 0)],
            )

    def test_max_distance_enforced(self) -> None:
        with pytest.raises(PathValidationError):
            validate_movement_path(
                [(1, 0), (2, 0), (3, 0)],
                start=(0, 0),
                max_distance=2,
                map_size=(5, 5),
                obstacles=[],
            )

    def test_destination_occupied_fails(self) -> None:
        with pytest.raises(PathValidationError):
            validate_movement_path(
                [(1, 0)],
                start=(0, 0),
                max_distance=2,
                map_size=(5, 5),
                obstacles=[],
                occupied=[(1, 0)],
            )

    def test_out_of_bounds_fails(self) -> None:
        with pytest.raises(PathValidationError):
            validate_movement_path(
                [(5, 0)],
                start=(4, 0),
                max_distance=2,
                map_size=(5, 5),
                obstacles=[],
            )

    def test_empty_path_fails(self) -> None:
        with pytest.raises(PathValidationError):
            validate_movement_path(
                [],
                start=(0, 0),
                max_distance=2,
                map_size=(5, 5),
                obstacles=[],
            )
