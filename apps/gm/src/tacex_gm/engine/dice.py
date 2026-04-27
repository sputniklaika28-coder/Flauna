"""Dice engine (GM spec §9-2).

Both the pool roll (success counting) and the sum roll are exposed via the
``DiceEngine`` Protocol. ``PythonDiceEngine`` is the deterministic reference
implementation used in unit/integration tests.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DiceResult:
    command: str
    rolls: list[int]
    successes: int
    sum: int
    success: bool


class DiceEngine(Protocol):
    async def roll_pool(self, count: int, threshold: int) -> DiceResult: ...

    async def roll_sum(
        self, count: int, sides: int = 6, modifier: int = 0
    ) -> DiceResult: ...


class PythonDiceEngine:
    """Reference implementation. Pass ``seed`` for deterministic output."""

    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)

    async def roll_pool(self, count: int, threshold: int) -> DiceResult:
        if count < 0:
            raise ValueError("count must be >= 0")
        if not 1 <= threshold <= 6:
            raise ValueError("threshold must be in 1..6 (d6 pool)")
        rolls = [self._random.randint(1, 6) for _ in range(count)]
        successes = sum(1 for r in rolls if r >= threshold)
        return DiceResult(
            command=f"{count}d6>={threshold}",
            rolls=rolls,
            successes=successes,
            sum=sum(rolls),
            success=successes >= 1,
        )

    async def roll_sum(
        self, count: int, sides: int = 6, modifier: int = 0
    ) -> DiceResult:
        if count < 0:
            raise ValueError("count must be >= 0")
        if sides < 2:
            raise ValueError("sides must be >= 2")
        rolls = [self._random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + modifier
        sign = "+" if modifier >= 0 else "-"
        return DiceResult(
            command=f"{count}d{sides}{sign}{abs(modifier)}",
            rolls=rolls,
            successes=0,
            sum=total,
            success=True,
        )
