from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class JoinRoomMessage(BaseModel):
    action: Literal["join_room"]
    player_id: str
    room_id: str
    auth_token: str
    last_seen_event_id: int = 0


class ClientMessage(BaseModel):
    action: str
    player_id: str
    room_id: str
    client_request_id: str | None = None
