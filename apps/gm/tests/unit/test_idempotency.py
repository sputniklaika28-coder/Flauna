from __future__ import annotations

import pytest

from tacex_gm.ws.idempotency import IdempotencyCache


class TestIdempotencyCache:
    def test_records_and_retrieves(self) -> None:
        cache: IdempotencyCache[str] = IdempotencyCache(max_size=2)
        cache.record("a", "result-a")
        assert cache.get("a") == "result-a"
        assert "a" in cache
        assert len(cache) == 1

    def test_get_missing_returns_none(self) -> None:
        cache: IdempotencyCache[str] = IdempotencyCache(max_size=2)
        assert cache.get("missing") is None

    def test_lru_eviction(self) -> None:
        cache: IdempotencyCache[str] = IdempotencyCache(max_size=2)
        cache.record("a", "1")
        cache.record("b", "2")
        cache.record("c", "3")  # evicts 'a'
        assert "a" not in cache
        assert cache.get("b") == "2"
        assert cache.get("c") == "3"

    def test_get_promotes_lru(self) -> None:
        cache: IdempotencyCache[str] = IdempotencyCache(max_size=2)
        cache.record("a", "1")
        cache.record("b", "2")
        # Touch 'a' so 'b' becomes least-recently-used
        assert cache.get("a") == "1"
        cache.record("c", "3")  # should evict 'b'
        assert "b" not in cache
        assert cache.get("a") == "1"
        assert cache.get("c") == "3"

    def test_re_record_updates_value_and_promotes(self) -> None:
        cache: IdempotencyCache[str] = IdempotencyCache(max_size=2)
        cache.record("a", "1")
        cache.record("b", "2")
        cache.record("a", "1-updated")  # promote 'a' and update
        cache.record("c", "3")  # should evict 'b'
        assert "b" not in cache
        assert cache.get("a") == "1-updated"

    def test_clear(self) -> None:
        cache: IdempotencyCache[int] = IdempotencyCache(max_size=2)
        cache.record("a", 1)
        cache.clear()
        assert len(cache) == 0
        assert cache.get("a") is None

    def test_invalid_max_size(self) -> None:
        with pytest.raises(ValueError):
            IdempotencyCache(max_size=0)
        with pytest.raises(ValueError):
            IdempotencyCache(max_size=-1)
