from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from tacex_gm.ai.backend import LLMBackend
from tacex_gm.ai.mock_backend import MockLLMBackend
from tacex_gm.ai.narration_engine import NarrationTemplateEngine
from tacex_gm.api.rooms import router as rooms_router
from tacex_gm.config import settings
from tacex_gm.room.lock import RoomLockRegistry
from tacex_gm.room.session import RoomStore
from tacex_gm.scenario.loader import load_enemies, load_narration_templates, load_weapons
from tacex_gm.ws.handler import handle_room_websocket

logging.basicConfig(level=settings.log_level.upper())

# ---------------------------------------------------------------------------
# Shared resources (loaded once at startup)
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_SCENARIO_DIR = Path(__file__).parent.parent.parent / "scenarios"


def _load_resources() -> RoomStore:
    weapon_catalog = load_weapons(_DATA_DIR / "weapons.yaml")
    enemy_catalog = load_enemies(_DATA_DIR / "enemies.yaml")

    narration_templates = load_narration_templates(_DATA_DIR / "narration_templates.yaml")
    narration_engine = NarrationTemplateEngine(narration_templates)

    # Use MockLLMBackend unless a real API key is configured.
    llm_backend: LLMBackend = MockLLMBackend()
    if settings.anthropic_api_key:
        from tacex_gm.ai.anthropic_backend import AnthropicBackend

        llm_backend = AnthropicBackend(api_key=settings.anthropic_api_key)

    lock_registry = RoomLockRegistry()

    return RoomStore(
        lock_registry=lock_registry,
        llm_backend=llm_backend,
        narration=narration_engine,
        weapon_catalog=weapon_catalog,
        enemy_catalog=enemy_catalog,
    )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(title="TacEx-GM", version="0.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rooms_router)
app.state.room_store = _load_resources()
app.state.scenario_dir = str(_SCENARIO_DIR)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> dict[str, str]:
    return {"status": "stub"}


@app.websocket("/room/{room_id}")
async def websocket_room(websocket: WebSocket, room_id: str) -> None:
    await handle_room_websocket(
        websocket,
        room_id,
        app.state.room_store,
        app.state.scenario_dir,
    )
