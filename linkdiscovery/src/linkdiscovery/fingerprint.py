"""Deterministic fingerprinting of JSON-safe values.

Fingerprints identify configuration, content, and artifacts across runs and
platforms, so every function here must be deterministic: the same logical
value always produces the same string on every OS and Python >= 3.11. That is
achieved by canonicalizing values to a single JSON encoding (sorted keys, no
whitespace variance, ASCII-only) before hashing.

Only JSON-safe values are accepted: ``dict`` with string keys, ``list``,
``str``, finite ``int``/``float``, ``bool``, and ``None``. Anything else
(tuples, sets, NaN, infinities, arbitrary objects) is rejected with
:class:`~linkdiscovery.errors.ContractError` rather than silently coerced,
because a lossy coercion would make fingerprints ambiguous.
"""

from __future__ import annotations

import hashlib
import json
import math

from linkdiscovery.errors import ContractError

__all__ = [
    "canonical_json",
    "combine_fingerprints",
    "fingerprint",
    "fingerprint_bytes",
]

_DEFAULT_ALGORITHM = "sha256"


def _ensure_json_safe(value: object, path: str) -> None:
    """Validate that ``value`` is JSON-safe, raising ``ContractError`` if not.

    ``path`` is a human-readable locator (for example ``$.weights.w_hub``)
    included in error messages so the offending value can be found.
    """
    if value is None or isinstance(value, bool | int | str):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ContractError(
                f"value at {path} is {value!r}; NaN and infinities are not JSON-safe"
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _ensure_json_safe(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError(
                    f"object key {key!r} at {path} is {type(key).__name__}; "
                    "JSON object keys must be strings"
                )
            _ensure_json_safe(item, f"{path}.{key}")
        return
    raise ContractError(
        f"value at {path} has type {type(value).__name__}, which is not JSON-safe; "
        "use dict, list, str, int, float, bool, or None"
    )


def canonical_json(obj: object) -> str:
    """Encode ``obj`` as canonical JSON: sorted keys, compact, ASCII-only.

    The output is byte-for-byte stable for a given logical value, independent
    of dict insertion order, platform, or locale, which makes it a valid
    hashing pre-image.

    Raises ``ContractError`` when ``obj`` contains a non-JSON-safe value.
    """
    _ensure_json_safe(obj, "$")
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def fingerprint_bytes(data: bytes, *, algorithm: str = _DEFAULT_ALGORITHM) -> str:
    """Hash raw bytes, returning ``"<algorithm>:<hexdigest>"``.

    Used for content-addressing artifact payloads. Raises ``ContractError``
    when ``algorithm`` is not available in :mod:`hashlib`.
    """
    try:
        digest = hashlib.new(algorithm)
    except (ValueError, TypeError) as exc:
        raise ContractError(
            f"unsupported fingerprint algorithm {algorithm!r}; "
            "use a hashlib algorithm name such as 'sha256'"
        ) from exc
    digest.update(data)
    return f"{algorithm}:{digest.hexdigest()}"


def fingerprint(obj: object, *, algorithm: str = _DEFAULT_ALGORITHM) -> str:
    """Fingerprint a JSON-safe value, returning ``"<algorithm>:<hexdigest>"``.

    Two values receive the same fingerprint if and only if their canonical
    JSON encodings are identical; any change to a nested field changes the
    result. Raises ``ContractError`` for non-JSON-safe values or unknown
    algorithms.
    """
    return fingerprint_bytes(canonical_json(obj).encode("utf-8"), algorithm=algorithm)


def combine_fingerprints(*parts: str, algorithm: str = _DEFAULT_ALGORITHM) -> str:
    """Combine fingerprint strings into one order-sensitive fingerprint.

    Used to compose stage-level cache keys (for example unit content hash +
    preprocessing fingerprint + model fingerprint). Requires at least one
    part; every part must be a non-empty string. Raises ``ContractError``
    otherwise.
    """
    if not parts:
        raise ContractError("combine_fingerprints requires at least one part")
    for index, part in enumerate(parts):
        if not isinstance(part, str) or not part:
            raise ContractError(
                f"combine_fingerprints part {index} must be a non-empty string, got {part!r}"
            )
    return fingerprint(list(parts), algorithm=algorithm)
