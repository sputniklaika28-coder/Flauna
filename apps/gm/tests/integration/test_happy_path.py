"""Phase 0 happy-path integration test.

End-to-end flow:
  1. POST /health → 200
  2. POST /api/v1/rooms → room created
  3. POST /api/v1/rooms/{id}/join → player token
  4. WebSocket connect → join_room → session_restore received
"""
import json

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tacex_gm.main import app


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_room(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/rooms",
        json={"scenario_id": "first_mission", "player_name": "GM"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "room_id" in data
    assert "master_token" in data
    assert data["scenario_title"] == "First Mission"


@pytest.mark.asyncio
async def test_join_nonexistent_room(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/rooms/room-does-not-exist/join",
        json={"player_name": "Alice"},
    )
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["error"]["code"] == "ROOM_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_and_join_room(client: AsyncClient) -> None:
    # Create
    create_resp = await client.post(
        "/api/v1/rooms",
        json={"scenario_id": "first_mission", "player_name": "GM"},
    )
    room_id = create_resp.json()["room_id"]

    # Join
    join_resp = await client.post(
        f"/api/v1/rooms/{room_id}/join",
        json={"player_name": "Alice"},
    )
    assert join_resp.status_code == 200
    data = join_resp.json()
    assert "player_id" in data
    assert "player_token" in data
    assert data["room_info"]["room_id"] == room_id


def test_websocket_join_room() -> None:
    """Synchronous WebSocket test via Starlette TestClient."""
    with TestClient(app) as tc:
        # Create a room first
        create_resp = tc.post(
            "/api/v1/rooms",
            json={"scenario_id": "first_mission", "player_name": "GM"},
        )
        assert create_resp.status_code == 200
        room_id = create_resp.json()["room_id"]
        master_token = create_resp.json()["master_token"]
        master_player_id = None

        # Figure out master player_id from join
        join_resp = tc.post(
            f"/api/v1/rooms/{room_id}/join",
            json={"player_name": "Alice"},
        )
        player_id = join_resp.json()["player_id"]
        player_token = join_resp.json()["player_token"]

        # WebSocket connect
        with tc.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_json(
                {
                    "action": "join_room",
                    "player_id": player_id,
                    "room_id": room_id,
                    "auth_token": player_token,
                    "last_seen_event_id": 0,
                }
            )
            msg = ws.receive_json()
            assert msg["type"] == "session_restore"
            assert msg["mode"] == "incremental"
