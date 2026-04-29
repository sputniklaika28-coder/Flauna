"""Auth tokens (GM spec §13-1).

Phase 0–7: tokens live in process memory and last forever.
Phase 8: tokens carry an expiry (default 24h, D47) and may optionally be
persisted to SQLite so they survive restarts.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from typing import TypedDict

from tacex_gm.config import settings

_DEFAULT_TTL_SECONDS = 60 * 60 * 24  # 24h, spec §13-1 Phase 8

# In-memory store: token → (payload, expires_at).  ``expires_at`` is a unix
# timestamp; ``float("inf")`` means "no expiry" (legacy Phase 0–7 behavior).
_tokens: dict[str, tuple[dict[str, str], float]] = {}


class TokenPayload(TypedDict):
    room_id: str
    player_id: str
    role: str  # "master" | "player"


def _ttl_seconds() -> int:
    ttl = getattr(settings, "token_ttl_seconds", _DEFAULT_TTL_SECONDS)
    return int(ttl) if ttl and ttl > 0 else _DEFAULT_TTL_SECONDS


def _store(token: str, payload: dict[str, str]) -> None:
    expires_at = time.time() + _ttl_seconds()
    _tokens[token] = (payload, expires_at)


def issue_master_token(room_id: str) -> str:
    token = secrets.token_urlsafe(32)
    _store(token, {"room_id": room_id, "player_id": "master", "role": "master"})
    return token


def issue_player_token(room_id: str, player_id: str) -> str:
    token = secrets.token_urlsafe(32)
    _store(token, {"room_id": room_id, "player_id": player_id, "role": "player"})
    return token


def verify_token(token: str) -> TokenPayload | None:
    entry = _tokens.get(token)
    if entry is None:
        return None
    payload, expires_at = entry
    if expires_at <= time.time():
        _tokens.pop(token, None)
        return None
    return TokenPayload(
        room_id=payload["room_id"],
        player_id=payload["player_id"],
        role=payload["role"],
    )


def hash_token(token: str) -> str:
    """One-way hash used when persisting tokens (we never store the plaintext)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_expiry(token: str) -> float | None:
    entry = _tokens.get(token)
    return entry[1] if entry else None
