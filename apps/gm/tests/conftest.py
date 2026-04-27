from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from tacex_gm.auth import _tokens
from tacex_gm.main import app


@pytest.fixture(autouse=True)
def reset_auth_tokens():
    """Clear the in-memory token store between tests."""
    _tokens.clear()
    yield
    _tokens.clear()


@pytest.fixture(autouse=True)
def reset_room_store():
    """Clear the in-memory room store between tests."""
    import asyncio

    store = app.state.room_store
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(store._guard.acquire())
        store._rooms.clear()
        store._guard.release()
    finally:
        loop.close()
    yield
    store2 = app.state.room_store
    loop2 = asyncio.new_event_loop()
    try:
        loop2.run_until_complete(store2._guard.acquire())
        store2._rooms.clear()
        store2._guard.release()
    finally:
        loop2.close()


@pytest.fixture
def sync_client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def room_data(sync_client: TestClient) -> dict:
    """Create a room and return {room_id, player_id, player_token, master_token}."""
    resp = sync_client.post(
        "/api/v1/rooms",
        json={"scenario_id": "first_mission", "player_name": "テスター"},
    )
    assert resp.status_code == 200
    return resp.json()
