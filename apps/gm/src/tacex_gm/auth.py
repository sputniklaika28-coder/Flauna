from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from .config import config


def _create_token(payload: dict[str, Any]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=config.jwt_expire_hours)
    return jwt.encode(
        {**payload, "exp": expire},
        config.jwt_secret,
        algorithm=config.jwt_algorithm,
    )


def create_master_token(room_id: str) -> str:
    return _create_token({"room_id": room_id, "role": "master"})


def create_player_token(room_id: str, player_id: str) -> str:
    return _create_token({"room_id": room_id, "player_id": player_id, "role": "player"})


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def generate_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(6)}"
