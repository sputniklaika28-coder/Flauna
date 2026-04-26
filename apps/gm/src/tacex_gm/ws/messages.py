"""Pydantic models for WebSocket messages (client→server and server→client)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


# ── Client → Server ──────────────────────────────────────────────────────────


class JoinRoomMessage(BaseModel):
    action: Literal["join_room"]
    player_id: str
    room_id: str
    auth_token: str
    last_seen_event_id: int = 0


class ClientMessage(BaseModel):
    """Discriminated union root for inbound WS messages."""

    action: str
    player_id: str
    room_id: str
    client_request_id: str | None = None
    payload: dict[str, Any] = {}


# ── Server → Client ──────────────────────────────────────────────────────────


class SessionRestoreMessage(BaseModel):
    type: Literal["session_restore"] = "session_restore"
    event_id: int
    timestamp: str
    mode: Literal["incremental", "full_sync"]
    current_state: dict[str, Any]
    missed_events: list[dict[str, Any]] = []
    missed_event_count: int = 0
    pending_for_you: list[dict[str, Any]] = []
    expired_pending: list[dict[str, Any]] = []


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    event_id: int
    timestamp: str
    code: str
    message: str
