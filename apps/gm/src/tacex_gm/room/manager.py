from __future__ import annotations

from dataclasses import dataclass, field

from .lock import RoomLock


@dataclass
class Room:
    room_id: str
    scenario_id: str
    players: dict[str, str] = field(default_factory=dict)  # player_id -> name
    lock: RoomLock = field(default_factory=RoomLock)


class RoomManager:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def create_room(self, room_id: str, scenario_id: str) -> Room:
        room = Room(room_id=room_id, scenario_id=scenario_id)
        self._rooms[room_id] = room
        return room

    def get_room(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id)

    def add_player(self, room_id: str, player_id: str, player_name: str) -> None:
        room = self._rooms.get(room_id)
        if room is not None:
            room.players[player_id] = player_name


room_manager = RoomManager()
