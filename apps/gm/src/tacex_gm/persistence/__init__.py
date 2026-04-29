"""SQLite persistence layer (Phase 8, GM spec §15-1, D12).

Opt-in: enabled when ``settings.db_path`` is non-empty.  When disabled
(default for tests and the in-memory MVP), the rest of the system continues
to operate purely from process-local state.
"""

from .db import Database, open_database
from .repository import (
    AuthTokenRecord,
    PlayerRecord,
    Repository,
    RoomRecord,
    StateSnapshotRecord,
)

__all__ = [
    "AuthTokenRecord",
    "Database",
    "PlayerRecord",
    "Repository",
    "RoomRecord",
    "StateSnapshotRecord",
    "open_database",
]
