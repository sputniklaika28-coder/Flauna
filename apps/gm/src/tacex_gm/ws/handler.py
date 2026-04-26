from __future__ import annotations

import datetime
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError

from tacex_gm.errors import CloseCode, ErrorCode
from tacex_gm.ws.messages import (
    ClientMessage,
    ErrorMessage,
    JoinRoom,
    SessionRestore,
)

logger = logging.getLogger(__name__)

_event_counter: dict[str, int] = {}
_client_message_adapter: TypeAdapter[ClientMessage] = TypeAdapter(ClientMessage)


def _next_event_id(room_id: str) -> int:
    _event_counter[room_id] = _event_counter.get(room_id, 0) + 1
    return _event_counter[room_id]


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


async def handle_room_websocket(websocket: WebSocket, room_id: str) -> None:
    await websocket.accept()
    logger.info("WS connected: room=%s", room_id)

    try:
        raw = await websocket.receive_text()
        try:
            data = json.loads(raw)
            msg = _client_message_adapter.validate_python(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            err = ErrorMessage(
                type="error",
                event_id=_next_event_id(room_id),
                timestamp=_now(),
                code=ErrorCode.INVALID_MESSAGE,
                message=str(exc),
            )
            await websocket.send_text(err.model_dump_json())
            await websocket.close(code=CloseCode.AUTH_FAILED)
            return

        if not isinstance(msg, JoinRoom):
            err = ErrorMessage(
                type="error",
                event_id=_next_event_id(room_id),
                timestamp=_now(),
                code=ErrorCode.INVALID_MESSAGE,
                message="First message must be join_room",
            )
            await websocket.send_text(err.model_dump_json())
            await websocket.close(code=CloseCode.AUTH_FAILED)
            return

        restore = SessionRestore(
            type="session_restore",
            event_id=_next_event_id(room_id),
            timestamp=_now(),
            mode="incremental",
            current_state={},
        )
        await websocket.send_text(restore.model_dump_json())

        while True:
            raw = await websocket.receive_text()
            # Phase 0: echo back as placeholder
            await websocket.send_text(raw)

    except WebSocketDisconnect:
        logger.info("WS disconnected: room=%s", room_id)
