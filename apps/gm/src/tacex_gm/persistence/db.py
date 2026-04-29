"""Async-friendly thin wrapper around stdlib ``sqlite3`` (Phase 8).

We deliberately avoid ``aiosqlite`` to keep dependencies minimal (cf.
GM spec ⚠ instruction §7: 依存最小化).  All blocking calls are dispatched
to a worker thread via :func:`asyncio.to_thread`.
"""

from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .schema import SCHEMA_SQL


class Database:
    """Single-connection SQLite handle, safe for one-event-loop access.

    The connection is created with ``check_same_thread=False`` because each
    call hops to a worker thread; concurrent access is serialised through
    :attr:`_lock` so the underlying connection sees only one operation at a
    time.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = asyncio.Lock()

    async def execute(self, sql: str, params: Iterable[Any] = ()) -> None:
        async with self._lock:
            await asyncio.to_thread(self._execute_commit, sql, tuple(params))

    async def execute_many(self, statements: Iterable[tuple[str, Iterable[Any]]]) -> None:
        prepared = [(sql, tuple(params)) for sql, params in statements]

        async with self._lock:
            await asyncio.to_thread(self._execute_many_commit, prepared)

    async def fetch_one(self, sql: str, params: Iterable[Any] = ()) -> tuple[Any, ...] | None:
        async with self._lock:
            return await asyncio.to_thread(self._fetch_one, sql, tuple(params))

    async def fetch_all(self, sql: str, params: Iterable[Any] = ()) -> list[tuple[Any, ...]]:
        async with self._lock:
            return await asyncio.to_thread(self._fetch_all, sql, tuple(params))

    async def close(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._conn.close)

    # ------------------------------------------------------------------ sync
    def _execute_commit(self, sql: str, params: tuple[Any, ...]) -> None:
        self._conn.execute(sql, params)
        self._conn.commit()

    def _execute_many_commit(self, statements: list[tuple[str, tuple[Any, ...]]]) -> None:
        cur = self._conn.cursor()
        try:
            for sql, params in statements:
                cur.execute(sql, params)
            self._conn.commit()
        finally:
            cur.close()

    def _fetch_one(self, sql: str, params: tuple[Any, ...]) -> tuple[Any, ...] | None:
        cur = self._conn.execute(sql, params)
        try:
            row = cur.fetchone()
        finally:
            cur.close()
        return tuple(row) if row is not None else None

    def _fetch_all(self, sql: str, params: tuple[Any, ...]) -> list[tuple[Any, ...]]:
        cur = self._conn.execute(sql, params)
        try:
            rows = cur.fetchall()
        finally:
            cur.close()
        return [tuple(r) for r in rows]


def _build_connection(db_path: str) -> sqlite3.Connection:
    """Create a connection and run the bootstrap schema."""
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    try:
        for stmt in SCHEMA_SQL:
            cur.execute(stmt)
        conn.commit()
    finally:
        cur.close()
    return conn


async def open_database(db_path: str) -> Database:
    """Open (and bootstrap) a SQLite database at *db_path*.

    Use ``":memory:"`` for ephemeral in-process storage (tests).
    """
    conn = await asyncio.to_thread(_build_connection, db_path)
    return Database(conn)
