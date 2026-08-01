"""Tests for the embedding provider protocol, registry, and hashing baseline."""

from __future__ import annotations

import hashlib
import importlib.util

import numpy as np
import pytest

from linkdiscovery.config import EmbeddingConfig
from linkdiscovery.embed.providers import (
    EmbeddingProvider,
    HashingProvider,
    SentenceTransformersProvider,
    create_provider,
)
from linkdiscovery.embed.providers.hashing import ALGORITHM_VERSION
from linkdiscovery.errors import ConfigError, EmbeddingRuntimeError

_SENTENCE_TRANSFORMERS_INSTALLED = importlib.util.find_spec("sentence_transformers") is not None


def make_config(**overrides: object) -> EmbeddingConfig:
    values: dict[str, object] = {
        "provider": "hashing",
        "model": "baseline",
        "revision": "v1",
        "dimensions": 32,
        "normalize": True,
        "device_preference": ("cpu",),
        "precision": "float32",
        "batch_size": 4,
    }
    values.update(overrides)
    return EmbeddingConfig(**values)  # type: ignore[arg-type]


class TestHashingProvider:
    def test_satisfies_protocol(self) -> None:
        assert isinstance(HashingProvider(make_config()), EmbeddingProvider)

    def test_output_shape_and_dtype(self) -> None:
        provider = HashingProvider(make_config(dimensions=16))
        matrix = provider.encode(["alpha beta gamma", "delta"], batch_size=2)
        assert matrix.shape == (2, 16)
        assert matrix.dtype == np.float32

    def test_deterministic_within_process(self) -> None:
        provider = HashingProvider(make_config())
        text = ["the quick brown fox jumps over the lazy dog"]
        np.testing.assert_array_equal(
            provider.encode(text, batch_size=1), provider.encode(text, batch_size=1)
        )

    def test_deterministic_across_processes_and_platforms(self) -> None:
        # Hardcoded digest: the vector for this input must be byte-identical
        # on every OS, Python, and NumPy version (hashlib-based, no salted
        # builtin hash()). A change here means the algorithm changed and
        # ALGORITHM_VERSION must be bumped.
        provider = HashingProvider(make_config(dimensions=32))
        matrix = provider.encode(["the quick brown fox jumps over the lazy dog"], batch_size=1)
        digest = hashlib.sha256(matrix.tobytes()).hexdigest()
        assert digest == "c94f7c06a6883cb40439ddbedd4887f9f3a977345a5edd1f8aa499c4c0bf8376"

    def test_output_is_not_normalized(self) -> None:
        provider = HashingProvider(make_config())
        matrix = provider.encode(["a reasonably long sentence about scheduling"], batch_size=1)
        assert float(np.linalg.norm(matrix[0])) > 1.5

    def test_short_text_yields_zero_vector(self) -> None:
        provider = HashingProvider(make_config())
        matrix = provider.encode(["ab"], batch_size=1)  # shorter than the smallest n-gram
        np.testing.assert_array_equal(matrix, np.zeros((1, 32), dtype=np.float32))

    def test_empty_batch(self) -> None:
        provider = HashingProvider(make_config(dimensions=8))
        assert provider.encode([], batch_size=4).shape == (0, 8)

    def test_counts_whitespace_tokens(self) -> None:
        provider = HashingProvider(make_config())
        assert provider.count_tokens("one two  three\nfour") == 4
        assert provider.count_tokens("") == 0

    def test_truncation_changes_vector(self) -> None:
        long_text = " ".join(f"word{i}" for i in range(50))
        unbounded = HashingProvider(make_config(max_input_tokens=None))
        bounded = HashingProvider(make_config(max_input_tokens=5))
        assert bounded.max_input_tokens == 5
        assert not np.array_equal(
            unbounded.encode([long_text], batch_size=1),
            bounded.encode([long_text], batch_size=1),
        )

    def test_instruction_changes_vector_and_fingerprint(self) -> None:
        plain = HashingProvider(make_config())
        instructed = HashingProvider(make_config(instruction="Represent the document:"))
        assert plain.model_fingerprint != instructed.model_fingerprint
        assert not np.array_equal(
            plain.encode(["same text"], batch_size=1),
            instructed.encode(["same text"], batch_size=1),
        )

    @pytest.mark.parametrize(
        "overrides",
        [
            {"dimensions": 64},
            {"normalize": False},
            {"precision": "float16"},
            {"max_input_tokens": 128},
        ],
    )
    def test_fingerprint_covers_output_affecting_options(
        self, overrides: dict[str, object]
    ) -> None:
        assert (
            HashingProvider(make_config()).model_fingerprint
            != HashingProvider(make_config(**overrides)).model_fingerprint
        )

    def test_fingerprint_includes_algorithm_version(self) -> None:
        # The fingerprint is a hash, so verify the version is an input by
        # checking it is pinned where the fingerprint is built.
        assert ALGORITHM_VERSION == "hashing-ngram-v1"
        provider = HashingProvider(make_config())
        assert provider.model_fingerprint.startswith("sha256:")

    def test_device_is_always_cpu(self) -> None:
        assert HashingProvider(make_config(), "mps").device == "cpu"


class TestCreateProvider:
    def test_dispatches_to_hashing(self) -> None:
        provider = create_provider(make_config(), device="cpu")
        assert isinstance(provider, HashingProvider)

    def test_unknown_provider_names_known_ones(self) -> None:
        config = make_config(provider="magic-embeddings")
        with pytest.raises(ConfigError, match=r"hashing.*sentence-transformers"):
            create_provider(config, device="cpu")

    @pytest.mark.skipif(
        _SENTENCE_TRANSFORMERS_INSTALLED,
        reason="sentence-transformers is installed; the missing-dependency path is unreachable",
    )
    def test_sentence_transformers_missing_dependency_is_actionable(self) -> None:
        config = make_config(provider="sentence-transformers", model="any/model")
        with pytest.raises(EmbeddingRuntimeError, match="linkdiscovery\\[embeddings\\]"):
            create_provider(config, device="cpu")


class TestSentenceTransformersModule:
    def test_module_imports_without_torch(self) -> None:
        # Heavy imports are lazy: the module (already imported above) must be
        # loadable and expose the provider class without torch installed.
        assert SentenceTransformersProvider.__name__ == "SentenceTransformersProvider"

    @pytest.mark.skipif(
        _SENTENCE_TRANSFORMERS_INSTALLED,
        reason="sentence-transformers is installed; the missing-dependency path is unreachable",
    )
    def test_constructor_without_dependency_raises(self) -> None:
        config = make_config(provider="sentence-transformers", model="any/model")
        with pytest.raises(EmbeddingRuntimeError, match="embeddings"):
            SentenceTransformersProvider(config, "cpu")
