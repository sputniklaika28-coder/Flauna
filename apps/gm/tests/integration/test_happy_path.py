from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tacex_gm.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_metrics(client: TestClient) -> None:
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "ws_connections_active" in resp.text


def test_create_room(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/rooms",
        json={"scenario_id": "first_mission", "player_name": "Alice"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["room_id"].startswith("room-")
    assert "master_token" in data
    assert data["scenario_title"] == "first_mission"


def test_join_room_not_found(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/rooms/nonexistent-room/join",
        json={"player_name": "Bob"},
    )
    assert resp.status_code == 404


def test_join_room_http(client: TestClient) -> None:
    create_resp = client.post(
        "/api/v1/rooms",
        json={"scenario_id": "first_mission", "player_name": "Alice"},
    )
    room_id = create_resp.json()["room_id"]

    join_resp = client.post(
        f"/api/v1/rooms/{room_id}/join",
        json={"player_name": "Bob"},
    )
    assert join_resp.status_code == 200
    data = join_resp.json()
    assert data["player_id"].startswith("player-")
    assert "player_token" in data


def test_websocket_join_room(client: TestClient) -> None:
    create_resp = client.post(
        "/api/v1/rooms",
        json={"scenario_id": "first_mission", "player_name": "Alice"},
    )
    data = create_resp.json()
    room_id = data["room_id"]
    master_token = data["master_token"]

    with client.websocket_connect(f"/room/{room_id}") as ws:
        ws.send_json(
            {
                "action": "join_room",
                "player_id": "master",
                "room_id": room_id,
                "auth_token": master_token,
                "last_seen_event_id": 0,
            }
        )
        msg = ws.receive_json()
        assert msg["type"] == "session_restore"
        assert msg["mode"] == "full_sync"


def test_websocket_invalid_token(client: TestClient) -> None:
    create_resp = client.post(
        "/api/v1/rooms",
        json={"scenario_id": "first_mission", "player_name": "Alice"},
    )
    room_id = create_resp.json()["room_id"]

    with client.websocket_connect(f"/room/{room_id}") as ws:
        ws.send_json(
            {
                "action": "join_room",
                "player_id": "master",
                "room_id": room_id,
                "auth_token": "invalid-token",
                "last_seen_event_id": 0,
            }
        )
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "AUTH_INVALID_TOKEN"
