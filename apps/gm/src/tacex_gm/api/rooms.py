from __future__ import annotations

import nanoid  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from tacex_gm.auth import issue_master_token, issue_player_token
from tacex_gm.errors import ErrorCode
from tacex_gm.room.session import RoomStore

router = APIRouter(prefix="/api/v1", tags=["rooms"])

SCENARIO_TITLES: dict[str, str] = {
    "first_mission": "最初の任務",
}


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class CreateRoomRequest(BaseModel):
    scenario_id: str
    player_name: str


class CreateRoomResponse(BaseModel):
    room_id: str
    master_token: str
    player_id: str
    player_token: str
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


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------


def get_room_store(request: Request) -> RoomStore:
    return request.app.state.room_store


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/rooms", response_model=CreateRoomResponse, status_code=status.HTTP_200_OK)
async def create_room(
    req: CreateRoomRequest,
    room_store: RoomStore = Depends(get_room_store),  # noqa: B008
) -> CreateRoomResponse:
    if req.scenario_id not in SCENARIO_TITLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": ErrorCode.SCENARIO_NOT_FOUND,
                    "message": "シナリオが見つかりません",
                }
            },
        )

    room_id = f"room-{nanoid.generate(size=8)}"
    scenario_title = SCENARIO_TITLES[req.scenario_id]

    await room_store.create_session(room_id=room_id, scenario_id=req.scenario_id)

    master_token = issue_master_token(room_id)

    # Register the creator as the sole player for Phase 2 MVP (1 PC only).
    player_id = f"player-{nanoid.generate(size=8)}"
    player_token = issue_player_token(room_id, player_id)

    session = room_store.get_session(room_id)
    assert session is not None
    session.register_player(player_id, req.player_name)

    return CreateRoomResponse(
        room_id=room_id,
        master_token=master_token,
        player_id=player_id,
        player_token=player_token,
        scenario_title=scenario_title,
    )


@router.post(
    "/rooms/{room_id}/join",
    response_model=JoinRoomResponse,
    status_code=status.HTTP_200_OK,
)
async def join_room(
    room_id: str,
    req: JoinRoomRequest,
    room_store: RoomStore = Depends(get_room_store),  # noqa: B008
) -> JoinRoomResponse:
    session = room_store.get_session(room_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": ErrorCode.ROOM_NOT_FOUND,
                    "message": "指定されたルームが見つかりません",
                }
            },
        )

    player_id = f"player-{nanoid.generate(size=8)}"
    player_token = issue_player_token(room_id, player_id)
    session.register_player(player_id, req.player_name)

    return JoinRoomResponse(
        player_id=player_id,
        player_token=player_token,
        room_info=RoomInfo(
            room_id=room_id,
            title=SCENARIO_TITLES.get(session.scenario_id, session.scenario_id),
        ),
    )
