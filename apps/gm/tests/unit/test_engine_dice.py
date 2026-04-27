from __future__ import annotations

import pytest

from tacex_gm.engine.dice import PythonDiceEngine


class TestPythonDiceEngine:
    @pytest.mark.asyncio
    async def test_seed_is_deterministic(self) -> None:
        a = PythonDiceEngine(seed=42)
        b = PythonDiceEngine(seed=42)
        result_a = await a.roll_pool(count=4, threshold=4)
        result_b = await b.roll_pool(count=4, threshold=4)
        assert result_a == result_b

    @pytest.mark.asyncio
    async def test_pool_threshold_filters(self) -> None:
        engine = PythonDiceEngine(seed=42)
        result = await engine.roll_pool(count=4, threshold=4)
        assert len(result.rolls) == 4
        assert all(1 <= r <= 6 for r in result.rolls)
        assert result.successes == sum(1 for r in result.rolls if r >= 4)
        assert result.command == "4d6>=4"
        assert result.success == (result.successes >= 1)

    @pytest.mark.asyncio
    async def test_pool_threshold_invalid(self) -> None:
        engine = PythonDiceEngine(seed=1)
        with pytest.raises(ValueError):
            await engine.roll_pool(count=2, threshold=0)
        with pytest.raises(ValueError):
            await engine.roll_pool(count=-1, threshold=4)

    @pytest.mark.asyncio
    async def test_sum_modifier(self) -> None:
        engine = PythonDiceEngine(seed=42)
        result = await engine.roll_sum(count=2, sides=6, modifier=3)
        assert result.sum == sum(result.rolls) + 3
        assert result.command.endswith("+3")

    @pytest.mark.asyncio
    async def test_sum_negative_modifier(self) -> None:
        engine = PythonDiceEngine(seed=42)
        result = await engine.roll_sum(count=1, sides=6, modifier=-1)
        assert result.command.endswith("-1")

    @pytest.mark.asyncio
    async def test_zero_count_pool(self) -> None:
        engine = PythonDiceEngine(seed=1)
        result = await engine.roll_pool(count=0, threshold=4)
        assert result.rolls == []
        assert result.successes == 0
        assert not result.success

    @pytest.mark.asyncio
    async def test_independent_streams(self) -> None:
        a = PythonDiceEngine(seed=1)
        b = PythonDiceEngine(seed=2)
        ra = await a.roll_pool(count=10, threshold=4)
        rb = await b.roll_pool(count=10, threshold=4)
        # Statistically near-impossible to coincide.
        assert ra.rolls != rb.rolls
