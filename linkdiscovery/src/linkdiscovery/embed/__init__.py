"""Embedding stage: providers, runtime qualification, caching, vector storage.

``vectors`` defines the storage boundary shared with the candidate stage; the
remaining modules implement the :class:`~linkdiscovery.interfaces.Embedder`
protocol: ``providers`` wraps embedding models behind one protocol,
``runtime`` implements device qualification and adaptive batching, and
``embedder`` ties them together as :class:`DefaultEmbedder`.
"""

from linkdiscovery.embed.embedder import DefaultEmbedder
from linkdiscovery.embed.providers import (
    EmbeddingProvider,
    HashingProvider,
    SentenceTransformersProvider,
    create_provider,
)
from linkdiscovery.embed.runtime import (
    default_is_oom,
    encode_adaptively,
    qualify_device,
    resolve_batch_size,
)
from linkdiscovery.embed.vectors import (
    VECTOR_GROUP,
    VectorTable,
    load_vector_table,
    make_vector_ref,
    save_vector_table,
)

__all__ = [
    "VECTOR_GROUP",
    "DefaultEmbedder",
    "EmbeddingProvider",
    "HashingProvider",
    "SentenceTransformersProvider",
    "VectorTable",
    "create_provider",
    "default_is_oom",
    "encode_adaptively",
    "load_vector_table",
    "make_vector_ref",
    "qualify_device",
    "resolve_batch_size",
    "save_vector_table",
]
