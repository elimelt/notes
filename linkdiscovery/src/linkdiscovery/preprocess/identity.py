"""Stable, content-derived identity for semantic units.

The SPEC requires that "the unit ID is stable for unchanged semantic content"
and that source spans — which shift after unrelated edits — are never the sole
identity input. Identity here is therefore derived only from the retrieval
view, the section path, and the unit text:

- ``id`` = ``"<document_id>#<view>#<h>"`` where ``h`` is the first 12 hex
  digits of sha256 over the canonical JSON of ``[view, section_path, text]``.
- ``content_hash`` = the full :func:`~linkdiscovery.fingerprint.fingerprint`
  of the unit text (the exact text presented to the embedding model,
  including any prepended context).

When two units of one document collide (identical view, section path, and
text), later occurrences get deterministic positional suffixes ``~1``, ``~2``,
… in draft order, so IDs stay unique and reproducible.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from linkdiscovery.contracts.units import RegionKind, SemanticUnit, Span
from linkdiscovery.fingerprint import canonical_json, fingerprint

__all__ = ["UnitDraft", "assign_unit_ids"]

_ID_HASH_HEX_DIGITS = 12


@dataclass(frozen=True, slots=True)
class UnitDraft:
    """A semantic unit before identity assignment.

    Carries everything a :class:`~linkdiscovery.contracts.units.SemanticUnit`
    needs except ``id``, ``document_id``, and ``content_hash``, which are
    derived by :func:`assign_unit_ids`. ``text`` is the exact text that will
    be presented to the embedding model (context included) and
    ``token_count`` was measured on that exact text.
    """

    view: str
    section_path: tuple[str, ...]
    region_kinds: tuple[RegionKind, ...]
    source_spans: tuple[Span, ...]
    text: str
    token_count: int


def _identity_hash(draft: UnitDraft) -> str:
    """First 12 hex digits of sha256 over canonical ``[view, section_path, text]``."""
    preimage = canonical_json([draft.view, list(draft.section_path), draft.text])
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()[:_ID_HASH_HEX_DIGITS]


def assign_unit_ids(document_id: str, drafts: Sequence[UnitDraft]) -> tuple[SemanticUnit, ...]:
    """Materialize drafts into :class:`SemanticUnit`\\ s with stable IDs.

    Deterministic: the same drafts in the same order always produce the same
    units. Duplicate identity hashes within ``drafts`` are disambiguated by
    position with ``~1``, ``~2``, … suffixes; distinct content is never
    affected by the presence of duplicates elsewhere in the document.
    """
    counts: dict[str, int] = {}
    units: list[SemanticUnit] = []
    for draft in drafts:
        base = f"{document_id}#{draft.view}#{_identity_hash(draft)}"
        occurrence = counts.get(base, 0)
        counts[base] = occurrence + 1
        unit_id = base if occurrence == 0 else f"{base}~{occurrence}"
        units.append(
            SemanticUnit(
                id=unit_id,
                document_id=document_id,
                view=draft.view,
                section_path=draft.section_path,
                region_kinds=draft.region_kinds,
                source_spans=draft.source_spans,
                text=draft.text,
                token_count=draft.token_count,
                content_hash=fingerprint(draft.text),
            )
        )
    return tuple(units)
