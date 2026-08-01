"""Exception hierarchy shared by every pipeline stage.

All errors raised by :mod:`linkdiscovery` derive from :class:`LinkDiscoveryError`,
so callers can catch one type at the pipeline boundary. Stage-specific
subclasses exist so independently implemented stages report failures through a
single, predictable hierarchy. Every message must be human-actionable: it names
the offending input (field, file, key, or spec) and states what was expected.
"""

from __future__ import annotations

__all__ = [
    "ArtifactError",
    "CacheError",
    "CandidateError",
    "ConfigError",
    "ContractError",
    "EmbeddingRuntimeError",
    "LinkDiscoveryError",
    "PluginError",
    "PreprocessError",
    "RankingError",
    "ReportError",
]


class LinkDiscoveryError(Exception):
    """Base class for every error raised by the linkdiscovery package."""


class ContractError(LinkDiscoveryError):
    """A data contract was violated.

    Raised when deserializing an artifact with missing fields, wrong types,
    an unknown ``schema_version``, or values that break a documented invariant
    (for example a span with ``end < start``), and when a value cannot be
    represented as canonical JSON.
    """


class ConfigError(LinkDiscoveryError):
    """A pipeline configuration is invalid.

    Raised for unknown fields, missing required fields, wrong value types, or
    values outside their documented domain. Messages name the field and the
    configuration location so the user can fix the YAML directly.
    """


class PluginError(LinkDiscoveryError):
    """A plugin spec could not be resolved to a usable object.

    Raised for malformed ``"package.module:Attr"`` specs, import failures,
    missing attributes, objects that do not satisfy the expected type or
    Protocol, and instantiation failures.
    """


class ArtifactError(LinkDiscoveryError):
    """An artifact could not be stored or retrieved.

    Raised for unknown artifact groups, unsafe keys, missing artifacts,
    corrupt payloads, and failed atomic writes.
    """


class CacheError(LinkDiscoveryError):
    """A cache operation failed for a reason other than a plain miss.

    A miss is reported as ``None``; :class:`CacheError` signals invalid keys,
    corrupt entries, or an unusable backing store.
    """


class EmbeddingRuntimeError(LinkDiscoveryError):
    """The embedding runtime failed (device, memory, model, or tokenizer).

    Reserved for the embedding stage: unavailable devices, unsupported
    operations, out-of-memory conditions that exhaust the retry policy, and
    model or tokenizer revision drift.
    """


class PreprocessError(LinkDiscoveryError):
    """Preprocessing failed to produce valid regions or semantic units."""


class CandidateError(LinkDiscoveryError):
    """Candidate generation failed (index mismatch, budget, or backend)."""


class RankingError(LinkDiscoveryError):
    """Ranking failed (incompatible features, versions, or calibration data)."""


class ReportError(LinkDiscoveryError):
    """Report generation failed (unwritable output or unsupported format)."""
