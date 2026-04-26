from httpx import AsyncClient, ASGITransport

from tacex_gm.main import app


async def test_health() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_create_room() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/rooms",
            json={"scenario_id": "first_mission", "player_name": "GM"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_title"] == "最初の任務"
    assert data["room_id"].startswith("room-")
    assert len(data["master_token"]) > 10
