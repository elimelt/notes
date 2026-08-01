"""Deterministic character n-gram feature-hashing provider.

Role: this is the SPEC's "compact baseline" — the cheap model that the
qualification benchmark compares real embedding models against — and the
dependency-free test double for the embedding stage in tests and CI. It needs
only NumPy and the standard library.

Algorithm (versioned as :data:`ALGORITHM_VERSION`): the input text (with the
configured instruction prefix, if any, and truncated to ``max_input_tokens``
whitespace tokens) is decomposed into character n-grams for n in 3..5. Each
n-gram is hashed with :func:`hashlib.blake2b` — never Python's builtin
``hash()``, which is salted per process — into one of ``config.dimensions``
buckets, with the digest's low bit choosing the sign (signed feature
hashing). The bucket sums form the raw vector, which is returned
un-normalized (the embedder L2-normalizes when configured) but is
L2-normalizable: only texts with no n-grams (fewer than three characters)
produce a zero vector. The result is identical across processes, platforms,
and NumPy versions.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import numpy as np

from linkdiscovery.fingerprint import fingerprint

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from linkdiscovery.config import EmbeddingConfig

__all__ = ["ALGORITHM_VERSION", "HashingProvider"]

ALGORITHM_VERSION = "hashing-ngram-v1"
"""Version of the hashing algorithm; part of the model fingerprint, so any
change to the n-gram or bucketing scheme must bump it."""

_NGRAM_SIZES = (3, 4, 5)
_DIGEST_SIZE = 8


class HashingProvider:
    """Character n-gram feature hashing behind the ``EmbeddingProvider`` protocol.

    Fully deterministic and CPU-only: the requested device is accepted for
    interface compatibility but ignored, and :attr:`device` always reports
    ``"cpu"``. Tokens are whitespace-delimited words, both for
    :meth:`count_tokens` and for ``max_input_tokens`` truncation.
    """

    def __init__(self, config: EmbeddingConfig, device: str = "cpu") -> None:
        """Configure the hasher from ``config``; ``device`` is ignored (always CPU)."""
        del device  # hashing is pure CPU arithmetic; there is nothing to accelerate
        self._dimensions = config.dimensions
        self._instruction = config.instruction
        self._max_input_tokens = config.max_input_tokens
        # Everything output-affecting, mirroring the SPEC model-fingerprint
        # inputs: identifier, revision (the algorithm version), tokenizer
        # revision, pooling, instruction, dimensions, normalization,
        # precision, and maximum input length.
        self._fingerprint = fingerprint(
            {
                "provider": "hashing",
                "model": "character-ngram-feature-hashing",
                "revision": ALGORITHM_VERSION,
                "tokenizer_revision": "whitespace-v1",
                "pooling": "sum",
                "instruction": config.instruction,
                "dimensions": config.dimensions,
                "normalize": config.normalize,
                "precision": config.precision,
                "max_input_tokens": config.max_input_tokens,
            }
        )

    @property
    def model_fingerprint(self) -> str:
        """Fingerprint over the algorithm version and every output-affecting option."""
        return self._fingerprint

    @property
    def dimensions(self) -> int:
        """Number of hash buckets, i.e. the output dimensionality."""
        return self._dimensions

    @property
    def max_input_tokens(self) -> int | None:
        """Whitespace-token budget from the configuration; ``None`` when unbounded."""
        return self._max_input_tokens

    @property
    def device(self) -> str:
        """Always ``"cpu"``: the hasher has no accelerated path."""
        return "cpu"

    def count_tokens(self, text: str) -> int:
        """Count whitespace-delimited tokens, the unit of this provider's truncation."""
        return len(text.split())

    def _prepare(self, text: str) -> str:
        """Apply the instruction prefix and whitespace-token truncation."""
        combined = f"{self._instruction} {text}" if self._instruction else text
        if self._max_input_tokens is not None:
            tokens = combined.split()
            if len(tokens) > self._max_input_tokens:
                return " ".join(tokens[: self._max_input_tokens])
        return combined

    def _embed_one(self, text: str) -> NDArray[np.float32]:
        """Hash one prepared text into a signed bucket-sum vector."""
        vector = np.zeros(self._dimensions, dtype=np.float32)
        prepared = self._prepare(text)
        for size in _NGRAM_SIZES:
            for start in range(len(prepared) - size + 1):
                gram = prepared[start : start + size].encode("utf-8")
                digest = hashlib.blake2b(gram, digest_size=_DIGEST_SIZE).digest()
                value = int.from_bytes(digest, "big")
                bucket = (value >> 1) % self._dimensions
                vector[bucket] += 1.0 if value & 1 else -1.0
        return vector

    def encode(self, texts: Sequence[str], *, batch_size: int) -> NDArray[np.float32]:
        """Embed ``texts`` into an un-normalized ``(n, dimensions)`` float32 matrix.

        ``batch_size`` is accepted for interface compatibility and ignored:
        hashing has no memory pressure to manage.
        """
        del batch_size
        if not texts:
            return np.zeros((0, self._dimensions), dtype=np.float32)
        return np.stack([self._embed_one(text) for text in texts])
