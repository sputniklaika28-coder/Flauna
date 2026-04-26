"""WebSocket endpoint handler."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect

from tacex_gm import auth, room as room_mod
from tacex_gm.errors import CloseCode, ErrorCode
from tacex_gm.ws.messages import ErrorMessage, JoinRoomMessage, SessionRestoreMessage


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


async def handle_websocket(websocket: WebSocket, room_id: str) -> None:
    await websocket.accept()

    player_id: str | None = None

    try:
        # Expect join_room as first message
        raw = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
        msg = JoinRoomMessage.model_validate(raw)

        # Verify token
        record = auth.verify_token(msg.auth_token)
        if record is None or record.room_id != room_id:
            await websocket.send_json(
                ErrorMessage(
                    event_id=0,
                    timestamp=_now_iso(),
                    code=ErrorCode.INVALID_TOKEN,
                    message="Invalid or expired token",
                ).model_dump()
            )
            await websocket.close(code=CloseCode.INVALID_TOKEN)
            return

        if record.player_id != msg.player_id:
            await websocket.send_json(
                ErrorMessage(
                    event_id=0,
                    timestamp=_now_iso(),
                    code=ErrorCode.INVALID_TOKEN,
                    message="player_id mismatch",
                ).model_dump()
            )
            await websocket.close(code=CloseCode.INVALID_TOKEN)
            return

        room = room_mod.get_room(room_id)
        if room is None:
            await websocket.close(code=CloseCode.ROOM_NOT_FOUND)
            return

        player_id = record.player_id
        room.connections[player_id] = websocket

        # Send session_restore
        restore = SessionRestoreMessage(
            event_id=room.next_event_id,
            timestamp=_now_iso(),
            mode="incremental",
            current_state={},
            missed_events=[
                e for e in room.event_log if e["event_id"] > msg.last_seen_event_id
            ],
            missed_event_count=max(
                0, room.next_event_id - 1 - msg.last_seen_event_id
            ),
        )
        await websocket.send_json(restore.model_dump())

        # Main receive loop
        while True:
            data = await websocket.receive_json()
            # Dispatch to action handlers (Phase 1+)
            action = data.get("action", "")
            if action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        await websocket.close(code=CloseCode.INVALID_TOKEN)
    finally:
        if player_id:
            room_ = room_mod.get_room(room_id)
            if room_:
                room_.connections.pop(player_id, None)
