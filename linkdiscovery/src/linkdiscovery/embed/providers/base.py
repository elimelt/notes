"""The provider protocol and registry for the embedding stage.

An :class:`EmbeddingProvider` is the smallest surface the default embedder
needs from a model backend. Providers return **un-normalized** matrices; the
embedder applies L2 normalization (when configured) so the normalization
policy lives in exactly one place. Everything that affects a provider's
output must be captured by its ``model_fingerprint`` — that string is a
component of every embedding cache key, so an under-specified fingerprint
silently serves stale vectors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from linkdiscovery.embed.providers.hashing import HashingProvider
from linkdiscovery.embed.providers.sentence_transformers import SentenceTransformersProvider
from linkdiscovery.errors import ConfigError

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy as np
    from numpy.typing import NDArray

    from linkdiscovery.config import EmbeddingConfig

__all__ = ["KNOWN_PROVIDERS", "EmbeddingProvider", "create_provider"]

KNOWN_PROVIDERS = ("hashing", "sentence-transformers")
"""Provider names :func:`create_provider` can dispatch to."""


@runtime_checkable
class EmbeddingProvider(Protocol):
    """One embedding model behind a uniform, framework-free surface.

    Contract:

    - :meth:`encode` returns an ``(n, dimensions)`` ``float32`` matrix for
      ``n`` input texts, **not** L2-normalized (the embedder normalizes).
      Texts longer than :attr:`max_input_tokens` are truncated by the
      provider's tokenizer, never rejected.
    - :attr:`model_fingerprint` covers, per the SPEC model policy: model
      identifier, immutable revision, tokenizer revision, pooling method,
      instruction text, output dimension, normalization, precision, and
      maximum input length. Changing any of them changes the fingerprint.
    - :meth:`count_tokens` uses the same tokenizer as :meth:`encode`, so
      truncation accounting is exact.
    - :attr:`device` is the *effective* device the provider computes on
      (for example ``"cpu"`` or ``"mps"``), which may differ from the
      requested device only for providers that are device-independent.

    Note: ``runtime_checkable`` verifies member presence, not signatures.
    """

    def encode(self, texts: Sequence[str], *, batch_size: int) -> NDArray[np.float32]:
        """Embed ``texts``, processing at most ``batch_size`` texts at once."""
        ...

    @property
    def model_fingerprint(self) -> str:
        """Fingerprint of every output-affecting model property (see class docs)."""
        ...

    @property
    def dimensions(self) -> int:
        """Output dimensionality of :meth:`encode` results."""
        ...

    @property
    def max_input_tokens(self) -> int | None:
        """Token budget beyond which inputs are truncated; ``None`` when unbounded."""
        ...

    def count_tokens(self, text: str) -> int:
        """Count ``text``'s tokens with the model's own tokenizer."""
        ...

    @property
    def device(self) -> str:
        """The effective compute device (for example ``"cpu"``, ``"mps"``)."""
        ...


def create_provider(config: EmbeddingConfig, *, device: str) -> EmbeddingProvider:
    """Build the provider named by ``config.provider`` for ``device``.

    Dispatches on the provider name (:data:`KNOWN_PROVIDERS`); an unknown
    name raises :class:`~linkdiscovery.errors.ConfigError` listing the known
    providers. Provider construction may itself raise
    :class:`~linkdiscovery.errors.EmbeddingRuntimeError` (missing optional
    dependency, model load failure, unsupported precision on ``device``).
    """
    if config.provider == "hashing":
        return HashingProvider(config, device)
    if config.provider == "sentence-transformers":
        return SentenceTransformersProvider(config, device)
    known = ", ".join(repr(name) for name in KNOWN_PROVIDERS)
    raise ConfigError(f"unknown embedding provider {config.provider!r}; expected one of: {known}")
