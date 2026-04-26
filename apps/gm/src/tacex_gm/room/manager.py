"""In-memory room registry (Phase 0)."""
import asyncio
import secrets
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Room:
    room_id: str
    scenario_id: str
    master_player_id: str
    scenario_title: str
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, compare=False, repr=False)
    # player_id -> websocket (set on WS connect)
    connections: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)
    event_log: list[dict[str, Any]] = field(default_factory=list, compare=False)
    next_event_id: int = 1
    version: int = 0


_rooms: dict[str, Room] = {}


def create_room(scenario_id: str, master_player_id: str) -> Room:
    room_id = f"room-{secrets.token_urlsafe(8)}"
    # Derive a human-readable title from scenario_id
    title = scenario_id.replace("_", " ").title()
    room = Room(
        room_id=room_id,
        scenario_id=scenario_id,
        master_player_id=master_player_id,
        scenario_title=title,
    )
    _rooms[room_id] = room
    return room


def get_room(room_id: str) -> Room | None:
    return _rooms.get(room_id)


def list_rooms() -> list[Room]:
    return list(_rooms.values())
