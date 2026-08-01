"""Tests for deterministic canonicalization."""

from __future__ import annotations

from linkdiscovery.preprocess import CanonicalizationPolicy, canonicalize


class TestCanonicalize:
    def test_line_endings_normalized(self) -> None:
        assert canonicalize("a\r\nb\rc\n") == "a\nb\nc\n"

    def test_trailing_whitespace_stripped_per_line(self) -> None:
        assert canonicalize("a  \nb\t\nc") == "a\nb\nc"

    def test_nfc_normalization(self) -> None:
        # "e" + combining acute accent composes to a single code point.
        assert canonicalize("café") == "café"

    def test_never_joins_separated_tokens(self) -> None:
        # Interior whitespace is untouched; only line-end whitespace is removed.
        assert canonicalize("alpha  beta\ngamma") == "alpha  beta\ngamma"

    def test_line_endings_flag_off(self) -> None:
        policy = CanonicalizationPolicy(
            normalize_line_endings=False, strip_trailing_whitespace=False
        )
        assert canonicalize("a\r\nb", policy) == "a\r\nb"

    def test_strip_flag_off(self) -> None:
        policy = CanonicalizationPolicy(strip_trailing_whitespace=False)
        assert canonicalize("a  \nb", policy) == "a  \nb"

    def test_strip_preserves_cr_when_line_endings_kept(self) -> None:
        policy = CanonicalizationPolicy(normalize_line_endings=False)
        assert canonicalize("a  \r\nb", policy) == "a\r\nb"

    def test_nfc_flag_off(self) -> None:
        policy = CanonicalizationPolicy(unicode_nfc=False)
        assert canonicalize("é", policy) == "é"

    def test_idempotent(self) -> None:
        text = "café  \r\nnext line\t\r\n\rlast"
        once = canonicalize(text)
        assert canonicalize(once) == once


class TestCanonicalizationPolicy:
    def test_fingerprint_stable(self) -> None:
        assert CanonicalizationPolicy().fingerprint() == CanonicalizationPolicy().fingerprint()

    def test_fingerprint_sensitive_to_every_flag(self) -> None:
        base = CanonicalizationPolicy().fingerprint()
        assert CanonicalizationPolicy(normalize_line_endings=False).fingerprint() != base
        assert CanonicalizationPolicy(strip_trailing_whitespace=False).fingerprint() != base
        assert CanonicalizationPolicy(unicode_nfc=False).fingerprint() != base

    def test_resolved_dict_names_algorithm_version(self) -> None:
        assert CanonicalizationPolicy().resolved_dict()["version"] == "canonicalization:v1"
