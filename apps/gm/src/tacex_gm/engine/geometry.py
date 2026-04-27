"""Distance, line-of-sight, and movement-path helpers (GM spec §9-3..§9-5)."""

from __future__ import annotations

from collections.abc import Iterable

Coordinate = tuple[int, int]


def calc_distance(p1: Coordinate, p2: Coordinate) -> int:
    """Chebyshev distance (8-directional movement, §9-3)."""

    return max(abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))


def in_bounds(point: Coordinate, map_size: tuple[int, int]) -> bool:
    width, height = map_size
    x, y = point
    return 0 <= x < width and 0 <= y < height


def _bresenham(start: Coordinate, end: Coordinate) -> list[Coordinate]:
    """Bresenham line — endpoints inclusive."""

    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    points: list[Coordinate] = []
    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy
    return points


def has_line_of_sight(
    start: Coordinate,
    end: Coordinate,
    obstacles: Iterable[Coordinate],
) -> bool:
    """§9-4: Bresenham, two-sided block check (player-friendly diagonals).

    A diagonal step is blocked only if **both** orthogonal neighbours adjacent
    to that step are obstacles. The endpoint and start point themselves are
    never treated as blockers.
    """

    obstacle_set = set(obstacles)
    points = _bresenham(start, end)
    for index in range(1, len(points) - 1):
        prev = points[index - 1]
        cur = points[index]
        if cur in obstacle_set:
            return False
        # Diagonal corner check
        if abs(cur[0] - prev[0]) == 1 and abs(cur[1] - prev[1]) == 1:
            corner_a = (prev[0], cur[1])
            corner_b = (cur[0], prev[1])
            if corner_a in obstacle_set and corner_b in obstacle_set:
                return False
    return end not in obstacle_set


class PathValidationError(ValueError):
    """Raised when a movement path violates the §9-5 invariants."""


def validate_movement_path(
    path: list[Coordinate],
    *,
    start: Coordinate,
    max_distance: int,
    map_size: tuple[int, int],
    obstacles: Iterable[Coordinate],
    occupied: Iterable[Coordinate] = (),
) -> None:
    """Validate that ``path`` is reachable in one move (§9-5).

    The ``path`` is the sequence of grid cells traversed *after* the start cell
    (i.e. it does not include ``start``). Each step must be 8-adjacent, every
    cell must be in bounds, and only the final cell may be occupied if it is
    the same as ``start`` (which never happens because path is non-empty).
    """

    if not path:
        raise PathValidationError("path must contain at least one step")
    if len(path) > max_distance:
        raise PathValidationError(f"path length {len(path)} exceeds max_distance {max_distance}")

    obstacle_set = set(obstacles)
    occupied_set = set(occupied)
    previous = start
    for index, cell in enumerate(path):
        if not in_bounds(cell, map_size):
            raise PathValidationError(f"cell {cell} is out of bounds")
        step = calc_distance(previous, cell)
        if step != 1:
            raise PathValidationError(
                f"non-adjacent step {previous} → {cell} (chebyshev distance {step})"
            )
        if cell in obstacle_set:
            raise PathValidationError(f"cell {cell} is an obstacle")
        # Only the destination may be the actor's own position (no-op move) or empty.
        is_destination = index == len(path) - 1
        if cell in occupied_set:
            raise PathValidationError(f"cell {cell} is occupied")
        if not is_destination and cell == start:
            raise PathValidationError(f"path returns to start cell at step {index}")
        previous = cell
