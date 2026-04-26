from __future__ import annotations

from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel

from .auth import create_master_token, create_player_token, generate_id
from .errors import ErrorCode
from .room.manager import room_manager
from .ws.handler import handle_websocket

app = FastAPI(title="TacEx-GM", version="0.1.0")


class CreateRoomRequest(BaseModel):
    scenario_id: str
    player_name: str


class CreateRoomResponse(BaseModel):
    room_id: str
    master_token: str
    scenario_title: str


class JoinRoomRequest(BaseModel):
    player_name: str


class JoinRoomResponse(BaseModel):
    player_id: str
    player_token: str
    room_info: dict[str, str]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> str:
    lines = [
        "# HELP ws_connections_active Active WebSocket connections",
        "# TYPE ws_connections_active gauge",
        "ws_connections_active 0",
    ]
    return "\n".join(lines) + "\n"


@app.post("/api/v1/rooms", response_model=CreateRoomResponse)
async def create_room(req: CreateRoomRequest) -> CreateRoomResponse:
    room_id = generate_id("room")
    master_token = create_master_token(room_id)
    room_manager.create_room(room_id, req.scenario_id)
    return CreateRoomResponse(
        room_id=room_id,
        master_token=master_token,
        scenario_title=req.scenario_id,
    )


@app.post("/api/v1/rooms/{room_id}/join", response_model=JoinRoomResponse)
async def join_room_http(room_id: str, req: JoinRoomRequest) -> JoinRoomResponse:
    room = room_manager.get_room(room_id)
    if room is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": ErrorCode.ROOM_NOT_FOUND, "message": "指定されたルームが見つかりません"}},
        )
    player_id = generate_id("player")
    player_token = create_player_token(room_id, player_id)
    room_manager.add_player(room_id, player_id, req.player_name)
    return JoinRoomResponse(
        player_id=player_id,
        player_token=player_token,
        room_info={"room_id": room_id, "scenario_id": room.scenario_id},
    )


@app.websocket("/room/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str) -> None:
    await handle_websocket(websocket, room_id)
