from __future__ import annotations

import pytest

from tacex_gm.auth import (
    _tokens,
    issue_master_token,
    issue_player_token,
    verify_token,
)


@pytest.fixture(autouse=True)
def clear_tokens():
    _tokens.clear()
    yield
    _tokens.clear()


class TestIssueMasterToken:
    def test_returns_non_empty_token(self):
        token = issue_master_token("room-abc")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_stored_with_correct_payload(self):
        token = issue_master_token("room-abc")
        payload, expires_at = _tokens[token]
        assert payload["room_id"] == "room-abc"
        assert payload["player_id"] == "master"
        assert payload["role"] == "master"
        assert expires_at > 0

    def test_different_tokens_for_different_rooms(self):
        t1 = issue_master_token("room-1")
        t2 = issue_master_token("room-2")
        assert t1 != t2

    def test_tokens_are_unique(self):
        tokens = {issue_master_token("room-x") for _ in range(20)}
        assert len(tokens) == 20


class TestIssuePlayerToken:
    def test_returns_non_empty_token(self):
        token = issue_player_token("room-abc", "player-1")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_stored_with_correct_payload(self):
        token = issue_player_token("room-abc", "player-1")
        payload, expires_at = _tokens[token]
        assert payload["room_id"] == "room-abc"
        assert payload["player_id"] == "player-1"
        assert payload["role"] == "player"
        assert expires_at > 0

    def test_tokens_are_unique(self):
        tokens = {issue_player_token("room-x", f"player-{i}") for i in range(20)}
        assert len(tokens) == 20


class TestVerifyToken:
    def test_valid_master_token(self):
        token = issue_master_token("room-abc")
        result = verify_token(token)
        assert result is not None
        assert result["room_id"] == "room-abc"
        assert result["player_id"] == "master"
        assert result["role"] == "master"

    def test_valid_player_token(self):
        token = issue_player_token("room-abc", "player-99")
        result = verify_token(token)
        assert result is not None
        assert result["room_id"] == "room-abc"
        assert result["player_id"] == "player-99"
        assert result["role"] == "player"

    def test_unknown_token_returns_none(self):
        assert verify_token("not-a-real-token") is None

    def test_empty_token_returns_none(self):
        assert verify_token("") is None
