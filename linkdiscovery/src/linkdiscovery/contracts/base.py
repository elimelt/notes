"""Artifact header and shared (de)serialization helpers for all contracts.

Every artifact-level contract (corpus, processed corpus, embedding index,
candidate set, proposal set, review history, run manifest) carries an
:class:`ArtifactHeader` recording schema version, run and corpus identity,
creation time, configuration fingerprint, and producer version, per the SPEC
"Data contracts" section.

The ``expect_*`` helpers implement one consistent validation policy for every
``from_dict``: a missing required field, a wrong type, or an out-of-domain
value raises :class:`~linkdiscovery.errors.ContractError` with a message that
names the context (contract type) and field. Fields that have dataclass
defaults are optional in the serialized form and fall back to their defaults.
Unknown extra fields are ignored for forward compatibility; an unknown
``schema_version`` is always an error.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from linkdiscovery.errors import ContractError
from linkdiscovery.fingerprint import canonical_json

__all__ = [
    "SCHEMA_VERSION",
    "ArtifactHeader",
    "check_schema_version",
    "expect_bool",
    "expect_float",
    "expect_header",
    "expect_int",
    "expect_json_object",
    "expect_list",
    "expect_mapping",
    "expect_nullable_float",
    "expect_nullable_int",
    "expect_nullable_str",
    "expect_str",
    "expect_str_float_map",
    "expect_str_int_map",
    "expect_str_str_map",
    "expect_str_tuple",
    "utc_now_iso",
]

SCHEMA_VERSION = 1
"""Current schema version for the base artifact header."""

_MISSING = object()


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with a UTC offset.

    Producers use this for ``ArtifactHeader.created_at``. Timestamps are
    stored as strings so artifacts stay JSON-safe and comparison stays lexical.
    """
    return datetime.now(UTC).isoformat(timespec="seconds")


def expect_mapping(value: object, context: str) -> dict[str, Any]:
    """Require ``value`` to be a JSON object (dict with string keys).

    Raises ``ContractError`` naming ``context`` when it is anything else.
    """
    if not isinstance(value, dict):
        raise ContractError(f"{context}: expected a JSON object, got {type(value).__name__}")
    for key in value:
        if not isinstance(key, str):
            raise ContractError(
                f"{context}: object keys must be strings, got {type(key).__name__} key {key!r}"
            )
    return cast("dict[str, Any]", value)


def _lookup(data: Mapping[str, Any], field: str, context: str, default: object) -> object:
    """Fetch ``field`` from ``data``; missing fields raise unless a default is given."""
    if field in data:
        return data[field]
    if default is _MISSING:
        raise ContractError(f"{context}: missing required field '{field}'")
    return default


def _type_error(context: str, field: str, expected: str, value: object) -> ContractError:
    return ContractError(
        f"{context}: field '{field}' must be {expected}, got {type(value).__name__}"
    )


def expect_str(
    data: Mapping[str, Any], field: str, context: str, default: str | object = _MISSING
) -> str:
    """Read a string field. Missing raises unless ``default`` is provided."""
    value = _lookup(data, field, context, default)
    if not isinstance(value, str):
        raise _type_error(context, field, "a string", value)
    return value


def expect_nullable_str(
    data: Mapping[str, Any], field: str, context: str, default: str | None = None
) -> str | None:
    """Read a string-or-null field, defaulting to ``default`` when absent."""
    value = _lookup(data, field, context, default)
    if value is None:
        return None
    if not isinstance(value, str):
        raise _type_error(context, field, "a string or null", value)
    return value


def expect_bool(
    data: Mapping[str, Any], field: str, context: str, default: bool | object = _MISSING
) -> bool:
    """Read a boolean field. Missing raises unless ``default`` is provided."""
    value = _lookup(data, field, context, default)
    if not isinstance(value, bool):
        raise _type_error(context, field, "a boolean", value)
    return value


