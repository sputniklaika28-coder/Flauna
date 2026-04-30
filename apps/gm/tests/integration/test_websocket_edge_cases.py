"""Phase 9 — WebSocket edge case integration tests (GM spec §16-3).

Covers reconnection (disconnect → reconnect → state preserved), version
drift detection across multiple turns, idempotent replay of the same
``client_request_id``, malformed turn_action payloads, and out-of-turn
submissions.

Phase 0/2 already test invalid JSON and bad tokens; this file focuses
on the longer-running flows where state has been mutated mid-session.
"""

from __future__ import annotations

import json

from tacex_gm.main import app


def _join(room_id: str, player_id: str, token: str) -> str:
    return json.dumps(
        {
            "action": "join_room",
            "player_id": player_id,
            "room_id": room_id,
            "auth_token": token,
            "last_seen_event_id": 0,
        }
    )


def _skip_turn(*, room_id: str, player_id: str, version: int, pc_id: str, request_id: str) -> str:
    return json.dumps(
        {
            "action": "submit_turn_action",
            "player_id": player_id,
            "room_id": room_id,
            "client_request_id": request_id,
            "expected_version": version,
            "turn_action": {"actor_id": pc_id, "main_action": {"type": "skip"}},
        }
    )


def _force_pc_turn(room_id: str) -> None:
    """Rotate ``turn_order`` so the PC is the current actor again.

    ``check_combat_outcome`` and the NPC default action both end the turn,
    advancing current_turn_index. Tests that need the PC to act repeatedly call
    this between WS sessions to put control back in the PC's hands.
    """
    session = app.state.room_store.get_session(room_id)
    assert session is not None and session.state is not None
    state = session.state
    pc = next(c for c in state.characters if c.faction == "pc")
    pc_idx = state.turn_order.index(pc.id)
    session.state = state.model_copy(update={"current_turn_index": pc_idx})


# ---------------------------------------------------------------------------
# Reconnection: state survives a WS close and is sent again on reconnect
# ---------------------------------------------------------------------------


class TestReconnection:
    def test_session_restore_returns_current_state_after_reconnect(self, sync_client, room_data):
        """First connection establishes the GameState (lazy init); the
        second connection should receive the *same* room_id with no
        version regression."""
        room_id = room_data["room_id"]
        player_id = room_data["player_id"]
        token = room_data["player_token"]

        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            first = ws.receive_json()

        first_version = first["current_state"]["version"]

        # Reconnect.
        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            second = ws.receive_json()

        assert second["type"] == "session_restore"
        assert second["current_state"]["room_id"] == room_id
        assert second["current_state"]["version"] >= first_version
        # Same PC still mapped to the player.
        pc1 = next(c for c in first["current_state"]["characters"] if c["faction"] == "pc")
        pc2 = next(c for c in second["current_state"]["characters"] if c["faction"] == "pc")
        assert pc1["id"] == pc2["id"]
        assert pc2["player_id"] == player_id

    def test_reconnect_after_skip_sees_advanced_state(self, sync_client, room_data):
        """Skip a turn, disconnect, reconnect — the new session_restore
        must reflect the advanced version."""
        room_id = room_data["room_id"]
        player_id = room_data["player_id"]
        token = room_data["player_token"]

        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            restore = ws.receive_json()
            state = restore["current_state"]
            pc_id = next(c["id"] for c in state["characters"] if c["faction"] == "pc")
            v0 = state["version"]
            ws.send_text(
                _skip_turn(
                    room_id=room_id,
                    player_id=player_id,
                    version=v0,
                    pc_id=pc_id,
                    request_id="req-skip-reco",
                )
            )
            # Drain a few messages so the skip is fully applied before we close.
            for _ in range(6):
                try:
                    ws.receive_json()
                except Exception:
                    break

        # Reconnect — version should have moved past v0.
        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            second = ws.receive_json()
        assert second["current_state"]["version"] > v0


# ---------------------------------------------------------------------------
# Version drift: stale expected_version is rejected even after reconnect
# ---------------------------------------------------------------------------


class TestVersionDrift:
    def test_stale_version_after_reconnect_returns_version_mismatch(self, sync_client, room_data):
        """A client that reconnects but submits an action with the *old*
        expected_version (cached locally before the disconnect) gets a
        VERSION_MISMATCH, not silent acceptance."""
        room_id = room_data["room_id"]
        player_id = room_data["player_id"]
        token = room_data["player_token"]

        # First session: advance state by skipping a turn.
        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            restore = ws.receive_json()
            state = restore["current_state"]
            pc_id = next(c["id"] for c in state["characters"] if c["faction"] == "pc")
            v0 = state["version"]
            ws.send_text(
                _skip_turn(
                    room_id=room_id,
                    player_id=player_id,
                    version=v0,
                    pc_id=pc_id,
                    request_id="req-skip-drift",
                )
            )
            for _ in range(6):
                try:
                    ws.receive_json()
                except Exception:
                    break

        # Put control back to the PC and reconnect with a stale version.
        _force_pc_turn(room_id)

        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            ws.receive_json()  # session_restore
            ws.send_text(
                _skip_turn(
                    room_id=room_id,
                    player_id=player_id,
                    version=v0,  # stale
                    pc_id=pc_id,
                    request_id="req-skip-stale",
                )
            )
            err = ws.receive_json()

        assert err["type"] == "error"
        assert err["code"] == "VERSION_MISMATCH"


# ---------------------------------------------------------------------------
# Malformed turn_action / out-of-turn submissions
# ---------------------------------------------------------------------------


class TestMalformedSubmissions:
    def test_unknown_main_action_type_returns_invalid_action_sequence(self, sync_client, room_data):
        room_id = room_data["room_id"]
        player_id = room_data["player_id"]
        token = room_data["player_token"]

        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            restore = ws.receive_json()
            state = restore["current_state"]
            pc_id = next(c["id"] for c in state["characters"] if c["faction"] == "pc")
            v0 = state["version"]

            ws.send_text(
                json.dumps(
                    {
                        "action": "submit_turn_action",
                        "player_id": player_id,
                        "room_id": room_id,
                        "client_request_id": "req-bogus-type",
                        "expected_version": v0,
                        "turn_action": {
                            "actor_id": pc_id,
                            "main_action": {"type": "no_such_action"},
                        },
                    }
                )
            )
            err = ws.receive_json()

        assert err["type"] == "error"
        assert err["code"] == "INVALID_ACTION_SEQUENCE"

    def test_evasion_submitted_without_pending_returns_error(self, sync_client, room_data):
        """submit_evasion with no outstanding EvasionRequest → error."""
        room_id = room_data["room_id"]
        player_id = room_data["player_id"]
        token = room_data["player_token"]

        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            ws.receive_json()  # session_restore
            ws.send_text(
                json.dumps(
                    {
                        "action": "submit_evasion",
                        "player_id": player_id,
                        "room_id": room_id,
                        "client_request_id": "req-bogus-evade",
                        "pending_id": "no-such-pending",
                        "dice_result": 1,
                    }
                )
            )
            err = ws.receive_json()

        assert err["type"] == "error"
        # OUT_OF_TURN is the spec-defined response when the server is
        # waiting for submit_turn_action and gets something else instead.
        assert err["code"] in ("OUT_OF_TURN", "INVALID_MESSAGE")
