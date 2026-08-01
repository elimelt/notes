"""Determinism and sensitivity tests for fingerprinting utilities."""

from __future__ import annotations

import math

import pytest

from linkdiscovery.errors import ContractError
from linkdiscovery.fingerprint import (
    canonical_json,
    combine_fingerprints,
    fingerprint,
    fingerprint_bytes,
)


class TestCanonicalJson:
    def test_key_order_does_not_matter(self) -> None:
        assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})

    def test_output_has_no_whitespace_variance(self) -> None:
        assert canonical_json({"a": [1, 2], "b": "x"}) == '{"a":[1,2],"b":"x"}'

    def test_nested_structures_are_canonicalized(self) -> None:
        left = {"outer": {"y": [True, None], "x": 1.5}}
        right = {"outer": {"x": 1.5, "y": [True, None]}}
        assert canonical_json(left) == canonical_json(right)

    def test_non_ascii_is_escaped_deterministically(self) -> None:
        assert canonical_json({"title": "schéma"}) == '{"title":"sch\\u00e9ma"}'

    @pytest.mark.parametrize(
        "bad",
        [
            math.nan,
            math.inf,
            {"a": -math.inf},
            {"a": {1: "non-string key"}},
            {"a": (1, 2)},
            {"a": {1, 2}},
            {"a": b"bytes"},
            object(),
        ],
        ids=["nan", "inf", "-inf", "int-key", "tuple", "set", "bytes", "object"],
    )
    def test_non_json_safe_values_rejected(self, bad: object) -> None:
        with pytest.raises(ContractError):
            canonical_json(bad)

    def test_error_names_the_path(self) -> None:
        with pytest.raises(ContractError, match=r"\$\.outer\[1\]"):
            canonical_json({"outer": [1, {3, 4}]})


class TestFingerprint:
    def test_deterministic_across_calls(self) -> None:
        value = {"model": "qwen", "dims": 4096, "normalize": True}
        assert fingerprint(value) == fingerprint(dict(reversed(list(value.items()))))

    def test_known_value_is_stable(self) -> None:
        # Pinned so a regression in canonicalization or hashing is caught.
        assert fingerprint({"a": 1}) == (
            "sha256:015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862"
        )

    def test_sensitive_to_any_field_change(self) -> None:
        base = {"a": 1, "b": {"c": [1, 2, 3]}}
        changed_value = {"a": 1, "b": {"c": [1, 2, 4]}}
        changed_key = {"a": 1, "d": {"c": [1, 2, 3]}}
        assert fingerprint(base) != fingerprint(changed_value)
        assert fingerprint(base) != fingerprint(changed_key)

    def test_type_changes_change_the_fingerprint(self) -> None:
        assert fingerprint({"a": "1"}) != fingerprint({"a": 1})

    def test_algorithm_prefix(self) -> None:
        result = fingerprint({"a": 1}, algorithm="sha512")
        assert result.startswith("sha512:")
        assert len(result.removeprefix("sha512:")) == 128

    def test_unknown_algorithm_rejected(self) -> None:
        with pytest.raises(ContractError, match="unsupported fingerprint algorithm"):
            fingerprint({"a": 1}, algorithm="rot13")

    def test_fingerprint_bytes_matches_prefix_format(self) -> None:
        result = fingerprint_bytes(b"payload")
        assert result.startswith("sha256:")
        assert len(result.removeprefix("sha256:")) == 64


class TestCombineFingerprints:
    def test_order_sensitive(self) -> None:
        a, b = fingerprint({"x": 1}), fingerprint({"x": 2})
        assert combine_fingerprints(a, b) != combine_fingerprints(b, a)

    def test_deterministic(self) -> None:
        assert combine_fingerprints("sha256:a", "sha256:b") == combine_fingerprints(
            "sha256:a", "sha256:b"
        )

    def test_distinct_from_parts(self) -> None:
        part = fingerprint({"x": 1})
        assert combine_fingerprints(part) != part

    def test_requires_at_least_one_part(self) -> None:
        with pytest.raises(ContractError, match="at least one part"):
            combine_fingerprints()

    def test_rejects_empty_parts(self) -> None:
        with pytest.raises(ContractError, match="non-empty string"):
            combine_fingerprints("sha256:a", "")
