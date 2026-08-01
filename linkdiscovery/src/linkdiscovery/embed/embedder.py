"""The default :class:`~linkdiscovery.interfaces.Embedder` implementation.

``DefaultEmbedder.embed`` ties the embedding stage together: qualify a device
from the configured preference order (with a real encoding probe), reuse
cached per-unit vectors, encode the misses with adaptive batching, normalize,
persist one content-addressed vector table, and return an
:class:`~linkdiscovery.contracts.embeddings.EmbeddingIndex` whose
:class:`~linkdiscovery.contracts.embeddings.RuntimeReport` records exactly
what happened (device, fallbacks, batch sizes, truncations, warnings).

Cache-key policy (SPEC "Embedding cache"): one unit's key combines the unit
content hash, the preprocessing fingerprint, the provider model fingerprint,
and a fingerprint of the output-affecting runtime options (precision,
normalize, instruction, max_input_tokens). Device and batch size are
deliberately **excluded**: they change how vectors are computed, not what the
vectors are — the same model at the same precision must produce equivalent
output on MPS and CPU at any batch size, so including them would only
destroy cache reuse without adding correctness.

Failure policy: this embedder is strict — a unit whose encoding fails
irrecoverably raises :class:`~linkdiscovery.errors.EmbeddingRuntimeError`
naming the unit. Permissive mode (emitting a complete artifact with explicit
omissions in ``failed_unit_ids``) is a later pipeline-level concern.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.contracts.embeddings import (
    SCHEMA_VERSION,
    EmbeddingIndex,
    EmbeddingRecord,
    RuntimeReport,
)
from linkdiscovery.embed.providers.base import EmbeddingProvider, create_provider
from linkdiscovery.embed.runtime import (
    default_is_oom,
    encode_adaptively,
    qualify_device,
    resolve_batch_size,
)
from linkdiscovery.embed.vectors import make_vector_ref, save_vector_table
from linkdiscovery.errors import EmbeddingRuntimeError
from linkdiscovery.fingerprint import combine_fingerprints, fingerprint

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from numpy.typing import NDArray

    from linkdiscovery.artifacts.cache import ArtifactCache
    from linkdiscovery.artifacts.store import ArtifactStore
    from linkdiscovery.config import EmbeddingConfig
    from linkdiscovery.contracts.units import ProcessedCorpus, SemanticUnit

__all__ = ["DefaultEmbedder"]

_PROBE_TEXTS = (
    "A short representative probe sentence.",
    "A second probe text, somewhat longer, that exercises the device end to end "
    "with ordinary prose.",
    "Third probe: code_identifiers, punctuation — and a few unusual tokens.",
)

_FLOAT32_BYTES = np.dtype(np.float32).itemsize


def _default_provider_factory(config: EmbeddingConfig, device: str) -> EmbeddingProvider:
    """Adapt :func:`create_provider`'s keyword-only ``device`` to a plain callable."""
    return create_provider(config, device=device)


def _collect_units(corpus: ProcessedCorpus) -> tuple[SemanticUnit, ...]:
    """All units of all documents in deterministic order: document id, then unit id."""
    return tuple(
        sorted(
            (unit for document in corpus.documents for unit in document.units),
            key=lambda unit: (unit.document_id, unit.id),
        )
    )


def _runtime_options_fingerprint(config: EmbeddingConfig) -> str:
    """Fingerprint of the output-affecting runtime options only.

    Device and batch size are excluded on purpose: they must not change the
    embedding values (see module docstring), so keying on them would
    invalidate perfectly reusable vectors.
    """
    return fingerprint(
        {
            "precision": config.precision,
            "normalize": config.normalize,
            "instruction": config.instruction,
            "max_input_tokens": config.max_input_tokens,
        }
    )


