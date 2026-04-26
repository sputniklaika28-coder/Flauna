"""Simple in-memory token store (Phase 0-7). Phase 8 moves this to SQLite."""
import secrets
from dataclasses import dataclass, field


@dataclass
class TokenRecord:
    player_id: str
    room_id: str
    is_master: bool = False


_tokens: dict[str, TokenRecord] = {}


def issue_token(player_id: str, room_id: str, *, is_master: bool = False) -> str:
    token = secrets.token_urlsafe(32)
    _tokens[token] = TokenRecord(
        player_id=player_id, room_id=room_id, is_master=is_master
    )
    return token


def verify_token(token: str) -> TokenRecord | None:
    return _tokens.get(token)


def revoke_room_tokens(room_id: str) -> None:
    to_delete = [t for t, r in _tokens.items() if r.room_id == room_id]
    for t in to_delete:
        del _tokens[t]
