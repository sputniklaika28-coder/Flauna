"""FastAPI application entry point."""
from __future__ import annotations

import secrets
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from tacex_gm import auth
from tacex_gm.errors import ErrorCode
from tacex_gm.room import manager as room_mgr
from tacex_gm.ws.handler import handle_websocket

app = FastAPI(title="TacEx GM Server", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ── Room API ──────────────────────────────────────────────────────────────────


class CreateRoomRequest(BaseModel):
    scenario_id: str
    player_name: str


class CreateRoomResponse(BaseModel):
    room_id: str
    master_token: str
    scenario_title: str


@app.post("/api/v1/rooms", response_model=CreateRoomResponse)
async def create_room(body: CreateRoomRequest) -> CreateRoomResponse:
    master_player_id = f"player-{secrets.token_urlsafe(6)}"
    room = room_mgr.create_room(
        scenario_id=body.scenario_id,
        master_player_id=master_player_id,
    )
    token = auth.issue_token(master_player_id, room.room_id, is_master=True)
    return CreateRoomResponse(
        room_id=room.room_id,
        master_token=token,
        scenario_title=room.scenario_title,
    )


class JoinRoomRequest(BaseModel):
    player_name: str


class JoinRoomResponse(BaseModel):
    player_id: str
    player_token: str
    room_info: dict[str, Any]


@app.post("/api/v1/rooms/{room_id}/join", response_model=JoinRoomResponse)
async def join_room(room_id: str, body: JoinRoomRequest) -> JoinRoomResponse:
    room = room_mgr.get_room(room_id)
    if room is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": ErrorCode.ROOM_NOT_FOUND, "message": "Room not found"}},
        )
    player_id = f"player-{secrets.token_urlsafe(6)}"
    token = auth.issue_token(player_id, room_id)
    return JoinRoomResponse(
        player_id=player_id,
        player_token=token,
        room_info={"room_id": room.room_id, "title": room.scenario_title},
    )


# ── WebSocket ─────────────────────────────────────────────────────────────────


@app.websocket("/room/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str) -> None:
    await handle_websocket(websocket, room_id)
