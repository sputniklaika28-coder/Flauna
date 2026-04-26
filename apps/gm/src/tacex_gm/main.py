from __future__ import annotations

import logging

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from tacex_gm.api.rooms import router as rooms_router
from tacex_gm.config import settings
from tacex_gm.ws.handler import handle_room_websocket

logging.basicConfig(level=settings.log_level.upper())

app = FastAPI(title="TacEx-GM", version="0.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rooms_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> dict[str, str]:
    # Phase 0 stub: Prometheus format metrics in Phase 1+
    return {"status": "stub"}


@app.websocket("/room/{room_id}")
async def websocket_room(websocket: WebSocket, room_id: str) -> None:
    await handle_room_websocket(websocket, room_id)
