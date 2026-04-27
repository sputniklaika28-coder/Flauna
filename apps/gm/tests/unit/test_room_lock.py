from __future__ import annotations

import asyncio

import pytest

from tacex_gm.room.lock import RoomLock, RoomLockRegistry, StateLockTimeout


class TestRoomLock:
    @pytest.mark.asyncio
    async def test_acquire_and_release(self) -> None:
        lock = RoomLock("room-x", default_timeout=1.0)
        async with lock.acquire():
            assert lock.locked
        assert not lock.locked

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        lock = RoomLock("room-x", default_timeout=0.05)

        async def hold() -> None:
            async with lock.acquire():
                await asyncio.sleep(0.5)

        holder = asyncio.create_task(hold())
        await asyncio.sleep(0.01)
        with pytest.raises(StateLockTimeout):
            async with lock.acquire(timeout=0.05):
                pass
        await holder

    @pytest.mark.asyncio
    async def test_serial_access(self) -> None:
        lock = RoomLock("room-x", default_timeout=1.0)
        order: list[str] = []

        async def worker(name: str) -> None:
            async with lock.acquire():
                order.append(f"+{name}")
                await asyncio.sleep(0.01)
                order.append(f"-{name}")

        await asyncio.gather(worker("a"), worker("b"))
        # Whichever ran first must complete fully before the next starts.
        if order[0] == "+a":
            assert order == ["+a", "-a", "+b", "-b"]
        else:
            assert order == ["+b", "-b", "+a", "-a"]


class TestRegistry:
    @pytest.mark.asyncio
    async def test_returns_same_lock_per_room(self) -> None:
        reg = RoomLockRegistry()
        a1 = await reg.get("room-1")
        a2 = await reg.get("room-1")
        b = await reg.get("room-2")
        assert a1 is a2
        assert a1 is not b
