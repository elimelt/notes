"""Tests for the sentence-transformers provider against a real (tiny) model.

The whole module is skipped when ``sentence_transformers`` is not installed
(install the ``embeddings`` extra). Tests that load a model additionally
require ``LINKDISCOVERY_ALLOW_MODEL_DOWNLOAD=1`` in the environment, because
the first run downloads the model from the Hugging Face Hub.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("sentence_transformers")

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
from linkdiscovery.embed import DefaultEmbedder, load_vector_table
from linkdiscovery.embed.providers.sentence_transformers import (
    SentenceTransformersProvider,
)
from linkdiscovery.errors import EmbeddingRuntimeError
from linkdiscovery.fingerprint import fingerprint

requires_download = pytest.mark.skipif(
    os.environ.get("LINKDISCOVERY_ALLOW_MODEL_DOWNLOAD") != "1",
    reason="set LINKDISCOVERY_ALLOW_MODEL_DOWNLOAD=1 to run tests that download a model",
)

# Tiny (~90 MB), well-known, 384-dimensional model kept only for CI.
TINY_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TINY_DIMS = 384


def make_config(**overrides: object) -> EmbeddingConfig:
    values: dict[str, object] = {
        "provider": "sentence-transformers",
        "model": TINY_MODEL,
        "revision": "main",
        "dimensions": TINY_DIMS,
        "normalize": True,
        "device_preference": ("cpu",),
        "precision": "float32",
        "batch_size": 8,
    }
    values.update(overrides)
    return EmbeddingConfig(**values)  # type: ignore[arg-type]


@requires_download
class TestSentenceTransformersProvider:
    @pytest.fixture(scope="class")
    def provider(self) -> SentenceTransformersProvider:
        return SentenceTransformersProvider(make_config(), "cpu")

    def test_encode_shape_and_dtype(self, provider: SentenceTransformersProvider) -> None:
        matrix = provider.encode(["hello world", "embedding models"], batch_size=2)
        assert matrix.shape == (2, TINY_DIMS)
        assert matrix.dtype == np.float32

    def test_output_is_not_normalized_by_provider(
        self, provider: SentenceTransformersProvider
    ) -> None:
        matrix = provider.encode(["a fairly ordinary sentence"], batch_size=1)
        assert not np.isclose(float(np.linalg.norm(matrix[0])), 1.0, atol=1e-3)

    def test_device_and_limits(self, provider: SentenceTransformersProvider) -> None:
        assert provider.device == "cpu"
        assert provider.dimensions == TINY_DIMS
        assert provider.max_input_tokens is not None
        assert provider.max_input_tokens > 0

    def test_count_tokens_uses_model_tokenizer(
        self, provider: SentenceTransformersProvider
    ) -> None:
        short = provider.count_tokens("word")
        long = provider.count_tokens("a much longer sentence with many more words in it")
        assert 0 < short < long

    def test_fingerprint_uses_resolved_revision(
        self, provider: SentenceTransformersProvider
    ) -> None:
        # "main" must be resolved to a commit hash: fingerprinting the config
        # revision verbatim would make revision drift undetectable.
        config = make_config()
        verbatim = fingerprint(
            {
                "provider": "sentence-transformers",
                "model": config.model,
                "revision": "main",
                "tokenizer_revision": "main",
                "pooling": "mean",
                "instruction": None,
                "dimensions": config.dimensions,
                "normalize": config.normalize,
                "precision": config.precision,
                "max_input_tokens": provider.max_input_tokens,
            }
        )
        assert provider.model_fingerprint != verbatim

    def test_instruction_changes_fingerprint(self, provider: SentenceTransformersProvider) -> None:
        instructed = SentenceTransformersProvider(
            make_config(instruction="Represent the document for retrieval:"), "cpu"
        )
        assert instructed.model_fingerprint != provider.model_fingerprint

    def test_matryoshka_truncation(self) -> None:
        truncated = SentenceTransformersProvider(make_config(dimensions=128), "cpu")
        matrix = truncated.encode(["truncate me"], batch_size=1)
        assert matrix.shape == (1, 128)
        assert truncated.dimensions == 128

    def test_dimensions_larger_than_native_raise(self) -> None:
        with pytest.raises(EmbeddingRuntimeError, match="native width"):
            SentenceTransformersProvider(make_config(dimensions=100_000), "cpu")


@requires_download
class TestEndToEnd:
    def test_default_embedder_with_real_model(self, tmp_path: Path) -> None:
        store = ArtifactStore(tmp_path / "artifacts")
        cache = ArtifactCache(store)
        header = ArtifactHeader(
            schema_version=1,
            run_id="run-st",
            corpus_id="corpus-st",
            created_at="2026-07-31T00:00:00+00:00",
            config_fingerprint="sha256:cfg",
            producer_version="test",
        )
        text = "Fair scheduling balances throughput and latency across tenants."
        corpus = ProcessedCorpus(
            header=header,
            preprocessing_fingerprint="sha256:pre",
            documents=(
                ProcessedDocument(
                    document_id="doc-a",
                    revision="rev-1",
                    units=(
                        SemanticUnit(
                            id="doc-a:u0",
                            document_id="doc-a",
                            view="section",
                            section_path=(),
                            region_kinds=(RegionKind.PROSE,),
                            source_spans=(Span(0, len(text)),),
                            text=text,
                            token_count=10,
                            content_hash=fingerprint(text),
                        ),
                    ),
                ),
            ),
        )
        index = DefaultEmbedder(store).embed(corpus, make_config(), cache)
        assert index.dimensions == TINY_DIMS
        assert index.runtime.device == "cpu"
        table = load_vector_table(store, index)
        np.testing.assert_allclose(
            float(np.linalg.norm(table.vector_for_unit("doc-a:u0"))), 1.0, rtol=1e-4
        )
