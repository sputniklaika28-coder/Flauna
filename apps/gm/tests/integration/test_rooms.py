from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tacex_gm.api.rooms import _rooms
from tacex_gm.auth import _tokens
from tacex_gm.main import app


@pytest.fixture(autouse=True)
def clear_state():
    _rooms.clear()
    _tokens.clear()
    yield
    _rooms.clear()
    _tokens.clear()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# POST /api/v1/rooms
# ---------------------------------------------------------------------------


async def test_create_room_known_scenario(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/rooms",
        json={"scenario_id": "first_mission", "player_name": "GM田中"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["scenario_title"] == "最初の任務"
    assert data["room_id"].startswith("room-")
    assert len(data["master_token"]) > 10


async def test_create_room_unknown_scenario_uses_id_as_title(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/rooms",
        json={"scenario_id": "custom_scenario", "player_name": "GM"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["scenario_title"] == "custom_scenario"


async def test_create_room_stores_in_registry(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/rooms",
        json={"scenario_id": "first_mission", "player_name": "GM"},
    )
    room_id = resp.json()["room_id"]
    assert room_id in _rooms
    assert _rooms[room_id]["scenario_id"] == "first_mission"
    assert _rooms[room_id]["gm_name"] == "GM"


async def test_create_room_master_token_is_valid(client: AsyncClient) -> None:
    from tacex_gm.auth import verify_token

    resp = await client.post(
        "/api/v1/rooms",
        json={"scenario_id": "first_mission", "player_name": "GM"},
    )
    data = resp.json()
    payload = verify_token(data["master_token"])
    assert payload is not None
    assert payload["role"] == "master"
    assert payload["room_id"] == data["room_id"]


async def test_create_room_ids_are_unique(client: AsyncClient) -> None:
    room_ids = set()
    for _ in range(5):
        resp = await client.post(
            "/api/v1/rooms",
            json={"scenario_id": "first_mission", "player_name": "GM"},
        )
        room_ids.add(resp.json()["room_id"])
    assert len(room_ids) == 5


async def test_create_room_requires_scenario_id(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/rooms", json={"player_name": "GM"})
    assert resp.status_code == 422


async def test_create_room_requires_player_name(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/rooms", json={"scenario_id": "first_mission"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/rooms/{room_id}/join
# ---------------------------------------------------------------------------


async def _create_room(client: AsyncClient, player_name: str = "GM") -> dict:
    resp = await client.post(
        "/api/v1/rooms",
        json={"scenario_id": "first_mission", "player_name": player_name},
    )
    return resp.json()


async def test_join_room_success(client: AsyncClient) -> None:
    room = await _create_room(client)
    resp = await client.post(
        f"/api/v1/rooms/{room['room_id']}/join",
        json={"player_name": "Player1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["player_id"].startswith("player-")
    assert len(data["player_token"]) > 10
    assert data["room_info"]["room_id"] == room["room_id"]
    assert data["room_info"]["title"] == "最初の任務"


async def test_join_room_player_token_is_valid(client: AsyncClient) -> None:
    from tacex_gm.auth import verify_token

    room = await _create_room(client)
    resp = await client.post(
        f"/api/v1/rooms/{room['room_id']}/join",
        json={"player_name": "Player1"},
    )
    data = resp.json()
    payload = verify_token(data["player_token"])
    assert payload is not None
    assert payload["role"] == "player"
    assert payload["room_id"] == room["room_id"]
    assert payload["player_id"] == data["player_id"]


async def test_join_room_not_found(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/rooms/room-nonexistent/join",
        json={"player_name": "Player1"},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["error"]["code"] == "ROOM_NOT_FOUND"


async def test_join_room_multiple_players_get_unique_ids(client: AsyncClient) -> None:
    room = await _create_room(client)
    player_ids = set()
    for i in range(3):
        resp = await client.post(
            f"/api/v1/rooms/{room['room_id']}/join",
            json={"player_name": f"Player{i}"},
        )
        player_ids.add(resp.json()["player_id"])
    assert len(player_ids) == 3


async def test_join_room_requires_player_name(client: AsyncClient) -> None:
    room = await _create_room(client)
    resp = await client.post(f"/api/v1/rooms/{room['room_id']}/join", json={})
    assert resp.status_code == 422
