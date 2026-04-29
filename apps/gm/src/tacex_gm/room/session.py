"""RoomStore — process-local in-memory room registry (Phase 2+).

Phase 6 addition: ``connections`` dict and ``broadcast`` / ``state_changed``
event for multi-player support.  Each player WebSocket registers itself on
connect; state-change notifications are sent to all connected clients.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from tacex_gm.ai.backend import LLMBackend
from tacex_gm.ai.narration_engine import NarrationTemplateEngine
from tacex_gm.models import GameState, Weapon
from tacex_gm.room.lock import RoomLock, RoomLockRegistry
from tacex_gm.ws.idempotency import IdempotencyCache

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class PlayerSlot:
    player_id: str
    player_name: str
    character_id: str = ""  # filled when GameState is built


@dataclass
class RoomSession:
    """All mutable state associated with one room."""

    room_id: str
    scenario_id: str
    lock: RoomLock
    idempotency: IdempotencyCache[str]
    weapon_catalog: dict[str, Weapon]
    enemy_catalog: dict[str, dict[str, Any]]
    llm_backend: LLMBackend
    narration: NarrationTemplateEngine

    # Populated lazily on first WS connection.
    state: GameState | None = None

    # player_id → PlayerSlot
    player_slots: dict[str, PlayerSlot] = field(default_factory=dict)

    # Phase 6: player_id → active WebSocket (multi-player broadcast).
    connections: dict[str, Any] = field(default_factory=dict)

    # Phase 6: player_id → asyncio.Queue for incoming WS messages.
    message_queues: dict[str, Any] = field(default_factory=dict)

    # Fires whenever session.state is replaced so waiting coroutines wake up.
    state_changed: asyncio.Event = field(default_factory=asyncio.Event)

    # Guard so only one coroutine initialises the state.
    _init_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    # ---------------------------------------------------------------------------
    # Player / character management
    # ---------------------------------------------------------------------------

    def register_player(self, player_id: str, player_name: str) -> None:
        """Record a player who has called POST /rooms/{id}/join."""
        self.player_slots[player_id] = PlayerSlot(
            player_id=player_id,
            player_name=player_name,
        )

    def find_pc_character_id(self, player_id: str) -> str | None:
        slot = self.player_slots.get(player_id)
        if slot is None:
            return None
        return slot.character_id or None

    def set_character_id(self, player_id: str, character_id: str) -> None:
        slot = self.player_slots.get(player_id)
        if slot is not None:
            slot.character_id = character_id

    # ---------------------------------------------------------------------------
    # Phase 6: multi-player connection management
    # ---------------------------------------------------------------------------

    def add_connection(self, player_id: str, websocket: Any) -> None:
        """Register an active WebSocket for ``player_id``."""
        self.connections[player_id] = websocket

    def remove_connection(self, player_id: str) -> None:
        """Deregister the WebSocket for ``player_id``."""
        self.connections.pop(player_id, None)

    def notify_state_changed(self) -> None:
        """Signal all waiting coroutines that state has been updated."""
        self.state_changed.set()
        self.state_changed.clear()

    async def broadcast(self, json_text: str, exclude_player_id: str | None = None) -> None:
        """Send ``json_text`` to every connected player except ``exclude_player_id``."""
        for pid, ws in list(self.connections.items()):
            if pid == exclude_player_id:
                continue
            with contextlib.suppress(Exception):
                await ws.send_text(json_text)


class RoomStore:
    """Process-local in-memory room registry."""

    def __init__(
        self,
        lock_registry: RoomLockRegistry,
        llm_backend: LLMBackend,
        narration: NarrationTemplateEngine,
        weapon_catalog: dict[str, Weapon],
        enemy_catalog: dict[str, dict[str, Any]],
    ) -> None:
        self._lock_registry = lock_registry
        self._llm_backend = llm_backend
        self._narration = narration
        self._weapon_catalog = weapon_catalog
        self._enemy_catalog = enemy_catalog
        self._rooms: dict[str, RoomSession] = {}
        self._guard = asyncio.Lock()

    async def create_session(self, room_id: str, scenario_id: str) -> RoomSession:
        lock = await self._lock_registry.get(room_id)
        session = RoomSession(
            room_id=room_id,
            scenario_id=scenario_id,
            lock=lock,
            idempotency=IdempotencyCache(max_size=256),
            weapon_catalog=self._weapon_catalog,
            enemy_catalog=self._enemy_catalog,
            llm_backend=self._llm_backend,
            narration=self._narration,
        )
        async with self._guard:
            self._rooms[room_id] = session
        return session

    def get_session(self, room_id: str) -> RoomSession | None:
        return self._rooms.get(room_id)

    async def delete_session(self, room_id: str) -> None:
        async with self._guard:
            self._rooms.pop(room_id, None)
