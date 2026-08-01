"""Deterministic text canonicalization (SPEC "Canonicalization").

Canonicalization normalizes text without ever concatenating tokens that were
separated in the source: every operation here either rewrites line
terminators, removes trailing whitespace at line ends, or applies Unicode
normalization. Markup removal is *not* canonicalization — that belongs to the
:class:`~linkdiscovery.interfaces.RegionParser`.

The policy is an explicit, frozen, fingerprintable value so the exact
normalization behavior is part of the preprocessing fingerprint: changing any
flag invalidates processed units.

Operations are applied in a fixed order (line endings, then trailing
whitespace, then Unicode NFC) and the composite is idempotent:
``canonicalize(canonicalize(t, p), p) == canonicalize(t, p)``.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any

from linkdiscovery.fingerprint import fingerprint as _fingerprint

__all__ = ["CanonicalizationPolicy", "canonicalize"]

_POLICY_VERSION = "canonicalization:v1"
"""Algorithm version; bumped whenever the meaning of any flag changes."""


@dataclass(frozen=True, slots=True)
class CanonicalizationPolicy:
    """Explicit switches for each canonicalization operation.

    Defaults implement the SPEC baseline and every field is documented so a
    configuration reviewer can see exactly what text rewriting happens:

    - ``normalize_line_endings`` (default ``True``): rewrite ``\\r\\n`` and
      lone ``\\r`` to ``\\n``.
    - ``strip_trailing_whitespace`` (default ``True``): remove trailing spaces
      and tabs from every line (line terminators are preserved).
    - ``unicode_nfc`` (default ``True``): apply Unicode NFC normalization to
      the whole text.
    """

    normalize_line_endings: bool = True
    strip_trailing_whitespace: bool = True
    unicode_nfc: bool = True

    def resolved_dict(self) -> dict[str, Any]:
        """Return the JSON-safe resolved policy, including the algorithm version."""
        return {
            "version": _POLICY_VERSION,
            "normalize_line_endings": self.normalize_line_endings,
            "strip_trailing_whitespace": self.strip_trailing_whitespace,
            "unicode_nfc": self.unicode_nfc,
        }

    def fingerprint(self) -> str:
        """Fingerprint of the resolved policy; a preprocessing-fingerprint component."""
        return _fingerprint(self.resolved_dict())


def _strip_line(line: str) -> str:
    """Strip trailing spaces and tabs from one line, preserving a ``\\r`` ending.

    ``line`` is a ``"\\n"``-split segment, so when the source used ``\\r\\n``
    terminators and line-ending normalization is disabled the segment still
    ends with ``\\r``; that terminator must survive.
    """
    if line.endswith("\r"):
        return line[:-1].rstrip(" \t") + "\r"
    return line.rstrip(" \t")


def canonicalize(text: str, policy: CanonicalizationPolicy | None = None) -> str:
    """Canonicalize ``text`` under ``policy`` (default policy when ``None``).

    Deterministic and idempotent for a fixed policy. Never joins tokens that
    were separated in the source: whitespace is only removed at line ends and
    line terminators are only rewritten, never deleted.
    """
    if policy is None:
        policy = CanonicalizationPolicy()
    if policy.normalize_line_endings:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    if policy.strip_trailing_whitespace:
        text = "\n".join(_strip_line(line) for line in text.split("\n"))
    if policy.unicode_nfc:
        text = unicodedata.normalize("NFC", text)
    return text
