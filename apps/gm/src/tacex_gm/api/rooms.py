from __future__ import annotations

import nanoid  # type: ignore[import-untyped]
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from tacex_gm.auth import issue_master_token, issue_player_token

router = APIRouter(prefix="/api/v1", tags=["rooms"])


class CreateRoomRequest(BaseModel):
    scenario_id: str
    player_name: str


class CreateRoomResponse(BaseModel):
    room_id: str
    master_token: str
    scenario_title: str


class JoinRoomRequest(BaseModel):
    player_name: str


class RoomInfo(BaseModel):
    room_id: str
    title: str


class JoinRoomResponse(BaseModel):
    player_id: str
    player_token: str
    room_info: RoomInfo


# Phase 0: in-memory room registry
_rooms: dict[str, dict[str, str]] = {}

SCENARIO_TITLES: dict[str, str] = {
    "first_mission": "最初の任務",
}


@router.post("/rooms", response_model=CreateRoomResponse, status_code=status.HTTP_200_OK)
async def create_room(req: CreateRoomRequest) -> CreateRoomResponse:
    room_id = f"room-{nanoid.generate(size=8)}"
    scenario_title = SCENARIO_TITLES.get(req.scenario_id, req.scenario_id)
    master_token = issue_master_token(room_id)
    _rooms[room_id] = {
        "scenario_id": req.scenario_id,
        "scenario_title": scenario_title,
        "gm_name": req.player_name,
    }
    return CreateRoomResponse(
        room_id=room_id,
        master_token=master_token,
        scenario_title=scenario_title,
    )


@router.post(
    "/rooms/{room_id}/join",
    response_model=JoinRoomResponse,
    status_code=status.HTTP_200_OK,
)
async def join_room(room_id: str, req: JoinRoomRequest) -> JoinRoomResponse:
    room = _rooms.get(room_id)
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {"code": "ROOM_NOT_FOUND", "message": "指定されたルームが見つかりません"}
            },
        )
    player_id = f"player-{nanoid.generate(size=8)}"
    player_token = issue_player_token(room_id, player_id)
    return JoinRoomResponse(
        player_id=player_id,
        player_token=player_token,
        room_info=RoomInfo(room_id=room_id, title=room["scenario_title"]),
    )
