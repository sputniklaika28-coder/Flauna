from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient

from tacex_gm.main import app
from tacex_gm.ws.handler import _event_counter


@pytest.fixture(autouse=True)
def clear_event_counter():
    _event_counter.clear()
    yield
    _event_counter.clear()


def _join_payload(room_id: str = "room-test") -> str:
    return json.dumps(
        {
            "action": "join_room",
            "player_id": "player-1",
            "room_id": room_id,
            "auth_token": "tok",
            "last_seen_event_id": 0,
        }
    )


class TestWebSocketHandler:
    def test_join_room_receives_session_restore(self):
        with TestClient(app) as client, client.websocket_connect("/room/room-test") as ws:
            ws.send_text(_join_payload())
            data = ws.receive_json()
        assert data["type"] == "session_restore"
        assert data["mode"] == "incremental"
        assert "event_id" in data
        assert "current_state" in data

    def test_join_room_echo_after_restore(self):
        with TestClient(app) as client, client.websocket_connect("/room/room-test") as ws:
            ws.send_text(_join_payload())
            ws.receive_json()  # session_restore
            ws.send_text(json.dumps({"hello": "world"}))
            echoed = ws.receive_json()
        assert echoed == {"hello": "world"}

    def test_invalid_json_returns_error_and_closes(self):
        with TestClient(app) as client, client.websocket_connect("/room/room-bad") as ws:
            ws.send_text("not json at all")
            data = ws.receive_json()
        assert data["type"] == "error"
        assert data["code"] == "INVALID_MESSAGE"

    def test_non_join_first_message_returns_error(self):
        with TestClient(app) as client, client.websocket_connect("/room/room-bad") as ws:
            ws.send_text(
                json.dumps(
                    {
                        "action": "player_statement",
                        "player_id": "p1",
                        "room_id": "room-bad",
                        "client_request_id": "req",
                        "text": "hi",
                    }
                )
            )
            data = ws.receive_json()
        assert data["type"] == "error"
        assert data["code"] == "INVALID_MESSAGE"
        assert "join_room" in data["message"]

    def test_event_ids_increment_within_room(self):
        with TestClient(app) as client, client.websocket_connect("/room/room-incr") as ws:
            ws.send_text(_join_payload("room-incr"))
            restore = ws.receive_json()
        first_id = restore["event_id"]
        assert first_id >= 1

        with TestClient(app) as client, client.websocket_connect("/room/room-incr") as ws:
            ws.send_text(_join_payload("room-incr"))
            restore2 = ws.receive_json()
        assert restore2["event_id"] > first_id
