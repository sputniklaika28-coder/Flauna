"""WebSocket handler integration tests (Phase 2)."""

from __future__ import annotations

import json


def _join_payload(room_id: str, player_id: str, token: str) -> str:
    return json.dumps(
        {
            "action": "join_room",
            "player_id": player_id,
            "room_id": room_id,
            "auth_token": token,
            "last_seen_event_id": 0,
        }
    )


class TestWebSocketHandler:
    def test_invalid_json_returns_error(self, sync_client):
        """Non-JSON payload → error message, then close."""
        with sync_client.websocket_connect("/room/room-bad") as ws:
            ws.send_text("not json at all ~~~~")
            data = ws.receive_json()
        assert data["type"] == "error"
        assert data["code"] == "INVALID_MESSAGE"

    def test_non_join_first_message_returns_error(self, sync_client):
        """First WS message must be join_room."""
        with sync_client.websocket_connect("/room/room-bad") as ws:
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

    def test_invalid_token_returns_error(self, sync_client):
        """Invalid auth_token → AUTH_INVALID_TOKEN."""
        with sync_client.websocket_connect("/room/room-x") as ws:
            ws.send_text(
                json.dumps(
                    {
                        "action": "join_room",
                        "player_id": "p1",
                        "room_id": "room-x",
                        "auth_token": "bad-token",
                        "last_seen_event_id": 0,
                    }
                )
            )
            data = ws.receive_json()
        assert data["type"] == "error"
        assert data["code"] == "AUTH_INVALID_TOKEN"

    def test_valid_join_receives_session_restore(self, sync_client, room_data):
        """Happy path: valid join_room → session_restore with game state."""
        room_id = room_data["room_id"]
        player_id = room_data["player_id"]
        player_token = room_data["player_token"]

        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join_payload(room_id, player_id, player_token))
            data = ws.receive_json()

        assert data["type"] == "session_restore"
        assert data["mode"] == "full_sync"
        assert "current_state" in data
        state = data["current_state"]
        assert state["room_id"] == room_id
        assert len(state["characters"]) >= 2
        # PC should be in the roster
        factions = {c["faction"] for c in state["characters"]}
        assert "pc" in factions
        assert "enemy" in factions

    def test_token_for_wrong_room_rejected(self, sync_client, room_data):
        """Token issued for room-A must not work for room-B."""
        # room_data token is for the correct room; try a different room path
        player_token = room_data["player_token"]
        with sync_client.websocket_connect("/room/room-other") as ws:
            ws.send_text(
                json.dumps(
                    {
                        "action": "join_room",
                        "player_id": room_data["player_id"],
                        "room_id": "room-other",
                        "auth_token": player_token,
                        "last_seen_event_id": 0,
                    }
                )
            )
            data = ws.receive_json()
        assert data["type"] == "error"
        assert data["code"] in ("AUTH_INVALID_TOKEN", "ROOM_NOT_FOUND")
