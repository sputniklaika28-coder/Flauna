"""SQLite schema definitions (Phase 8).

The schema is intentionally narrow — only what is needed to survive a
process restart: room registry, player registry, auth tokens with expiry
(§13-1, D47, Phase 8: 24h), and the latest game-state snapshot per room.
"""

from __future__ import annotations

SCHEMA_SQL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS rooms (
        room_id TEXT PRIMARY KEY,
        scenario_id TEXT NOT NULL,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS players (
        player_id TEXT PRIMARY KEY,
        room_id TEXT NOT NULL,
        player_name TEXT NOT NULL,
        character_id TEXT NOT NULL DEFAULT '',
        created_at REAL NOT NULL,
        FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_players_room ON players(room_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_tokens (
        token_hash TEXT PRIMARY KEY,
        room_id TEXT NOT NULL,
        player_id TEXT NOT NULL,
        role TEXT NOT NULL,
        expires_at REAL NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_auth_tokens_room ON auth_tokens(room_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS state_snapshots (
        room_id TEXT PRIMARY KEY,
        state_json TEXT NOT NULL,
        version INTEGER NOT NULL,
        updated_at REAL NOT NULL,
        FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
    )
    """,
)
