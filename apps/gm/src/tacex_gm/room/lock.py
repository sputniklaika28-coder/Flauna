"""RoomLock — pessimistic per-room lock (GM spec §7-2)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class StateLockTimeout(TimeoutError):
    """Raised when ``RoomLock.acquire`` times out."""

    def __init__(self, room_id: str, timeout: float) -> None:
        super().__init__(f"timed out acquiring lock for room {room_id} after {timeout}s")
        self.room_id = room_id
        self.timeout = timeout


class RoomLock:
    """Per-room exclusive lock. Held across AI calls (§7-2)."""

    def __init__(self, room_id: str, default_timeout: float = 30.0) -> None:
        self.room_id = room_id
        self.default_timeout = default_timeout
        self._lock = asyncio.Lock()

    @property
    def locked(self) -> bool:
        return self._lock.locked()

    @asynccontextmanager
    async def acquire(self, timeout: float | None = None) -> AsyncIterator[None]:
        wait = self.default_timeout if timeout is None else timeout
        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=wait)
        except TimeoutError as exc:  # pragma: no cover - re-raised
            raise StateLockTimeout(self.room_id, wait) from exc
        try:
            yield
        finally:
            self._lock.release()


class RoomLockRegistry:
    """Process-local registry of per-room locks."""

    def __init__(self, default_timeout: float = 30.0) -> None:
        self._default_timeout = default_timeout
        self._locks: dict[str, RoomLock] = {}
        self._guard = asyncio.Lock()

    async def get(self, room_id: str) -> RoomLock:
        async with self._guard:
            lock = self._locks.get(room_id)
            if lock is None:
                lock = RoomLock(room_id, self._default_timeout)
                self._locks[room_id] = lock
            return lock

    def reset(self) -> None:
        self._locks.clear()