def _normalize_rows(
    matrix: NDArray[np.float32], unit_ids: Sequence[str]
) -> tuple[NDArray[np.float32], tuple[str, ...]]:
    """L2-normalize each row; zero rows are left as zeros and reported by unit id."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    zero_mask = norms[:, 0] == 0.0
    zero_ids = tuple(
        unit_id for unit_id, is_zero in zip(unit_ids, zero_mask.tolist(), strict=True) if is_zero
    )
    safe = np.where(zero_mask[:, None], np.float32(1.0), norms)
    normalized: NDArray[np.float32] = (matrix / safe).astype(np.float32, copy=False)
    return normalized, zero_ids


@dataclass(frozen=True, slots=True)
class _EncodeOutcome:
    """Result of encoding the cache misses, feeding the runtime report."""

    matrix: NDArray[np.float32]
    effective_batch_size: int
    fallback_events: tuple[str, ...]
    truncation_count: int
    token_throughput: float | None
    warnings: tuple[str, ...]


class DefaultEmbedder:
    """Cache-aware, device-qualified embedder over pluggable providers.

    ``provider_factory`` builds an :class:`EmbeddingProvider` for a
    ``(config, device)`` pair (defaults to the registry); ``device_prober``
    optionally replaces the default qualification probe (build a provider and
    encode a few representative texts) — tests use it to skip real probing.
    ``run_id`` and ``producer_version`` are stamped into the artifact header.
    """

    def __init__(
        self,
        store: ArtifactStore,
        *,
        run_id: str = "adhoc",
        producer_version: str = "linkdiscovery/0.1.0",
        provider_factory: Callable[
            [EmbeddingConfig, str], EmbeddingProvider
        ] = _default_provider_factory,
        device_prober: Callable[[str], None] | None = None,
    ) -> None:
        """Bind the artifact store the vector table will be published to."""
        self._store = store
        self._run_id = run_id
        self._producer_version = producer_version
        self._provider_factory = provider_factory
        self._device_prober = device_prober

    def embed(
        self, corpus: ProcessedCorpus, config: EmbeddingConfig, cache: ArtifactCache
    ) -> EmbeddingIndex:
        """Embed every unit of ``corpus``, reusing ``cache`` entries where keys match.

        An empty corpus produces a valid empty index (distinguishable from a
        failure). Any irrecoverable encoding failure raises
        :class:`EmbeddingRuntimeError` naming the affected unit (strict mode;
        see module docstring).
        """
        start = time.perf_counter()
        provider, qualification_events = self._qualify(config)
        dims = provider.dimensions
        units = _collect_units(corpus)
        options_fp = _runtime_options_fingerprint(config)
        keys = {
            unit.id: combine_fingerprints(
                unit.content_hash,
                corpus.preprocessing_fingerprint,
                provider.model_fingerprint,
                options_fp,
            )
            for unit in units
        }
        vectors, misses, cache_warnings = self._read_cache(cache, units, keys, dims)
        initial_batch = resolve_batch_size(config.batch_size, device=provider.device)
        outcome = self._encode_misses(provider, config, misses, initial_batch)
        for unit, row in zip(misses, outcome.matrix, strict=True):
            vector = np.ascontiguousarray(row, dtype=np.float32)
            cache.put_bytes(keys[unit.id], vector.tobytes())
            vectors[unit.id] = vector
        full = np.zeros((len(units), dims), dtype=np.float32)
        for row_index, unit in enumerate(units):
            full[row_index] = vectors[unit.id]
        storage_dtype = "float16" if config.precision == "float16" else "float32"
        records: tuple[EmbeddingRecord, ...] = ()
        if units:
            # Content-addressed table key: identical logical tables (same
            # model, same preprocessing, same options, same ordered unit
            # contents) share one stored artifact.
            table_key = combine_fingerprints(
                provider.model_fingerprint,
                corpus.preprocessing_fingerprint,
                options_fp,
                fingerprint([unit.content_hash for unit in units]),
            )
            save_vector_table(
                self._store,
                table_key,
                tuple(unit.id for unit in units),
                full,
                dtype=storage_dtype,
            )
            records = tuple(
                EmbeddingRecord(
                    unit_id=unit.id,
                    model_fingerprint=provider.model_fingerprint,
                    dimensions=dims,
                    normalized=config.normalize,
                    dtype=storage_dtype,
                    vector_ref=make_vector_ref(table_key, row_index),
                )
                for row_index, unit in enumerate(units)
            )
        runtime = RuntimeReport(
            device=provider.device,
            effective_batch_size=outcome.effective_batch_size,
            requested_batch_size=config.batch_size,
            fallback_events=qualification_events + outcome.fallback_events,
            truncation_count=outcome.truncation_count,
            failed_unit_ids=(),
            warnings=cache_warnings + outcome.warnings,
            wall_time_seconds=time.perf_counter() - start,
            token_throughput=outcome.token_throughput,
        )
        header = ArtifactHeader(
            schema_version=SCHEMA_VERSION,
            run_id=self._run_id,
            corpus_id=corpus.header.corpus_id,
            created_at=utc_now_iso(),
            config_fingerprint=config.fingerprint(),
            producer_version=self._producer_version,
        )
        return EmbeddingIndex(
            header=header,
            model_fingerprint=provider.model_fingerprint,
            dimensions=dims,
            normalized=config.normalize,
            dtype=storage_dtype,
            runtime=runtime,
            records=records,
        )

    def _qualify(self, config: EmbeddingConfig) -> tuple[EmbeddingProvider, tuple[str, ...]]:
        """Qualify a device per the runtime policy and return a provider on it.

        The default probe builds a provider for the candidate device and
        encodes a few representative texts on it — real work, not a
        framework availability check. Providers built during probing are
        reused so the model is not loaded twice. Device-independent
        providers (hashing) trivially pass on any candidate and report their
        effective device themselves.
        """
        built: dict[str, EmbeddingProvider] = {}

        def probe(device: str) -> None:
            candidate = self._provider_factory(config, device)
            candidate.encode(_PROBE_TEXTS, batch_size=len(_PROBE_TEXTS))
            built[device] = candidate

        device, events = qualify_device(config.device_preference, self._device_prober or probe)
        provider = built.get(device)
        if provider is None:
            provider = self._provider_factory(config, device)
        return provider, events

    @staticmethod
    def _read_cache(
        cache: ArtifactCache,
        units: Sequence[SemanticUnit],
        keys: dict[str, str],
        dims: int,
    ) -> tuple[dict[str, NDArray[np.float32]], list[SemanticUnit], tuple[str, ...]]:
        """Load cached vectors, validating length; mismatches are misses + warnings."""
        vectors: dict[str, NDArray[np.float32]] = {}
        misses: list[SemanticUnit] = []
        warnings: list[str] = []
        expected_bytes = dims * _FLOAT32_BYTES
        for unit in units:
            data = cache.get_bytes(keys[unit.id])
            if data is None:
                misses.append(unit)
                continue
            if len(data) != expected_bytes:
                warnings.append(
                    f"cached vector for unit {unit.id!r} has {len(data)} bytes, expected "
                    f"{expected_bytes} ({dims} float32 dimensions); treating as a miss"
                )
                misses.append(unit)
                continue
            vectors[unit.id] = np.frombuffer(data, dtype=np.float32)
        return vectors, misses, tuple(warnings)

    @staticmethod
    def _encode_misses(
        provider: EmbeddingProvider,
        config: EmbeddingConfig,
        misses: Sequence[SemanticUnit],
        initial_batch_size: int,
    ) -> _EncodeOutcome:
        """Encode cache misses adaptively; normalize; account tokens and truncations."""
        if not misses:
            return _EncodeOutcome(
                matrix=np.zeros((0, provider.dimensions), dtype=np.float32),
                effective_batch_size=initial_batch_size,
                fallback_events=(),
                truncation_count=0,
                token_throughput=None,
                warnings=(),
            )
        max_tokens = provider.max_input_tokens
        truncation_count = 0
        total_tokens = 0
        for unit in misses:
            count = provider.count_tokens(unit.text)
            if max_tokens is not None and count > max_tokens:
                truncation_count += 1
                count = max_tokens
            total_tokens += count
        miss_ids = tuple(unit.id for unit in misses)
        completed = 0

        def encode_batch(batch: Sequence[str], batch_size: int) -> NDArray[np.float32]:
            nonlocal completed
            result = provider.encode(batch, batch_size=batch_size)
            completed += len(batch)
            return result

        encode_start = time.perf_counter()
        try:
            matrix, effective_batch_size, events = encode_adaptively(
                encode_batch,
                tuple(unit.text for unit in misses),
                initial_batch_size=initial_batch_size,
                is_oom=default_is_oom,
            )
        except EmbeddingRuntimeError as exc:
            raise EmbeddingRuntimeError(
                f"{exc} (first unencoded unit: {miss_ids[completed]!r})"
            ) from exc
        except Exception as exc:
            raise EmbeddingRuntimeError(
                f"encoding failed irrecoverably for unit {miss_ids[completed]!r}: {exc}"
            ) from exc
        encode_seconds = time.perf_counter() - encode_start
        if matrix.shape != (len(misses), provider.dimensions):
            raise EmbeddingRuntimeError(
                f"provider returned matrix of shape {matrix.shape} for {len(misses)} "
                f"units; expected ({len(misses)}, {provider.dimensions}) — embedding "
                "dimension mismatch"
            )
        warnings: tuple[str, ...] = ()
        if config.normalize:
            matrix, zero_ids = _normalize_rows(matrix, miss_ids)
            warnings = tuple(
                f"unit {unit_id!r}: zero vector cannot be L2-normalized; left as zeros"
                for unit_id in zero_ids
            )
        throughput = (
            total_tokens / encode_seconds if total_tokens > 0 and encode_seconds > 0 else None
        )
        return _EncodeOutcome(
            matrix=matrix,
            effective_batch_size=effective_batch_size,
            fallback_events=events,
            truncation_count=truncation_count,
            token_throughput=throughput,
            warnings=warnings,
        )
