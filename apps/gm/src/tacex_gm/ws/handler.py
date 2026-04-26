from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from ..auth import decode_token
from ..errors import ErrorCode
from ..room.manager import room_manager
from .messages import JoinRoomMessage


async def handle_websocket(websocket: WebSocket, room_id: str) -> None:
    await websocket.accept()

    try:
        raw = await websocket.receive_text()
        data = json.loads(raw)

        if data.get("action") != "join_room":
            await _send_error(websocket, ErrorCode.AUTH_INVALID_TOKEN, "First message must be join_room")
            await websocket.close(code=4000)
            return

        try:
            msg = JoinRoomMessage.model_validate(data)
        except ValidationError as exc:
            await _send_error(websocket, ErrorCode.AUTH_INVALID_TOKEN, str(exc))
            await websocket.close(code=4000)
            return

        try:
            claims = decode_token(msg.auth_token)
        except ValueError:
            await _send_error(websocket, ErrorCode.AUTH_INVALID_TOKEN, "Invalid token")
            await websocket.close(code=4000)
            return

        if claims.get("room_id") != room_id:
            await _send_error(websocket, ErrorCode.AUTH_PERMISSION_DENIED, "Token room mismatch")
            await websocket.close(code=4000)
            return

        room = room_manager.get_room(room_id)
        if room is None:
            await _send_error(websocket, ErrorCode.ROOM_NOT_FOUND, "Room not found")
            await websocket.close(code=4001)
            return

        await websocket.send_text(
            json.dumps(
                {
                    "type": "session_restore",
                    "event_id": 0,
                    "timestamp": _now(),
                    "mode": "full_sync",
                    "current_state": None,
                    "missed_events": [],
                    "missed_event_count": 0,
                    "pending_for_you": [],
                    "expired_pending": [],
                }
            )
        )

        while True:
            await websocket.receive_text()
            # Phase 1+: route to action handlers

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await _send_error(websocket, ErrorCode.INTERNAL_ERROR, str(exc))
        except Exception:
            pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _send_error(
    websocket: WebSocket,
    code: ErrorCode,
    message: str,
    detail: dict[str, Any] | None = None,
    client_request_id: str | None = None,
) -> None:
    await websocket.send_text(
        json.dumps(
            {
                "type": "error",
                "event_id": 0,
                "timestamp": _now(),
                "code": code,
                "message": message,
                "detail": detail or {},
                "client_request_id": client_request_id,
            }
        )
    )
