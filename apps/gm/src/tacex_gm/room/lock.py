from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator


class RoomLock:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self, timeout: float = 30.0) -> AsyncIterator[None]:
        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise TimeoutError("Room lock acquire timed out") from exc
        try:
            yield
        finally:
            self._lock.release()
