"""Phase 9 — long-running stability tests (GM spec §15-1, §16-3).

These tests drive a single room through many sequential PC turns to
verify the invariants that matter for an all-day session:

- ``state.version`` is strictly monotonic.
- ``next_event_id`` only ever grows.
- Per-room idempotency cache stays bounded.
- The room store does not accumulate orphan rooms.
- Memory does not grow unboundedly per turn (sanity check via
  ``len(state.events)`` if events are stored, and via the cache size).
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


def _force_pc_turn(room_id: str) -> int:
    """Rotate ``turn_order`` so the PC actor is current. Returns version."""
    session = app.state.room_store.get_session(room_id)
    assert session is not None and session.state is not None
    state = session.state
    pc = next(c for c in state.characters if c.faction == "pc")
    pc_idx = state.turn_order.index(pc.id)
    if state.current_turn_index != pc_idx:
        session.state = state.model_copy(update={"current_turn_index": pc_idx})
    return session.state.version


class TestLongRunningSession:
    def test_many_skip_turns_keep_version_and_event_id_monotonic(self, sync_client, room_data):
        """Drive 25 PC skip turns in the same room. Confirm version and
        event_id grow monotonically and the session never desyncs."""
        room_id = room_data["room_id"]
        player_id = room_data["player_id"]
        token = room_data["player_token"]

        n_turns = 25
        prev_version = -1
        prev_event_id = -1

        # Lazy-init the GameState by opening the WS once.
        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            ws.receive_json()

        for i in range(n_turns):
            # Make sure it's the PC's turn before each cycle.
            _force_pc_turn(room_id)

            with sync_client.websocket_connect(f"/room/{room_id}") as ws:
                ws.send_text(_join(room_id, player_id, token))
                restore = ws.receive_json()
                state = restore["current_state"]
                pc_id = next(c["id"] for c in state["characters"] if c["faction"] == "pc")
                version = state["version"]
                event_id = restore["event_id"]

                assert version > prev_version, (
                    f"turn {i}: version {version} did not increase past {prev_version}"
                )
                assert event_id >= prev_event_id, (
                    f"turn {i}: event_id {event_id} regressed from {prev_event_id}"
                )

                ws.send_text(
                    _skip_turn(
                        room_id=room_id,
                        player_id=player_id,
                        version=version,
                        pc_id=pc_id,
                        request_id=f"req-skip-{i}",
                    )
                )
                # Drain a few messages so the skip lands.
                for _ in range(8):
                    try:
                        ws.receive_json()
                    except Exception:
                        break

                prev_version = version
                prev_event_id = event_id

        # Final assertions: state still consistent.
        session = app.state.room_store.get_session(room_id)
        assert session is not None and session.state is not None
        assert session.state.version > prev_version
        # Idempotency cache is bounded.
        assert len(session.idempotency) <= session.idempotency.max_size

    def test_many_turns_do_not_leak_rooms_or_connections(self, sync_client, room_data):
        """Repeated connect/disconnect to the same room should leave no
        lingering connections in ``session.connections``."""
        room_id = room_data["room_id"]
        player_id = room_data["player_id"]
        token = room_data["player_token"]

        for _ in range(15):
            with sync_client.websocket_connect(f"/room/{room_id}") as ws:
                ws.send_text(_join(room_id, player_id, token))
                ws.receive_json()  # session_restore

        session = app.state.room_store.get_session(room_id)
        assert session is not None
        # Every WS exited cleanly → no live connections registered.
        assert len(session.connections) == 0, session.connections
        # Per-player message queues should also be cleaned up.
        assert len(session.message_queues) == 0, session.message_queues

    def test_room_store_size_stable_across_repeated_sessions(self, sync_client):
        """Creating and using N rooms should leave exactly N entries in
        the store — no duplicates, no leaks past test cleanup."""
        store = app.state.room_store
        baseline = len(store._rooms)

        n = 20
        for i in range(n):
            resp = sync_client.post(
                "/api/v1/rooms",
                json={"scenario_id": "first_mission", "player_name": f"P{i}"},
            )
            data = resp.json()
            with sync_client.websocket_connect(f"/room/{data['room_id']}") as ws:
                ws.send_text(_join(data["room_id"], data["player_id"], data["player_token"]))
                ws.receive_json()

        assert len(store._rooms) == baseline + n
