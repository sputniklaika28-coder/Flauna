from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from tacex_gm.ws.messages import (
    ClientMessage,
    ErrorMessage,
    GmNarrative,
    JoinRoom,
    PlayerStatement,
    ServerMessage,
    SessionRestore,
    StateFull,
    StateUpdate,
    SubmitDeathAvoidance,
    SubmitEvasion,
    SubmitTurnAction,
)

client_adapter: TypeAdapter[ClientMessage] = TypeAdapter(ClientMessage)
server_adapter: TypeAdapter[ServerMessage] = TypeAdapter(ServerMessage)


# ---------------------------------------------------------------------------
# Client messages
# ---------------------------------------------------------------------------


class TestJoinRoom:
    def test_valid(self):
        msg = client_adapter.validate_python(
            {
                "action": "join_room",
                "player_id": "p1",
                "room_id": "room-abc",
                "auth_token": "tok",
                "last_seen_event_id": 0,
            }
        )
        assert isinstance(msg, JoinRoom)
        assert msg.action == "join_room"
        assert msg.player_id == "p1"

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            client_adapter.validate_python(
                {"action": "join_room", "player_id": "p1", "room_id": "room-abc"}
            )


class TestSubmitTurnAction:
    def test_valid(self):
        msg = client_adapter.validate_python(
            {
                "action": "submit_turn_action",
                "player_id": "p1",
                "room_id": "room-abc",
                "client_request_id": "req-1",
                "expected_version": 3,
                "turn_action": {"move": [0, 1]},
            }
        )
        assert isinstance(msg, SubmitTurnAction)
        assert msg.expected_version == 3

    def test_turn_action_accepts_arbitrary_dict(self):
        msg = client_adapter.validate_python(
            {
                "action": "submit_turn_action",
                "player_id": "p1",
                "room_id": "r",
                "client_request_id": "x",
                "expected_version": 0,
                "turn_action": {"anything": True},
            }
        )
        assert msg.turn_action == {"anything": True}  # type: ignore[union-attr]


class TestSubmitEvasion:
    def test_valid(self):
        msg = client_adapter.validate_python(
            {
                "action": "submit_evasion",
                "player_id": "p1",
                "room_id": "r",
                "client_request_id": "req",
                "pending_id": "pend-1",
                "dice_result": 5,
            }
        )
        assert isinstance(msg, SubmitEvasion)
        assert msg.dice_result == 5


class TestSubmitDeathAvoidance:
    def test_use_katashiro_true(self):
        msg = client_adapter.validate_python(
            {
                "action": "submit_death_avoidance",
                "player_id": "p1",
                "room_id": "r",
                "client_request_id": "req",
                "pending_id": "pend-1",
                "use_katashiro": True,
            }
        )
        assert isinstance(msg, SubmitDeathAvoidance)
        assert msg.use_katashiro is True

    def test_use_katashiro_false(self):
        msg = client_adapter.validate_python(
            {
                "action": "submit_death_avoidance",
                "player_id": "p1",
                "room_id": "r",
                "client_request_id": "req",
                "pending_id": "pend-2",
                "use_katashiro": False,
            }
        )
        assert msg.use_katashiro is False  # type: ignore[union-attr]


class TestPlayerStatement:
    def test_valid(self):
        msg = client_adapter.validate_python(
            {
                "action": "player_statement",
                "player_id": "p1",
                "room_id": "r",
                "client_request_id": "req",
                "text": "こんにちは",
            }
        )
        assert isinstance(msg, PlayerStatement)
        assert msg.text == "こんにちは"


class TestClientDiscriminator:
    def test_unknown_action_raises(self):
        with pytest.raises(ValidationError):
            client_adapter.validate_python({"action": "nonexistent"})


# ---------------------------------------------------------------------------
# Server messages
# ---------------------------------------------------------------------------


class TestSessionRestore:
    def test_incremental_mode(self):
        msg = server_adapter.validate_python(
            {
                "type": "session_restore",
                "event_id": 1,
                "timestamp": "2025-01-01T00:00:00+00:00",
                "mode": "incremental",
                "current_state": {},
            }
        )
        assert isinstance(msg, SessionRestore)
        assert msg.missed_events == []

    def test_full_sync_with_missed_events(self):
        msg = server_adapter.validate_python(
            {
                "type": "session_restore",
                "event_id": 5,
                "timestamp": "2025-01-01T00:00:00+00:00",
                "mode": "full_sync",
                "current_state": {"hp": 10},
                "missed_events": [{"e": 1}],
            }
        )
        assert msg.missed_events == [{"e": 1}]  # type: ignore[union-attr]


class TestStateUpdate:
    def test_valid(self):
        msg = server_adapter.validate_python(
            {
                "type": "state_update",
                "event_id": 2,
                "timestamp": "2025-01-01T00:00:00+00:00",
                "version": 4,
                "patch": [{"op": "replace", "path": "/hp", "value": 5}],
            }
        )
        assert isinstance(msg, StateUpdate)
        assert msg.version == 4


class TestStateFull:
    def test_valid(self):
        msg = server_adapter.validate_python(
            {
                "type": "state_full",
                "event_id": 3,
                "timestamp": "2025-01-01T00:00:00+00:00",
                "version": 1,
                "state": {"turn": 2},
            }
        )
        assert isinstance(msg, StateFull)
        assert msg.state == {"turn": 2}


class TestGmNarrative:
    def test_default_not_streaming(self):
        msg = server_adapter.validate_python(
            {
                "type": "gm_narrative",
                "event_id": 4,
                "timestamp": "2025-01-01T00:00:00+00:00",
                "text": "敵が現れた！",
            }
        )
        assert isinstance(msg, GmNarrative)
        assert msg.is_streaming is False

    def test_streaming_flag(self):
        msg = server_adapter.validate_python(
            {
                "type": "gm_narrative",
                "event_id": 4,
                "timestamp": "2025-01-01T00:00:00+00:00",
                "text": "...",
                "is_streaming": True,
            }
        )
        assert msg.is_streaming is True  # type: ignore[union-attr]


class TestErrorMessage:
    def test_minimal(self):
        msg = server_adapter.validate_python(
            {
                "type": "error",
                "event_id": 99,
                "timestamp": "2025-01-01T00:00:00+00:00",
                "code": "INVALID_MESSAGE",
                "message": "bad input",
            }
        )
        assert isinstance(msg, ErrorMessage)
        assert msg.detail is None
        assert msg.client_request_id is None

    def test_with_detail_and_request_id(self):
        msg = server_adapter.validate_python(
            {
                "type": "error",
                "event_id": 99,
                "timestamp": "2025-01-01T00:00:00+00:00",
                "code": "OUT_OF_RANGE",
                "message": "value too large",
                "detail": {"max": 10},
                "client_request_id": "req-42",
            }
        )
        assert msg.detail == {"max": 10}  # type: ignore[union-attr]
        assert msg.client_request_id == "req-42"  # type: ignore[union-attr]


class TestServerDiscriminator:
    def test_unknown_type_raises(self):
        with pytest.raises(ValidationError):
            server_adapter.validate_python({"type": "unknown_type", "event_id": 0, "timestamp": ""})
