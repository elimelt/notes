"""Cache tests: hit/miss semantics, byte entries, stats, error wrapping."""

from __future__ import annotations

import pytest

from linkdiscovery.artifacts import ArtifactCache, ArtifactStore, CacheStats
from linkdiscovery.errors import CacheError
from linkdiscovery.fingerprint import combine_fingerprints, fingerprint


class TestJsonEntries:
    def test_miss_returns_none(self, cache: ArtifactCache) -> None:
        assert cache.get("sha256:absent") is None

    def test_put_then_get_hits(self, cache: ArtifactCache) -> None:
        cache.put("sha256:vec", {"vector_ref": "embeddings/v1", "dimensions": 4096})
        assert cache.get("sha256:vec") == {"vector_ref": "embeddings/v1", "dimensions": 4096}

    def test_put_overwrites(self, cache: ArtifactCache) -> None:
        cache.put("sha256:vec", {"generation": 1})
        cache.put("sha256:vec", {"generation": 2})
        assert cache.get("sha256:vec") == {"generation": 2}


class TestByteEntries:
    def test_miss_returns_none(self, cache: ArtifactCache) -> None:
        assert cache.get_bytes("sha256:absent") is None

    def test_put_then_get_bytes(self, cache: ArtifactCache) -> None:
        cache.put_bytes("sha256:raw", b"\x00\x01")
        assert cache.get_bytes("sha256:raw") == b"\x00\x01"


class TestStats:
    def test_counters_track_hits_and_misses(self, cache: ArtifactCache) -> None:
        assert cache.stats() == CacheStats(hits=0, misses=0)
        cache.get("sha256:a")  # miss
        cache.put("sha256:a", {"x": 1})
        cache.get("sha256:a")  # hit
        cache.get_bytes("sha256:b")  # miss
        assert cache.stats() == CacheStats(hits=1, misses=2)

    def test_stats_snapshot_is_serializable(self, cache: ArtifactCache) -> None:
        cache.get("sha256:a")
        assert cache.stats().to_dict() == {"hits": 0, "misses": 1}

    def test_put_does_not_change_counters(self, cache: ArtifactCache) -> None:
        cache.put("sha256:a", {"x": 1})
        assert cache.stats() == CacheStats(hits=0, misses=0)


class TestErrors:
    def test_invalid_key_raises_cache_error(self, cache: ArtifactCache) -> None:
        with pytest.raises(CacheError, match="invalid cache key"):
            cache.get("../escape")

    def test_invalid_payload_raises_cache_error(self, cache: ArtifactCache) -> None:
        with pytest.raises(CacheError, match="cannot cache entry"):
            cache.put("sha256:bad", {"oops": {1, 2}})  # type: ignore[dict-item]


class TestSpecKeyComposition:
    def test_composed_embedding_key_is_a_valid_cache_key(
        self, cache: ArtifactCache, store: ArtifactStore
    ) -> None:
        """The SPEC embedding cache key composition must produce usable keys."""
        key = combine_fingerprints(
            "sha256:unit-content",
            "sha256:preprocessing",
            "sha256:model",
            fingerprint({"precision": "float16", "instruction": None}),
        )
        cache.put(key, {"vector_ref": "embeddings/v1"})
        entry = cache.get(key)
        assert entry == {"vector_ref": "embeddings/v1"}
        assert cache.stats().hits == 1
