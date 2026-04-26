import secrets
from typing import TypedDict

# Phase 0: in-memory token store. Replace with persistent storage in Phase 1+.
_tokens: dict[str, dict[str, str]] = {}


class TokenPayload(TypedDict):
    room_id: str
    player_id: str
    role: str  # "master" | "player"


def issue_master_token(room_id: str) -> str:
    token = secrets.token_urlsafe(32)
    _tokens[token] = {"room_id": room_id, "player_id": "master", "role": "master"}
    return token


def issue_player_token(room_id: str, player_id: str) -> str:
    token = secrets.token_urlsafe(32)
    _tokens[token] = {"room_id": room_id, "player_id": player_id, "role": "player"}
    return token


def verify_token(token: str) -> TokenPayload | None:
    payload = _tokens.get(token)
    if payload is None:
        return None
    return TokenPayload(
        room_id=payload["room_id"],
        player_id=payload["player_id"],
        role=payload["role"],
    )
