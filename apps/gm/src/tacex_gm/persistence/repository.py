"""Repository layer for persisted entities (Phase 8).

The repository is the only module that knows the SQLite schema; the rest
of the codebase deals in :class:`pydantic` records.  All methods are
``async`` so they integrate with the FastAPI runtime; under the hood they
delegate to :class:`~tacex_gm.persistence.db.Database`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .db import Database


@dataclass(frozen=True)
class RoomRecord:
    room_id: str
    scenario_id: str
    created_at: float
    updated_at: float


@dataclass(frozen=True)
class PlayerRecord:
    player_id: str
    room_id: str
    player_name: str
    character_id: str
    created_at: float


@dataclass(frozen=True)
class AuthTokenRecord:
    token_hash: str
    room_id: str
    player_id: str
    role: str
    expires_at: float


@dataclass(frozen=True)
class StateSnapshotRecord:
    room_id: str
    state_json: str
    version: int
    updated_at: float


class Repository:
    """High-level CRUD operations on the persisted tables."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------ rooms
    async def upsert_room(self, room_id: str, scenario_id: str) -> None:
        now = time.time()
        await self._db.execute(
            """
            INSERT INTO rooms (room_id, scenario_id, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(room_id) DO UPDATE SET
                scenario_id = excluded.scenario_id,
                updated_at = excluded.updated_at
            """,
            (room_id, scenario_id, now, now),
        )

    async def get_room(self, room_id: str) -> RoomRecord | None:
        row = await self._db.fetch_one(
            "SELECT room_id, scenario_id, created_at, updated_at FROM rooms WHERE room_id = ?",
            (room_id,),
        )
        if row is None:
            return None
        return RoomRecord(
            room_id=str(row[0]),
            scenario_id=str(row[1]),
            created_at=float(row[2]),
            updated_at=float(row[3]),
        )

    async def list_rooms(self) -> list[RoomRecord]:
        rows = await self._db.fetch_all(
            "SELECT room_id, scenario_id, created_at, updated_at FROM rooms ORDER BY created_at"
        )
        return [
            RoomRecord(
                room_id=str(r[0]),
                scenario_id=str(r[1]),
                created_at=float(r[2]),
                updated_at=float(r[3]),
            )
            for r in rows
        ]

    async def delete_room(self, room_id: str) -> None:
        await self._db.execute("DELETE FROM rooms WHERE room_id = ?", (room_id,))

    # ----------------------------------------------------------- players
    async def upsert_player(
        self,
        player_id: str,
        room_id: str,
        player_name: str,
        character_id: str = "",
    ) -> None:
        now = time.time()
        await self._db.execute(
            """
            INSERT INTO players (player_id, room_id, player_name, character_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                player_name = excluded.player_name,
                character_id = excluded.character_id
            """,
            (player_id, room_id, player_name, character_id, now),
        )

    async def list_players(self, room_id: str) -> list[PlayerRecord]:
        rows = await self._db.fetch_all(
            """
            SELECT player_id, room_id, player_name, character_id, created_at
            FROM players WHERE room_id = ? ORDER BY created_at
            """,
            (room_id,),
        )
        return [
            PlayerRecord(
                player_id=str(r[0]),
                room_id=str(r[1]),
                player_name=str(r[2]),
                character_id=str(r[3]),
                created_at=float(r[4]),
            )
            for r in rows
        ]

    # ------------------------------------------------------- auth tokens
    async def insert_auth_token(
        self,
        token_hash: str,
        room_id: str,
        player_id: str,
        role: str,
        expires_at: float,
    ) -> None:
        await self._db.execute(
            """
            INSERT INTO auth_tokens (token_hash, room_id, player_id, role, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (token_hash, room_id, player_id, role, expires_at),
        )

    async def find_auth_token(self, token_hash: str) -> AuthTokenRecord | None:
        row = await self._db.fetch_one(
            """
            SELECT token_hash, room_id, player_id, role, expires_at
            FROM auth_tokens WHERE token_hash = ?
            """,
            (token_hash,),
        )
        if row is None:
            return None
        return AuthTokenRecord(
            token_hash=str(row[0]),
            room_id=str(row[1]),
            player_id=str(row[2]),
            role=str(row[3]),
            expires_at=float(row[4]),
        )

    async def purge_expired_tokens(self, now: float | None = None) -> int:
        threshold = time.time() if now is None else now
        await self._db.execute("DELETE FROM auth_tokens WHERE expires_at <= ?", (threshold,))
        # SQLite doesn't return rowcount through this path; callers can re-query.
        return 0

    # ----------------------------------------------------- state snapshots
    async def save_state_snapshot(self, room_id: str, state_json: str, version: int) -> None:
        now = time.time()
        await self._db.execute(
            """
            INSERT INTO state_snapshots (room_id, state_json, version, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(room_id) DO UPDATE SET
                state_json = excluded.state_json,
                version = excluded.version,
                updated_at = excluded.updated_at
            """,
            (room_id, state_json, version, now),
        )

    async def load_state_snapshot(self, room_id: str) -> StateSnapshotRecord | None:
        row = await self._db.fetch_one(
            """
            SELECT room_id, state_json, version, updated_at
            FROM state_snapshots WHERE room_id = ?
            """,
            (room_id,),
        )
        if row is None:
            return None
        return StateSnapshotRecord(
            room_id=str(row[0]),
            state_json=str(row[1]),
            version=int(row[2]),
            updated_at=float(row[3]),
        )
