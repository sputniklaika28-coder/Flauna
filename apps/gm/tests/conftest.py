"""Shared pytest fixtures."""
import pytest
from httpx import ASGITransport, AsyncClient

from tacex_gm.main import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
