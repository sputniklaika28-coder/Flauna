"""LRU idempotency cache for ``client_request_id`` deduplication (GM spec D24).

The cache stores the *response payload* keyed by ``(room_id, client_request_id)``
so that a retried message returns the same answer instead of re-running the
state machine. This is the WS-side complement to ``RoomLock`` — together they
guarantee at-least-once-with-replay semantics across reconnects.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Hashable
from typing import Generic, TypeVar

T = TypeVar("T")


class IdempotencyCache(Generic[T]):
    """Bounded LRU cache.

    - Capacity is per-instance; mounting one cache per room is the expected shape.
    - ``get`` is read-only; calling ``record`` is what advances the LRU position.
    - Keys must be hashable; the typical key is a UUID-like ``client_request_id``.
    """

    def __init__(self, max_size: int = 256) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be > 0")
        self._max_size = max_size
        self._items: OrderedDict[Hashable, T] = OrderedDict()

    @property
    def max_size(self) -> int:
        return self._max_size

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, key: Hashable) -> bool:
        return key in self._items

    def get(self, key: Hashable) -> T | None:
        """Return the cached payload (refreshing LRU position) or ``None``."""

        if key not in self._items:
            return None
        self._items.move_to_end(key)
        return self._items[key]

    def record(self, key: Hashable, value: T) -> None:
        """Store a new payload, evicting the least recently used entry if full.

        Re-recording an existing key updates the value and promotes it.
        """

        if key in self._items:
            self._items.move_to_end(key)
            self._items[key] = value
            return
        self._items[key] = value
        if len(self._items) > self._max_size:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()