def expect_int(
    data: Mapping[str, Any], field: str, context: str, default: int | object = _MISSING
) -> int:
    """Read an integer field; booleans are rejected despite being int subclasses."""
    value = _lookup(data, field, context, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise _type_error(context, field, "an integer", value)
    return value


def expect_nullable_int(
    data: Mapping[str, Any], field: str, context: str, default: int | None = None
) -> int | None:
    """Read an integer-or-null field, defaulting to ``default`` when absent."""
    value = _lookup(data, field, context, default)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise _type_error(context, field, "an integer or null", value)
    return value


def expect_float(
    data: Mapping[str, Any], field: str, context: str, default: float | object = _MISSING
) -> float:
    """Read a finite number field; integers are accepted and widened to float."""
    value = _lookup(data, field, context, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _type_error(context, field, "a number", value)
    result = float(value)
    if not math.isfinite(result):
        raise ContractError(f"{context}: field '{field}' must be finite, got {value!r}")
    return result


def expect_nullable_float(
    data: Mapping[str, Any], field: str, context: str, default: float | None = None
) -> float | None:
    """Read a number-or-null field, defaulting to ``default`` when absent."""
    value = _lookup(data, field, context, default)
    if value is None:
        return None
    return expect_float({field: value}, field, context)


def expect_list(
    data: Mapping[str, Any], field: str, context: str, default: list[Any] | object = _MISSING
) -> list[Any]:
    """Read a JSON array field. Missing raises unless ``default`` is provided."""
    value = _lookup(data, field, context, default)
    if not isinstance(value, list):
        raise _type_error(context, field, "an array", value)
    return value


def expect_str_tuple(
    data: Mapping[str, Any],
    field: str,
    context: str,
    default: tuple[str, ...] | object = _MISSING,
) -> tuple[str, ...]:
    """Read an array of strings as an immutable tuple."""
    if field not in data and isinstance(default, tuple):
        return default
    items = expect_list(data, field, context, default)
    for index, item in enumerate(items):
        if not isinstance(item, str):
            raise ContractError(
                f"{context}: field '{field}[{index}]' must be a string, got {type(item).__name__}"
            )
    return tuple(items)


def expect_json_object(
    data: Mapping[str, Any],
    field: str,
    context: str,
    default: dict[str, Any] | object = _MISSING,
) -> dict[str, Any]:
    """Read an arbitrary JSON-safe object field (used for opaque metadata).

    The value must round-trip through canonical JSON; non-JSON-safe content
    raises ``ContractError``.
    """
    value = _lookup(data, field, context, default)
    result = expect_mapping(value, f"{context}: field '{field}'")
    try:
        canonical_json(result)
    except ContractError as exc:
        raise ContractError(f"{context}: field '{field}' is not JSON-safe: {exc}") from exc
    return dict(result)


def _expect_typed_map(
    data: Mapping[str, Any],
    field: str,
    context: str,
    default: object,
    *,
    expected: str,
    check: type | tuple[type, ...],
) -> dict[str, Any]:
    value = _lookup(data, field, context, default)
    mapping = expect_mapping(value, f"{context}: field '{field}'")
    for key, item in mapping.items():
        if isinstance(item, bool) or not isinstance(item, check):
            raise ContractError(
                f"{context}: field '{field}[{key!r}]' must be {expected}, got {type(item).__name__}"
            )
    return dict(mapping)


def expect_str_float_map(
    data: Mapping[str, Any],
    field: str,
    context: str,
    default: dict[str, float] | object = _MISSING,
) -> dict[str, float]:
    """Read an object whose values are finite numbers, as ``dict[str, float]``."""
    mapping = _expect_typed_map(
        data, field, context, default, expected="a number", check=(int, float)
    )
    result: dict[str, float] = {}
    for key, item in mapping.items():
        result[key] = expect_float({key: item}, key, f"{context}: field '{field}'")
    return result


def expect_str_int_map(
    data: Mapping[str, Any],
    field: str,
    context: str,
    default: dict[str, int] | object = _MISSING,
) -> dict[str, int]:
    """Read an object whose values are integers, as ``dict[str, int]``."""
    return _expect_typed_map(data, field, context, default, expected="an integer", check=int)


def expect_str_str_map(
    data: Mapping[str, Any],
    field: str,
    context: str,
    default: dict[str, str] | object = _MISSING,
) -> dict[str, str]:
    """Read an object whose values are strings, as ``dict[str, str]``."""
    return _expect_typed_map(data, field, context, default, expected="a string", check=str)


@dataclass(frozen=True, slots=True)
class ArtifactHeader:
    """Provenance carried by every artifact-level contract.

    Invariants: ``schema_version`` identifies the serialized shape of the
    owning artifact; ``run_id`` and ``corpus_id`` are opaque identifiers;
    ``created_at`` is an ISO-8601 timestamp string; ``config_fingerprint`` is
    the fingerprint of the configuration that produced the artifact (per
    stage, so unrelated config changes do not invalidate it); and
    ``producer_version`` records the code version for drift detection.
    """

    schema_version: int
    run_id: str
    corpus_id: str
    created_at: str
    config_fingerprint: str
    producer_version: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "corpus_id": self.corpus_id,
            "created_at": self.created_at,
            "config_fingerprint": self.config_fingerprint,
            "producer_version": self.producer_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactHeader:
        """Deserialize, raising ``ContractError`` on missing or mistyped fields."""
        context = "ArtifactHeader"
        mapping = expect_mapping(data, context)
        return cls(
            schema_version=expect_int(mapping, "schema_version", context),
            run_id=expect_str(mapping, "run_id", context),
            corpus_id=expect_str(mapping, "corpus_id", context),
            created_at=expect_str(mapping, "created_at", context),
            config_fingerprint=expect_str(mapping, "config_fingerprint", context),
            producer_version=expect_str(mapping, "producer_version", context),
        )


def expect_header(data: Mapping[str, Any], context: str) -> ArtifactHeader:
    """Read and validate the required ``header`` field of an artifact."""
    value = _lookup(data, "header", context, _MISSING)
    return ArtifactHeader.from_dict(expect_mapping(value, f"{context}: field 'header'"))


def check_schema_version(header: ArtifactHeader, expected: int, context: str) -> None:
    """Reject artifacts whose header carries an unknown schema version."""
    if header.schema_version != expected:
        raise ContractError(
            f"{context}: unknown schema_version {header.schema_version}; "
            f"this build of linkdiscovery reads version {expected}"
        )
