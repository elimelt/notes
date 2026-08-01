"""Tests for :class:`DefaultEmbedder`: caching, batching, qualification, artifacts."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pytest
from numpy.typing import NDArray

from linkdiscovery.artifacts import ArtifactCache, ArtifactStore
from linkdiscovery.config import EmbeddingConfig
from linkdiscovery.contracts.base import ArtifactHeader
from linkdiscovery.contracts.units import (
    ProcessedCorpus,
    ProcessedDocument,
    RegionKind,
    SemanticUnit,
    Span,
)
from linkdiscovery.embed import DefaultEmbedder, HashingProvider, load_vector_table
from linkdiscovery.embed.providers.base import EmbeddingProvider
from linkdiscovery.errors import EmbeddingRuntimeError
from linkdiscovery.fingerprint import fingerprint

# --------------------------------------------------------------------------
# Fixtures and fakes
# --------------------------------------------------------------------------


def make_config(**overrides: object) -> EmbeddingConfig:
    values: dict[str, object] = {
        "provider": "hashing",
        "model": "baseline",
        "revision": "v1",
        "dimensions": 16,
        "normalize": True,
        "device_preference": ("cpu",),
        "precision": "float32",
        "batch_size": 4,
    }
    values.update(overrides)
    return EmbeddingConfig(**values)  # type: ignore[arg-type]


def make_unit(doc_id: str, unit_id: str, text: str) -> SemanticUnit:
    return SemanticUnit(
        id=unit_id,
        document_id=doc_id,
        view="section",
        section_path=(),
        region_kinds=(RegionKind.PROSE,),
        source_spans=(Span(0, len(text)),),
        text=text,
        token_count=len(text.split()),
        content_hash=fingerprint(text),
    )


def make_corpus(
    documents: dict[str, dict[str, str]],
    preprocessing_fingerprint: str = "sha256:pre",
) -> ProcessedCorpus:
    """Build a corpus from ``{doc_id: {unit_id: text}}``."""
    header = ArtifactHeader(
        schema_version=1,
        run_id="run-1",
        corpus_id="corpus-1",
        created_at="2026-07-31T00:00:00+00:00",
        config_fingerprint="sha256:cfg",
        producer_version="test",
    )
    return ProcessedCorpus(
        header=header,
        preprocessing_fingerprint=preprocessing_fingerprint,
        documents=tuple(
            ProcessedDocument(
                document_id=doc_id,
                revision="rev-1",
                units=tuple(make_unit(doc_id, unit_id, text) for unit_id, text in units.items()),
            )
            for doc_id, units in documents.items()
        ),
    )


def simple_corpus() -> ProcessedCorpus:
    return make_corpus(
        {
            "doc-a": {
                "doc-a:u0": "alpha beta gamma delta epsilon",
                "doc-a:u1": "systems scheduling fairness theory",
            },
            "doc-b": {"doc-b:u0": "distributed consensus and replication"},
        }
    )


class CountingProvider:
    """Delegating provider wrapper that records every ``encode`` call."""

    def __init__(self, inner: EmbeddingProvider, calls: list[list[str]]) -> None:
        self._inner = inner
        self.calls = calls

    def encode(self, texts: Sequence[str], *, batch_size: int) -> NDArray[np.float32]:
        self.calls.append(list(texts))
        return self._inner.encode(texts, batch_size=batch_size)

    @property
    def model_fingerprint(self) -> str:
        return self._inner.model_fingerprint

    @property
    def dimensions(self) -> int:
        return self._inner.dimensions

    @property
    def max_input_tokens(self) -> int | None:
        return self._inner.max_input_tokens

    def count_tokens(self, text: str) -> int:
        return self._inner.count_tokens(text)

    @property
    def device(self) -> str:
        return self._inner.device


class OomProvider:
    """Deterministic provider that OOMs on batches larger than 2 after the first call."""

    def __init__(self, dimensions: int) -> None:
        self._dimensions = dimensions
        self.successful_texts: list[str] = []
        self._call_count = 0

    def encode(self, texts: Sequence[str], *, batch_size: int) -> NDArray[np.float32]:
        self._call_count += 1
        if self._call_count > 1 and len(texts) > 2:
            raise RuntimeError("MPS backend out of memory")
        self.successful_texts.extend(texts)
        matrix = np.zeros((len(texts), self._dimensions), dtype=np.float32)
        for row, text in enumerate(texts):
            matrix[row, 0] = float(len(text))
            matrix[row, 1] = 1.0
        return matrix

    @property
    def model_fingerprint(self) -> str:
        return "sha256:oom-fake-model"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def max_input_tokens(self) -> int | None:
        return None

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    @property
    def device(self) -> str:
        return "cpu"


class FailingProvider(OomProvider):
    """Provider whose encode always fails with a non-OOM error."""

    def encode(self, texts: Sequence[str], *, batch_size: int) -> NDArray[np.float32]:
        raise ValueError("tokenizer exploded")


def noop_prober(device: str) -> None:
    del device


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


class TestEmbedBasics:
    def test_index_structure_and_round_trip(
        self, store: ArtifactStore, cache: ArtifactCache
    ) -> None:
        corpus = simple_corpus()
        config = make_config()
        index = DefaultEmbedder(store, run_id="run-x").embed(corpus, config, cache)

        assert index.header.run_id == "run-x"
        assert index.header.corpus_id == "corpus-1"
        assert index.header.config_fingerprint == config.fingerprint()
        assert index.dimensions == 16
        assert index.normalized is True
        assert index.dtype == "float32"
        assert index.runtime.device == "cpu"
        assert index.runtime.requested_batch_size == 4
        assert index.runtime.effective_batch_size == 4
        assert index.runtime.fallback_events == ()
        assert index.runtime.failed_unit_ids == ()
        assert index.runtime.wall_time_seconds >= 0.0

        # Deterministic order: by document id, then unit id.
        assert [record.unit_id for record in index.records] == [
            "doc-a:u0",
            "doc-a:u1",
            "doc-b:u0",
        ]
        table = load_vector_table(store, index)
        assert table.unit_ids == ("doc-a:u0", "doc-a:u1", "doc-b:u0")
        np.testing.assert_allclose(np.linalg.norm(table.matrix, axis=1), np.ones(3), rtol=1e-5)

    def test_vectors_match_provider_output_normalized(
        self, store: ArtifactStore, cache: ArtifactCache
    ) -> None:
        corpus = simple_corpus()
        config = make_config()
        index = DefaultEmbedder(store).embed(corpus, config, cache)
        table = load_vector_table(store, index)
        provider = HashingProvider(config)
        raw = provider.encode(["alpha beta gamma delta epsilon"], batch_size=1)
        expected = raw[0] / np.linalg.norm(raw[0])
        np.testing.assert_allclose(table.vector_for_unit("doc-a:u0"), expected, rtol=1e-5)

    def test_normalize_false_keeps_raw_vectors(
        self, store: ArtifactStore, cache: ArtifactCache
    ) -> None:
        corpus = simple_corpus()
        config = make_config(normalize=False)
        index = DefaultEmbedder(store).embed(corpus, config, cache)
        assert index.normalized is False
        table = load_vector_table(store, index)
        assert float(np.linalg.norm(table.vector_for_unit("doc-a:u0"))) > 1.5

    def test_float16_precision_sets_storage_dtype(
        self, store: ArtifactStore, cache: ArtifactCache
    ) -> None:
        index = DefaultEmbedder(store).embed(
            simple_corpus(), make_config(precision="float16"), cache
        )
        assert index.dtype == "float16"
        assert all(record.dtype == "float16" for record in index.records)
        table = load_vector_table(store, index)  # widens back to float32
        assert table.matrix.dtype == np.float32

    def test_auto_batch_size_is_resolved(self, store: ArtifactStore, cache: ArtifactCache) -> None:
        index = DefaultEmbedder(store).embed(simple_corpus(), make_config(batch_size="auto"), cache)
        assert index.runtime.requested_batch_size == "auto"
        assert index.runtime.effective_batch_size == 16  # cpu auto default

    def test_token_throughput_reported(self, store: ArtifactStore, cache: ArtifactCache) -> None:
        index = DefaultEmbedder(store).embed(simple_corpus(), make_config(), cache)
        assert index.runtime.token_throughput is not None
        assert index.runtime.token_throughput > 0

    def test_empty_corpus_is_a_valid_empty_index(
        self, store: ArtifactStore, cache: ArtifactCache
    ) -> None:
        corpus = make_corpus({})
        index = DefaultEmbedder(store).embed(corpus, make_config(), cache)
        assert index.records == ()
        assert index.dimensions == 16
        assert index.runtime.failed_unit_ids == ()
        table = load_vector_table(store, index)
        assert len(table) == 0


class TestCaching:
    def test_second_embed_hits_cache_without_encoding(
        self, store: ArtifactStore, cache: ArtifactCache
    ) -> None:
        corpus = simple_corpus()
        config = make_config()
        calls: list[list[str]] = []

        def factory(cfg: EmbeddingConfig, device: str) -> EmbeddingProvider:
            return CountingProvider(HashingProvider(cfg, device), calls)

        embedder = DefaultEmbedder(store, provider_factory=factory, device_prober=noop_prober)
        first = embedder.embed(corpus, config, cache)
        assert sum(len(batch) for batch in calls) == 3

        calls.clear()
        second = embedder.embed(corpus, config, cache)
        assert calls == []  # provider.encode called zero times
        table_first = load_vector_table(store, first)
        table_second = load_vector_table(store, second)
        np.testing.assert_array_equal(table_first.matrix, table_second.matrix)

    @pytest.mark.parametrize(
        ("corpus_change", "config_overrides"),
        [
            pytest.param("sha256:other-preprocessing", {}, id="preprocessing-fingerprint"),
            pytest.param(None, {"instruction": "Represent:"}, id="model-fingerprint"),
            pytest.param(None, {"precision": "float16"}, id="precision"),
        ],
    )
    def test_output_affecting_changes_invalidate_cache(
        self,
        store: ArtifactStore,
        cache: ArtifactCache,
        corpus_change: str | None,
        config_overrides: dict[str, object],
    ) -> None:
        documents = {"doc-a": {"doc-a:u0": "alpha beta gamma delta"}}
        calls: list[list[str]] = []

        def factory(cfg: EmbeddingConfig, device: str) -> EmbeddingProvider:
            return CountingProvider(HashingProvider(cfg, device), calls)

        embedder = DefaultEmbedder(store, provider_factory=factory, device_prober=noop_prober)
        embedder.embed(make_corpus(documents), make_config(), cache)

        calls.clear()
        changed_corpus = (
            make_corpus(documents, preprocessing_fingerprint=corpus_change)
            if corpus_change is not None
            else make_corpus(documents)
        )
        embedder.embed(changed_corpus, make_config(**config_overrides), cache)
        assert sum(len(batch) for batch in calls) == 1  # re-encoded, not served stale

    def test_batch_size_and_device_do_not_invalidate_cache(
        self, store: ArtifactStore, cache: ArtifactCache
    ) -> None:
        corpus = simple_corpus()
        calls: list[list[str]] = []

        def factory(cfg: EmbeddingConfig, device: str) -> EmbeddingProvider:
            return CountingProvider(HashingProvider(cfg, device), calls)

        embedder = DefaultEmbedder(store, provider_factory=factory, device_prober=noop_prober)
        embedder.embed(corpus, make_config(batch_size=4), cache)
        calls.clear()
        embedder.embed(corpus, make_config(batch_size=1, device_preference=("mps", "cpu")), cache)
        assert calls == []

    def test_corrupt_cache_entry_is_a_miss_with_warning(
        self, store: ArtifactStore, cache: ArtifactCache
    ) -> None:
        corpus = make_corpus({"doc-a": {"doc-a:u0": "alpha beta gamma delta"}})
        config = make_config()
        embedder = DefaultEmbedder(store, device_prober=noop_prober)
        embedder.embed(corpus, config, cache)

        # Overwrite the single cached vector with a wrong-sized payload.
        cache_dir = store.root / "cache"
        entries = list(cache_dir.iterdir())
        assert len(entries) == 1
        entries[0].write_bytes(b"\x00" * 8)  # 2 floats instead of 16

        second = embedder.embed(corpus, config, cache)
        assert any("treating as a miss" in warning for warning in second.runtime.warnings)
        table = load_vector_table(store, second)
        np.testing.assert_allclose(np.linalg.norm(table.matrix, axis=1), [1.0], rtol=1e-5)


class TestRuntimeBehavior:
    def test_oom_adaptive_batching_records_effective_batch(
        self, store: ArtifactStore, cache: ArtifactCache
    ) -> None:
        documents = {"doc-a": {f"doc-a:u{i}": f"text number {i} with words" for i in range(8)}}
        corpus = make_corpus(documents)
        provider = OomProvider(dimensions=16)

        def factory(cfg: EmbeddingConfig, device: str) -> EmbeddingProvider:
            return provider

        embedder = DefaultEmbedder(store, provider_factory=factory, device_prober=noop_prober)
        index = embedder.embed(corpus, make_config(batch_size=4), cache)

        assert index.runtime.effective_batch_size == 2
        assert index.runtime.requested_batch_size == 4
        assert any("4->2" in event for event in index.runtime.fallback_events)
        # Completed batches were never re-encoded: every text exactly once.
        expected = [corpus.documents[0].units[i].text for i in range(8)]
        assert sorted(provider.successful_texts) == sorted(expected)
        assert len(provider.successful_texts) == len(set(provider.successful_texts))

    def test_device_qualification_fallback_recorded(
        self, store: ArtifactStore, cache: ArtifactCache
    ) -> None:
        def factory(cfg: EmbeddingConfig, device: str) -> EmbeddingProvider:
            if device == "mps":
                raise RuntimeError("mps kernel missing")
            return HashingProvider(cfg, device)

        embedder = DefaultEmbedder(store, provider_factory=factory)
        config = make_config(device_preference=("mps", "cpu"))
        index = embedder.embed(simple_corpus(), config, cache)
        assert index.runtime.device == "cpu"
        assert any(event.startswith("mps unavailable: ") for event in index.runtime.fallback_events)

    def test_no_device_qualifies_raises(self, store: ArtifactStore, cache: ArtifactCache) -> None:
        def factory(cfg: EmbeddingConfig, device: str) -> EmbeddingProvider:
            raise RuntimeError(f"{device} is broken")

        embedder = DefaultEmbedder(store, provider_factory=factory)
        with pytest.raises(EmbeddingRuntimeError, match="no device"):
            embedder.embed(simple_corpus(), make_config(), cache)

    def test_zero_vector_units_warn_and_stay_zero(
        self, store: ArtifactStore, cache: ArtifactCache
    ) -> None:
        corpus = make_corpus(
            {"doc-a": {"doc-a:tiny": "ab", "doc-a:u1": "regular length text here"}}
        )
        index = DefaultEmbedder(store, device_prober=noop_prober).embed(
            corpus, make_config(), cache
        )
        assert any("doc-a:tiny" in warning for warning in index.runtime.warnings)
        table = load_vector_table(store, index)
        np.testing.assert_array_equal(
            table.vector_for_unit("doc-a:tiny"), np.zeros(16, dtype=np.float32)
        )
        np.testing.assert_allclose(
            np.linalg.norm(table.vector_for_unit("doc-a:u1")), 1.0, rtol=1e-5
        )

    def test_truncation_count(self, store: ArtifactStore, cache: ArtifactCache) -> None:
        corpus = make_corpus(
            {
                "doc-a": {
                    "doc-a:long": " ".join(f"word{i}" for i in range(20)),
                    "doc-a:short": "just three words",
                }
            }
        )
        config = make_config(max_input_tokens=5)
        index = DefaultEmbedder(store, device_prober=noop_prober).embed(corpus, config, cache)
        assert index.runtime.truncation_count == 1

    def test_irrecoverable_failure_names_the_unit(
        self, store: ArtifactStore, cache: ArtifactCache
    ) -> None:
        provider = FailingProvider(dimensions=16)

        def factory(cfg: EmbeddingConfig, device: str) -> EmbeddingProvider:
            return provider

        embedder = DefaultEmbedder(store, provider_factory=factory, device_prober=noop_prober)
        with pytest.raises(EmbeddingRuntimeError, match="doc-a:u0"):
            embedder.embed(simple_corpus(), make_config(), cache)

    def test_oom_exhaustion_names_the_first_unencoded_unit(
        self, store: ArtifactStore, cache: ArtifactCache
    ) -> None:
        class AlwaysOom(OomProvider):
            def encode(self, texts: Sequence[str], *, batch_size: int) -> NDArray[np.float32]:
                raise MemoryError("insufficient memory")

        provider = AlwaysOom(dimensions=16)

        def factory(cfg: EmbeddingConfig, device: str) -> EmbeddingProvider:
            return provider

        embedder = DefaultEmbedder(store, provider_factory=factory, device_prober=noop_prober)
        with pytest.raises(EmbeddingRuntimeError, match="doc-a:u0"):
            embedder.embed(simple_corpus(), make_config(), cache)
