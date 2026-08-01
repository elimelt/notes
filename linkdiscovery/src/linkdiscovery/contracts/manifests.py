"""Manifest contracts: artifact references, stage stats, run and report manifests.

The run manifest is the reproducibility record required by the SPEC: resolved
configuration, per-stage statistics (including cache hits and misses), seeds,
environment provenance, and references to every published artifact. A partial
run cannot appear complete because the manifest is published atomically after
its artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from linkdiscovery.contracts.base import (
    ArtifactHeader,
    check_schema_version,
    expect_float,
    expect_header,
    expect_int,
    expect_json_object,
    expect_list,
    expect_mapping,
    expect_str,
    expect_str_int_map,
    expect_str_str_map,
    expect_str_tuple,
)
from linkdiscovery.errors import ContractError

__all__ = [
    "SCHEMA_VERSION",
    "ArtifactRef",
    "ReportManifest",
    "RunManifest",
    "StageStats",
]

SCHEMA_VERSION = 1
"""Schema version for run-manifest and report-manifest artifacts."""


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    """A durable reference to one stored artifact.

    ``group`` is a logical artifact group (see
    :mod:`linkdiscovery.artifacts.store`), ``key`` the sanitized key within
    it, ``path`` the storage path relative to the store root, and
    ``fingerprint`` the content fingerprint of the stored bytes, so
    corruption and drift are detectable. ``size`` is the payload size in
    bytes (>= 0, enforced at construction).
    """

    group: str
    key: str
    path: str
    fingerprint: str
    size: int

    def __post_init__(self) -> None:
        if self.size < 0:
            raise ContractError(f"ArtifactRef {self.path!r}: size must be >= 0, got {self.size}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "group": self.group,
            "key": self.key,
            "path": self.path,
            "fingerprint": self.fingerprint,
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactRef:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "ArtifactRef"
        mapping = expect_mapping(data, context)
        return cls(
            group=expect_str(mapping, "group", context),
            key=expect_str(mapping, "key", context),
            path=expect_str(mapping, "path", context),
            fingerprint=expect_str(mapping, "fingerprint", context),
            size=expect_int(mapping, "size", context),
        )


@dataclass(frozen=True, slots=True)
class StageStats:
    """Observability counters for one pipeline stage.

    ``counters`` carries stage-specific counts (documents, regions, units,
    vectors, exclusions and failures by reason) without widening this
    contract for every stage; ``warnings`` are human-readable and preserved
    verbatim in the run manifest.
    """

    stage: str
    wall_time_seconds: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    input_count: int = 0
    output_count: int = 0
    warnings: tuple[str, ...] = ()
    counters: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "stage": self.stage,
            "wall_time_seconds": self.wall_time_seconds,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "input_count": self.input_count,
            "output_count": self.output_count,
            "warnings": list(self.warnings),
            "counters": dict(self.counters),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StageStats:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "StageStats"
        mapping = expect_mapping(data, context)
        return cls(
            stage=expect_str(mapping, "stage", context),
            wall_time_seconds=expect_float(mapping, "wall_time_seconds", context, default=0.0),
            cache_hits=expect_int(mapping, "cache_hits", context, default=0),
            cache_misses=expect_int(mapping, "cache_misses", context, default=0),
            input_count=expect_int(mapping, "input_count", context, default=0),
            output_count=expect_int(mapping, "output_count", context, default=0),
            warnings=expect_str_tuple(mapping, "warnings", context, default=()),
            counters=expect_str_int_map(mapping, "counters", context, default={}),
        )


@dataclass(frozen=True, slots=True)
class RunManifest:
    """The reproducibility record for one run: an artifact-level contract.

    ``resolved_config`` is the fully resolved configuration (defaults filled)
    from ``PipelineConfig.resolved_dict()``; ``seeds`` records every random
    seed; ``environment`` records dependency and producer versions, device
    and platform strings. ``artifacts`` references every artifact the run
    published.
    """

    header: ArtifactHeader
    resolved_config: dict[str, Any] = field(default_factory=dict)
    stages: tuple[StageStats, ...] = ()
    artifacts: tuple[ArtifactRef, ...] = ()
    seeds: dict[str, int] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "header": self.header.to_dict(),
            "resolved_config": dict(self.resolved_config),
            "stages": [stage.to_dict() for stage in self.stages],
            "artifacts": [ref.to_dict() for ref in self.artifacts],
            "seeds": dict(self.seeds),
            "environment": dict(self.environment),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunManifest:
        """Deserialize, raising ``ContractError`` on invalid or unknown-version input."""
        context = "RunManifest"
        mapping = expect_mapping(data, context)
        header = expect_header(mapping, context)
        check_schema_version(header, SCHEMA_VERSION, context)
        stages = expect_list(mapping, "stages", context, default=[])
        artifacts = expect_list(mapping, "artifacts", context, default=[])
        return cls(
            header=header,
            resolved_config=expect_json_object(mapping, "resolved_config", context, default={}),
            stages=tuple(
                StageStats.from_dict(expect_mapping(item, f"{context}: field 'stages[{index}]'"))
                for index, item in enumerate(stages)
            ),
            artifacts=tuple(
                ArtifactRef.from_dict(
                    expect_mapping(item, f"{context}: field 'artifacts[{index}]'")
                )
                for index, item in enumerate(artifacts)
            ),
            seeds=expect_str_int_map(mapping, "seeds", context, default={}),
            environment=expect_str_str_map(mapping, "environment", context, default={}),
        )


@dataclass(frozen=True, slots=True)
class ReportManifest:
    """What a reporter wrote: an artifact-level contract returned by ``Reporter.write``.

    ``formats`` lists the formats actually rendered; ``outputs`` references
    the rendered files. Reporters never mutate source documents, so this is
    the only record of their effect.
    """

    header: ArtifactHeader
    formats: tuple[str, ...] = ()
    outputs: tuple[ArtifactRef, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "header": self.header.to_dict(),
            "formats": list(self.formats),
            "outputs": [ref.to_dict() for ref in self.outputs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReportManifest:
        """Deserialize, raising ``ContractError`` on invalid or unknown-version input."""
        context = "ReportManifest"
        mapping = expect_mapping(data, context)
        header = expect_header(mapping, context)
        check_schema_version(header, SCHEMA_VERSION, context)
        outputs = expect_list(mapping, "outputs", context, default=[])
        return cls(
            header=header,
            formats=expect_str_tuple(mapping, "formats", context, default=()),
            outputs=tuple(
                ArtifactRef.from_dict(expect_mapping(item, f"{context}: field 'outputs[{index}]'"))
                for index, item in enumerate(outputs)
            ),
        )
