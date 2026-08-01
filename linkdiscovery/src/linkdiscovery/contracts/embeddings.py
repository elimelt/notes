"""Embedding contracts: per-unit records, the index artifact, runtime report.

The embedding boundary returns normalized vectors plus model and runtime
provenance. It never exposes PyTorch, MLX, NumPy, or sentence-transformers
objects: vectors live behind ``vector_ref``, an artifact-relative reference,
so the record format does not require one storage backend. The
:class:`RuntimeReport` implements the SPEC "no silent fallback" principle by
recording device selection, fallbacks, batch sizes, and truncation stats.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from linkdiscovery.contracts.base import (
    ArtifactHeader,
    check_schema_version,
    expect_bool,
    expect_float,
    expect_header,
    expect_int,
    expect_list,
    expect_mapping,
    expect_nullable_float,
    expect_nullable_int,
    expect_str,
    expect_str_tuple,
)
from linkdiscovery.errors import ContractError

__all__ = [
    "SCHEMA_VERSION",
    "EmbeddingIndex",
    "EmbeddingRecord",
    "RuntimeReport",
]

SCHEMA_VERSION = 1
"""Schema version for embedding-index artifacts."""


@dataclass(frozen=True, slots=True)
class EmbeddingRecord:
    """Provenance for one semantic unit's vector, matching the SPEC JSON shape.

    ``model_fingerprint`` covers model identifier, revision, tokenizer
    revision, pooling, instruction text, output dimension, normalization,
    precision, and maximum input length; changing any of those changes the
    fingerprint and invalidates the record. ``vector_ref`` is an
    artifact-relative reference resolved by the storage backend.
    """

    unit_id: str
    model_fingerprint: str
    dimensions: int
    normalized: bool
    dtype: str
    vector_ref: str

    def __post_init__(self) -> None:
        if self.dimensions <= 0:
            raise ContractError(
                f"EmbeddingRecord {self.unit_id!r}: dimensions must be > 0, got {self.dimensions}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives matching the SPEC JSON shape."""
        return {
            "unit_id": self.unit_id,
            "model_fingerprint": self.model_fingerprint,
            "dimensions": self.dimensions,
            "normalized": self.normalized,
            "dtype": self.dtype,
            "vector_ref": self.vector_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmbeddingRecord:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "EmbeddingRecord"
        mapping = expect_mapping(data, context)
        return cls(
            unit_id=expect_str(mapping, "unit_id", context),
            model_fingerprint=expect_str(mapping, "model_fingerprint", context),
            dimensions=expect_int(mapping, "dimensions", context),
            normalized=expect_bool(mapping, "normalized", context),
            dtype=expect_str(mapping, "dtype", context),
            vector_ref=expect_str(mapping, "vector_ref", context),
        )


def _batch_size(data: dict[str, Any], name: str, context: str) -> int | str:
    """Read a batch-size field that is either a positive integer or ``"auto"``."""
    value = data.get(name, "auto")
    if isinstance(value, str):
        if value != "auto":
            raise ContractError(
                f"{context}: field '{name}' must be a positive integer or 'auto', got {value!r}"
            )
        return value
    size = expect_int(data, name, context)
    if size <= 0:
        raise ContractError(f"{context}: field '{name}' must be > 0, got {size}")
    return size


@dataclass(frozen=True, slots=True)
class RuntimeReport:
    """Effective embedding runtime, recorded for the run manifest.

    Captures what actually happened: the selected device, every fallback
    event (as human-readable strings such as ``"mps->cpu: out of memory"``),
    requested vs effective batch size, truncation and failure counts,
    throughput, and peak memory when the platform reports it. A permissive
    run with skipped units is distinguishable from a clean one by
    ``failed_unit_ids`` and ``warnings``.
    """

    device: str
    effective_batch_size: int
    requested_batch_size: int | str = "auto"
    fallback_events: tuple[str, ...] = ()
    truncation_count: int = 0
    failed_unit_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    wall_time_seconds: float = 0.0
    token_throughput: float | None = None
    peak_memory_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "device": self.device,
            "effective_batch_size": self.effective_batch_size,
            "requested_batch_size": self.requested_batch_size,
            "fallback_events": list(self.fallback_events),
            "truncation_count": self.truncation_count,
            "failed_unit_ids": list(self.failed_unit_ids),
            "warnings": list(self.warnings),
            "wall_time_seconds": self.wall_time_seconds,
            "token_throughput": self.token_throughput,
            "peak_memory_bytes": self.peak_memory_bytes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuntimeReport:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "RuntimeReport"
        mapping = expect_mapping(data, context)
        return cls(
            device=expect_str(mapping, "device", context),
            effective_batch_size=expect_int(mapping, "effective_batch_size", context),
            requested_batch_size=_batch_size(mapping, "requested_batch_size", context),
            fallback_events=expect_str_tuple(mapping, "fallback_events", context, default=()),
            truncation_count=expect_int(mapping, "truncation_count", context, default=0),
            failed_unit_ids=expect_str_tuple(mapping, "failed_unit_ids", context, default=()),
            warnings=expect_str_tuple(mapping, "warnings", context, default=()),
            wall_time_seconds=expect_float(mapping, "wall_time_seconds", context, default=0.0),
            token_throughput=expect_nullable_float(mapping, "token_throughput", context),
            peak_memory_bytes=expect_nullable_int(mapping, "peak_memory_bytes", context),
        )


@dataclass(frozen=True, slots=True)
class EmbeddingIndex:
    """The embedding stage output: an artifact-level contract.

    Invariants (enforced at construction): every record shares the index-level
    ``model_fingerprint``, ``dimensions``, ``normalized``, and ``dtype`` — a
    mismatch is the "embedding dimension or normalization mismatch" failure
    from the SPEC — and unit IDs are unique.
    """

    header: ArtifactHeader
    model_fingerprint: str
    dimensions: int
    normalized: bool
    dtype: str
    runtime: RuntimeReport
    records: tuple[EmbeddingRecord, ...] = ()

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for record in self.records:
            if record.unit_id in seen:
                raise ContractError(
                    f"EmbeddingIndex: duplicate embedding record for unit {record.unit_id!r}"
                )
            seen.add(record.unit_id)
            if (
                record.model_fingerprint != self.model_fingerprint
                or record.dimensions != self.dimensions
                or record.normalized != self.normalized
                or record.dtype != self.dtype
            ):
                raise ContractError(
                    f"EmbeddingIndex: record for unit {record.unit_id!r} does not match the "
                    f"index (model_fingerprint/dimensions/normalized/dtype); mixed-model "
                    f"indexes are invalid"
                )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "header": self.header.to_dict(),
            "model_fingerprint": self.model_fingerprint,
            "dimensions": self.dimensions,
            "normalized": self.normalized,
            "dtype": self.dtype,
            "runtime": self.runtime.to_dict(),
            "records": [record.to_dict() for record in self.records],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmbeddingIndex:
        """Deserialize, raising ``ContractError`` on invalid or unknown-version input."""
        context = "EmbeddingIndex"
        mapping = expect_mapping(data, context)
        header = expect_header(mapping, context)
        check_schema_version(header, SCHEMA_VERSION, context)
        records = expect_list(mapping, "records", context, default=[])
        return cls(
            header=header,
            model_fingerprint=expect_str(mapping, "model_fingerprint", context),
            dimensions=expect_int(mapping, "dimensions", context),
            normalized=expect_bool(mapping, "normalized", context),
            dtype=expect_str(mapping, "dtype", context),
            runtime=RuntimeReport.from_dict(
                expect_mapping(mapping.get("runtime"), f"{context}: field 'runtime'")
            ),
            records=tuple(
                EmbeddingRecord.from_dict(
                    expect_mapping(item, f"{context}: field 'records[{index}]'")
                )
                for index, item in enumerate(records)
            ),
        )
