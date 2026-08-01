"""Embedding providers: the model boundary behind the default embedder.

A provider owns one embedding model (or algorithm) and exposes it through the
:class:`~linkdiscovery.embed.providers.base.EmbeddingProvider` protocol:
un-normalized ``float32`` matrices in, plus the model fingerprint and token
accounting the embedder needs for caching and runtime reports. Providers are
selected by :func:`~linkdiscovery.embed.providers.base.create_provider` from
``EmbeddingConfig.provider``.
"""

from linkdiscovery.embed.providers.base import EmbeddingProvider, create_provider
from linkdiscovery.embed.providers.hashing import HashingProvider
from linkdiscovery.embed.providers.sentence_transformers import SentenceTransformersProvider

__all__ = [
    "EmbeddingProvider",
    "HashingProvider",
    "SentenceTransformersProvider",
    "create_provider",
]
