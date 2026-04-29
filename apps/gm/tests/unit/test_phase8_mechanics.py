"""Phase 8 mechanics: SQLite persistence + 複数術修得 (multi-art mastery)."""

from __future__ import annotations

import json
import time

import pytest

from tacex_gm.engine.cast_art import resolve_cast_art
from tacex_gm.models.character import Character
from tacex_gm.models.turn_action import CastArt
from tacex_gm.persistence import Repository, open_database
from tacex_gm.system_module.tactical_exorcist.arts import (
    ArtDefinition,
    ArtRegistry,
    caster_knows_art,
    known_arts,
    validate_caster,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _exorcist(
    arts: list[str] | None = None,
    skills: list[str] | None = None,
    mp: int = 4,
    jutsu: int = 1,
) -> Character:
    return Character(
        id="pc1",
        name="術者",
        player_id="player1",
        faction="pc",
        tai=4,
        rei=6,
        kou=4,
        jutsu=jutsu,
        max_hp=20,
        max_mp=8,
        hp=20,
        mp=mp,
        evasion_dice=3,
        max_evasion_dice=3,
        position=(0, 0),
        skills=list(skills if skills is not None else ["祓魔の心得"]),
        arts=list(arts if arts is not None else []),
    )


def _registry() -> ArtRegistry:
    return ArtRegistry(
        [
            ArtDefinition(
                name="加護防壁",
                mp_cost=2,
                target_type="single",
                description="味方を守る",
            ),
            ArtDefinition(
                name="反閃歩法",
                mp_cost=2,
                target_type="self",
                description="自身を加速",
            ),
            ArtDefinition(
                name="霊力放出",
                mp_cost=3,
                target_type="area",
                description="範囲攻撃",
            ),
        ]
    )


# ---------------------------------------------------------------------------
# 複数術修得 — multi-art mastery
# ---------------------------------------------------------------------------


class TestKnownArts:
    def test_returns_arts_list(self):
        c = _exorcist(arts=["加護防壁", "反閃歩法"])
        assert known_arts(c) == ["加護防壁", "反閃歩法"]

    def test_empty_for_character_without_arts(self):
        c = _exorcist(arts=[])
        assert known_arts(c) == []

    def test_caster_knows_art(self):
        c = _exorcist(arts=["加護防壁"])
        assert caster_knows_art(c, "加護防壁") is True
        assert caster_knows_art(c, "反閃歩法") is False


class TestValidateCaster:
    def test_accepts_qualified_caster(self):
        c = _exorcist(arts=["加護防壁"])
        art = _registry().get("加護防壁")
        assert art is not None
        assert validate_caster(c, art) is None

    def test_rejects_when_art_not_learned(self):
        c = _exorcist(arts=["反閃歩法"])
        art = _registry().get("加護防壁")
        assert art is not None
        msg = validate_caster(c, art)
        assert msg is not None and "修得" in msg

    def test_rejects_without_basic_skill(self):
        c = _exorcist(arts=["加護防壁"], skills=[])
        art = _registry().get("加護防壁")
        assert art is not None
        msg = validate_caster(c, art)
        assert msg is not None and "祓魔の心得" in msg

    def test_rejects_with_zero_jutsu_rank(self):
        c = _exorcist(arts=["加護防壁"], jutsu=0)
        art = _registry().get("加護防壁")
        assert art is not None
        msg = validate_caster(c, art)
        assert msg is not None and "ランク" in msg

    def test_rejects_when_mp_insufficient(self):
        c = _exorcist(arts=["加護防壁"], mp=1)
        art = _registry().get("加護防壁")
        assert art is not None
        msg = validate_caster(c, art)
        assert msg is not None and "MP" in msg


class TestResolveCastArt:
    def test_pays_mp_on_success(self):
        c = _exorcist(arts=["加護防壁"], mp=4)
        action = CastArt(art_name="加護防壁", target="ally1")
        result = resolve_cast_art(c, action, _registry())
        assert result.success
        assert result.mp_spent == 2
        assert result.updated_caster is not None
        assert result.updated_caster.mp == 2
        assert "加護防壁" in result.narrative

    def test_can_switch_between_known_arts_in_same_session(self):
        # 複数術修得 — character has learned several arts and can pick one each turn.
        c = _exorcist(arts=["加護防壁", "反閃歩法", "霊力放出"], mp=8)
        registry = _registry()

        first = resolve_cast_art(c, CastArt(art_name="反閃歩法"), registry)
        assert first.success and first.updated_caster is not None
        assert first.updated_caster.mp == 6

        second = resolve_cast_art(
            first.updated_caster,
            CastArt(art_name="霊力放出", center_position=(3, 3)),
            registry,
        )
        assert second.success and second.updated_caster is not None
        assert second.updated_caster.mp == 3

    def test_unknown_art_fails(self):
        c = _exorcist(arts=["加護防壁"])
        action = CastArt(art_name="霊弾発射")
        result = resolve_cast_art(c, action, _registry())
        assert not result.success
        assert result.error and "Unknown" in result.error

    def test_unlearned_art_fails(self):
        c = _exorcist(arts=["反閃歩法"])
        action = CastArt(art_name="加護防壁", target="ally1")
        result = resolve_cast_art(c, action, _registry())
        assert not result.success
        assert result.mp_spent == 0
        assert result.updated_caster is None

    def test_target_validation_runs_before_mp_check(self):
        c = _exorcist(arts=["加護防壁"], mp=0)
        action = CastArt(art_name="加護防壁", target=None)  # missing target
        result = resolve_cast_art(c, action, _registry())
        assert not result.success
        assert result.error and "target_id" in result.error


# ---------------------------------------------------------------------------
# Persistence layer
# ---------------------------------------------------------------------------


class TestPersistenceRoundTrip:
    @pytest.mark.asyncio
    async def test_room_upsert_and_fetch(self):
        db = await open_database(":memory:")
        repo = Repository(db)
        await repo.upsert_room("room-1", "first_mission")
        row = await repo.get_room("room-1")
        assert row is not None
        assert row.scenario_id == "first_mission"
        await db.close()

    @pytest.mark.asyncio
    async def test_room_upsert_is_idempotent(self):
        db = await open_database(":memory:")
        repo = Repository(db)
        await repo.upsert_room("room-1", "first_mission")
        await repo.upsert_room("room-1", "first_mission")
        rows = await repo.list_rooms()
        assert len(rows) == 1
        await db.close()

    @pytest.mark.asyncio
    async def test_player_round_trip(self):
        db = await open_database(":memory:")
        repo = Repository(db)
        await repo.upsert_room("room-1", "first_mission")
        await repo.upsert_player("player-1", "room-1", "テスター")
        await repo.upsert_player("player-2", "room-1", "二号機", character_id="pc-2")
        players = await repo.list_players("room-1")
        assert {p.player_id for p in players} == {"player-1", "player-2"}
        with_char = next(p for p in players if p.player_id == "player-2")
        assert with_char.character_id == "pc-2"
        await db.close()

    @pytest.mark.asyncio
    async def test_auth_token_lookup_and_expiry(self):
        db = await open_database(":memory:")
        repo = Repository(db)
        await repo.upsert_room("room-1", "first_mission")

        future = time.time() + 3600
        past = time.time() - 60
        await repo.insert_auth_token("hash-good", "room-1", "p1", "player", future)
        await repo.insert_auth_token("hash-old", "room-1", "p2", "player", past)

        good = await repo.find_auth_token("hash-good")
        assert good is not None and good.player_id == "p1"

        # Purge and confirm the expired token disappears while the live one stays.
        await repo.purge_expired_tokens()
        assert await repo.find_auth_token("hash-old") is None
        assert await repo.find_auth_token("hash-good") is not None
        await db.close()

    @pytest.mark.asyncio
    async def test_state_snapshot_round_trip(self):
        db = await open_database(":memory:")
        repo = Repository(db)
        await repo.upsert_room("room-1", "first_mission")

        snapshot = json.dumps({"version": 7, "characters": []})
        await repo.save_state_snapshot("room-1", snapshot, version=7)

        loaded = await repo.load_state_snapshot("room-1")
        assert loaded is not None
        assert loaded.version == 7
        assert json.loads(loaded.state_json)["version"] == 7

        # Newer snapshot overwrites the older one.
        await repo.save_state_snapshot("room-1", json.dumps({"version": 9}), version=9)
        latest = await repo.load_state_snapshot("room-1")
        assert latest is not None and latest.version == 9
        await db.close()

    @pytest.mark.asyncio
    async def test_delete_room_cascades(self):
        db = await open_database(":memory:")
        repo = Repository(db)
        await repo.upsert_room("room-1", "first_mission")
        await repo.upsert_player("p1", "room-1", "テスター")
        await repo.save_state_snapshot("room-1", "{}", 1)

        await repo.delete_room("room-1")

        assert await repo.get_room("room-1") is None
        assert await repo.list_players("room-1") == []
        assert await repo.load_state_snapshot("room-1") is None
        await db.close()


class TestRoomStorePersistence:
    @pytest.mark.asyncio
    async def test_create_session_writes_to_repository(self):
        from tacex_gm.ai.mock_backend import MockLLMBackend
        from tacex_gm.ai.narration_engine import NarrationTemplateEngine
        from tacex_gm.room.lock import RoomLockRegistry
        from tacex_gm.room.session import RoomStore

        db = await open_database(":memory:")
        repo = Repository(db)
        store = RoomStore(
            lock_registry=RoomLockRegistry(),
            llm_backend=MockLLMBackend(),
            narration=NarrationTemplateEngine({}),
            weapon_catalog={},
            enemy_catalog={},
            repository=repo,
        )

        await store.create_session("room-X", "first_mission")
        row = await repo.get_room("room-X")
        assert row is not None
        assert row.scenario_id == "first_mission"
        await db.close()

    @pytest.mark.asyncio
    async def test_restore_from_repository_repopulates_sessions(self):
        from tacex_gm.ai.mock_backend import MockLLMBackend
        from tacex_gm.ai.narration_engine import NarrationTemplateEngine
        from tacex_gm.room.lock import RoomLockRegistry
        from tacex_gm.room.session import RoomStore

        db = await open_database(":memory:")
        repo = Repository(db)
        # Seed two rooms directly through the repository (simulating prior process).
        await repo.upsert_room("room-A", "first_mission")
        await repo.upsert_room("room-B", "first_mission")

        store = RoomStore(
            lock_registry=RoomLockRegistry(),
            llm_backend=MockLLMBackend(),
            narration=NarrationTemplateEngine({}),
            weapon_catalog={},
            enemy_catalog={},
            repository=repo,
        )
        restored = await store.restore_from_repository()
        assert restored == 2
        assert store.get_session("room-A") is not None
        assert store.get_session("room-B") is not None
        await db.close()
