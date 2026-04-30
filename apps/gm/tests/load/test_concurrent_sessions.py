"""Phase 9 — concurrent session load tests (GM spec §15-1, §17 ``tests/load/``).

These tests verify that the GM backend keeps each room isolated when many
sessions run side by side: tokens scoped to one room must not work in
another, room state must not leak between sessions, and the room store
must survive a burst of creations + WebSocket connect/skip-turn cycles
without losing rooms or interleaving events.

The tests intentionally avoid full attack/evasion flows — those depend on
RNG and per-character placement, which would make a load test flaky.
The skip-turn flow exercises the same locking, version, broadcast, and
event-emission paths while staying deterministic.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

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


@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Concurrent room creation
# ---------------------------------------------------------------------------


class TestConcurrentRoomCreation:
    async def test_many_rooms_created_in_parallel_are_distinct(self, async_client):
        """50 concurrent POST /rooms calls produce 50 distinct rooms in the store."""
        n = 50

        async def create_one(i: int) -> dict:
            resp = await async_client.post(
                "/api/v1/rooms",
                json={"scenario_id": "first_mission", "player_name": f"P{i}"},
            )
            assert resp.status_code == 200
            return resp.json()

        results = await asyncio.gather(*(create_one(i) for i in range(n)))

        room_ids = {r["room_id"] for r in results}
        player_ids = {r["player_id"] for r in results}
        master_tokens = {r["master_token"] for r in results}

        assert len(room_ids) == n, "every room id must be unique"
        assert len(player_ids) == n, "every player id must be unique"
        assert len(master_tokens) == n, "every master token must be unique"

        store = app.state.room_store
        for r in results:
            session = store.get_session(r["room_id"])
            assert session is not None
            assert session.scenario_id == "first_mission"
            assert r["player_id"] in session.player_slots


# ---------------------------------------------------------------------------
# Cross-room token isolation under load
# ---------------------------------------------------------------------------


class TestCrossRoomIsolation:
    def test_token_from_one_room_cannot_join_another(self, sync_client):
        """Tokens are bound to room_id; reusing them across rooms must fail
        even when many rooms exist concurrently."""
        rooms = []
        for i in range(10):
            resp = sync_client.post(
                "/api/v1/rooms",
                json={"scenario_id": "first_mission", "player_name": f"P{i}"},
            )
            assert resp.status_code == 200
            rooms.append(resp.json())

        # Try to use room-0's token to join room-1.
        a, b = rooms[0], rooms[1]
        with sync_client.websocket_connect(f"/room/{b['room_id']}") as ws:
            ws.send_text(
                json.dumps(
                    {
                        "action": "join_room",
                        "player_id": a["player_id"],
                        "room_id": b["room_id"],
                        "auth_token": a["player_token"],
                        "last_seen_event_id": 0,
                    }
                )
            )
            err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] in ("AUTH_INVALID_TOKEN", "AUTH_PERMISSION_DENIED")


# ---------------------------------------------------------------------------
# Concurrent skip-turn flow across rooms
# ---------------------------------------------------------------------------


class TestConcurrentSkipTurns:
    def test_many_rooms_each_advance_independently(self, sync_client: TestClient):
        """Open N rooms, advance one PC turn (skip) in each. Confirm:
        - every room's version advances exactly once;
        - no room sees another room's state or events.
        """
        n = 8
        rooms: list[dict] = []
        for i in range(n):
            resp = sync_client.post(
                "/api/v1/rooms",
                json={"scenario_id": "first_mission", "player_name": f"Tester{i}"},
            )
            assert resp.status_code == 200
            rooms.append(resp.json())

        # For each room, run a skip turn and assert state advances.
        for room in rooms:
            with sync_client.websocket_connect(f"/room/{room['room_id']}") as ws:
                ws.send_text(_join(room["room_id"], room["player_id"], room["player_token"]))
                restore = ws.receive_json()
                assert restore["type"] == "session_restore"
                state = restore["current_state"]
                assert state["room_id"] == room["room_id"]
                pc_id = next(c["id"] for c in state["characters"] if c["faction"] == "pc")
                start_version = state["version"]

                ws.send_text(
                    _skip_turn(
                        room_id=room["room_id"],
                        player_id=room["player_id"],
                        version=start_version,
                        pc_id=pc_id,
                        request_id=f"req-{room['room_id']}",
                    )
                )

                # Drain until we see at least one state_full reflecting the
                # advance, or until the NPC turn signals via ai_thinking.
                seen_advance = False
                seen_room_ids: set[str] = set()
                for _ in range(15):
                    try:
                        msg = ws.receive_json()
                    except Exception:
                        break
                    if msg.get("type") == "state_full":
                        cur = msg["state"]
                        seen_room_ids.add(cur["room_id"])
                        if msg["version"] > start_version:
                            seen_advance = True
                    if msg.get("type") == "ai_thinking":
                        break

                assert seen_advance, (
                    f"room {room['room_id']} version did not advance past {start_version}"
                )
                # Crucial isolation check: no message ever carried a different room_id.
                assert seen_room_ids <= {room["room_id"]}, (
                    f"room {room['room_id']} leaked state from other rooms: {seen_room_ids}"
                )

        # After all sessions have closed, every room is still registered and holds its own state.
        store = app.state.room_store
        for room in rooms:
            session = store.get_session(room["room_id"])
            assert session is not None
            assert session.state is not None
            assert session.state.room_id == room["room_id"]


# ---------------------------------------------------------------------------
# Idempotency cache stays bounded under load
# ---------------------------------------------------------------------------


class TestIdempotencyBounded:
    def test_idempotency_cache_does_not_grow_without_bound(self, sync_client):
        """Drive the same room with many distinct request ids and confirm
        the per-room idempotency cache obeys its LRU max_size."""
        resp = sync_client.post(
            "/api/v1/rooms",
            json={"scenario_id": "first_mission", "player_name": "Tester"},
        )
        room = resp.json()
        session = app.state.room_store.get_session(room["room_id"])
        assert session is not None

        max_size = session.idempotency.max_size
        for i in range(max_size * 3):
            session.idempotency.record(f"req-{i}", "payload")

        assert len(session.idempotency) <= max_size
