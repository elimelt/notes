"""Stratified sampling of existing links for the data audit.

Implements the "minimum data audit" sampling design of
SPEC-INLINE-LINKING §4: enumerate the resolvable explicit links, stratify by
region type, anchor length bucket, topic family, and source doc type, then
draw a seeded, proportional, without-replacement sample with a floor of one
item per non-empty stratum. Output is deterministic for a fixed corpus,
size, and seed.
"""

from __future__ import annotations

import random
import re

from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.contracts.documents import Corpus, Relationship, SourceDocument
from linkdiscovery.contracts.units import (
    ProcessedCorpus,
    ProcessedDocument,
    RegionKind,
    Span,
)
from linkdiscovery.fingerprint import fingerprint
from linkdiscovery.inline.records import (
    PRODUCER_VERSION,
    SCHEMA_VERSION,
    AuditItem,
    AuditSample,
    LinkRegionKind,
)

__all__ = ["build_audit_sample"]

_CONTEXT_RADIUS = 240
"""Characters of raw source content kept on each side of the link span."""

_AUDITED_KIND = "explicit-link"
"""The relationship kind the audit samples (resolved inline/wiki links)."""

_RELATED_SECTION_TITLES = frozenset({"related", "related notes"})
"""Normalized section titles that mark a Related-notes region (Tier C zone)."""

_SHORT_ANCHOR_MAX_WORDS = 3
"""Upper bound of the "2-3" anchor word-count bucket from the audit design."""

_REGION_KIND_MAP: dict[RegionKind, LinkRegionKind] = {
    RegionKind.TITLE: LinkRegionKind.HEADING,
    RegionKind.HEADING: LinkRegionKind.HEADING,
    RegionKind.PROSE: LinkRegionKind.PROSE,
    RegionKind.LIST: LinkRegionKind.LIST,
    RegionKind.CODE: LinkRegionKind.CODE,
    RegionKind.EQUATION: LinkRegionKind.OTHER,
    RegionKind.TABLE: LinkRegionKind.TABLE,
    RegionKind.QUOTE: LinkRegionKind.OTHER,
    RegionKind.CITATION: LinkRegionKind.CITATION,
    RegionKind.METADATA: LinkRegionKind.OTHER,
    RegionKind.BOILERPLATE: LinkRegionKind.OTHER,
    RegionKind.OTHER: LinkRegionKind.OTHER,
}
"""How parser region kinds map onto the audit's link-region taxonomy."""


def _normalize_title(title: str) -> str:
    """Lowercase a heading title and collapse punctuation to single spaces."""
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _contains(outer: Span, inner: Span) -> bool:
    """True when ``inner`` lies fully within ``outer`` (half-open ranges)."""
    return outer.start <= inner.start and inner.end <= outer.end


def _locate_region_kind(processed: ProcessedDocument | None, span: Span) -> LinkRegionKind:
    """Classify where a link span sits, per the sampler rules of the audit.

    The base kind is the smallest processed region containing the span
    (ties broken by start offset, then kind value, for determinism), mapped
    through :data:`_REGION_KIND_MAP`; a span contained by no region — or a
    document with no processed form — defaults to ``prose``. The
    ``related_notes`` override then applies: a span inside a semantic unit
    whose section path ends in a heading titled like "Related notes" or
    "Related" (case-insensitive) is a Related-notes link regardless of its
    syntactic region, because those lists are graph edges, not anchor
    examples (SPEC-INLINE-LINKING §4).
    """
    if processed is None:
        return LinkRegionKind.PROSE
    for unit in processed.units:
        if not unit.section_path:
            continue
        if _normalize_title(unit.section_path[-1]) not in _RELATED_SECTION_TITLES:
            continue
        if any(_contains(unit_span, span) for unit_span in unit.source_spans):
            return LinkRegionKind.RELATED_NOTES
    containing = [region for region in processed.regions if _contains(region.span, span)]
    if not containing:
        return LinkRegionKind.PROSE
    smallest = min(
        containing,
        key=lambda region: (
            region.span.end - region.span.start,
            region.span.start,
            region.kind.value,
        ),
    )
    return _REGION_KIND_MAP[smallest.kind]


def _anchor_text(relationship: Relationship, source: SourceDocument, span: Span) -> str:
    """The link's display text: adapter metadata when present, else the span slice."""
    metadata_anchor = relationship.metadata.get("anchor_text")
    if isinstance(metadata_anchor, str) and metadata_anchor:
        return metadata_anchor
    return source.content[span.start : span.end]


def _word_count_bucket(word_count: int) -> str:
    """The audit's anchor-length strata: 1 word, 2-3 words, or 4+ words."""
    if word_count <= 1:
        return "1"
    if word_count <= _SHORT_ANCHOR_MAX_WORDS:
        return "2-3"
    return "4+"


def _topic_family(document_id: str) -> str:
    """The first path segment of a document ID (the ID itself when unsegmented)."""
    return document_id.split("/", 1)[0]


def _is_index_like(document_id: str) -> bool:
    """Index notes get their own stratum: ``index`` or any ``*/index`` ID."""
    return document_id == "index" or document_id.endswith("/index")


def _context_window(content: str, span: Span) -> str:
    """A whitespace-collapsed, ellipsized window of +-240 chars around the span."""
    start = max(0, span.start - _CONTEXT_RADIUS)
    end = min(len(content), span.end + _CONTEXT_RADIUS)
    text = " ".join(content[start:end].split())
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(content) else ""
    return f"{prefix}{text}{suffix}"


def _build_item(
    relationship: Relationship,
    source: SourceDocument,
    processed: ProcessedDocument | None,
    span: Span,
) -> AuditItem:
    """Derive one audit item from a resolvable explicit-link relationship."""
    anchor = _anchor_text(relationship, source, span)
    region_kind = _locate_region_kind(processed, span)
    word_count = len(anchor.split())
    topic_family = _topic_family(relationship.target_id)
    source_type = "index" if _is_index_like(relationship.source_id) else "note"
    strata_key = "|".join(
        (region_kind.value, _word_count_bucket(word_count), topic_family, source_type)
    )
    item_id = fingerprint([relationship.source_id, relationship.target_id, span.start, span.end])
    return AuditItem(
        id=item_id,
        source_document_id=relationship.source_id,
        target_document_id=relationship.target_id,
        anchor_text=anchor,
        source_span=span,
        region_kind=region_kind,
        context=_context_window(source.content, span),
        anchor_word_count=word_count,
        topic_family=topic_family,
        strata_key=strata_key,
    )


def _allocate(counts: dict[str, int], size: int) -> dict[str, int]:
    """Proportional per-stratum quotas with a floor of one, summing to ``size``.

    Deterministic: strata are processed in sorted-key order, leftover items
    go to the largest fractional remainders (ties broken by key). When there
    are more non-empty strata than budget the floor cannot be honored for
    all; the largest strata (ties by key) each get one item.
    """
    total = sum(counts.values())
    if size >= total:
        return dict(counts)
    keys = sorted(counts)
    if len(keys) >= size:
        chosen = sorted(keys, key=lambda key: (-counts[key], key))[:size]
        return dict.fromkeys(sorted(chosen), 1)
    allocation = dict.fromkeys(keys, 1)
    capacity = {key: counts[key] - 1 for key in keys}
    remaining = size - len(keys)
    capacity_total = sum(capacity.values())
    exact = {
        key: (remaining * capacity[key] / capacity_total) if capacity_total else 0.0 for key in keys
    }
    for key in keys:
        take = min(int(exact[key]), capacity[key])
        allocation[key] += take
        capacity[key] -= take
    remaining = size - sum(allocation.values())
    order = sorted(keys, key=lambda key: (-(exact[key] - int(exact[key])), key))
    position = 0
    while remaining > 0:
        key = order[position % len(order)]
        if capacity[key] > 0:
            allocation[key] += 1
            capacity[key] -= 1
            remaining -= 1
        position += 1
    return allocation


def build_audit_sample(
    corpus: Corpus,
    processed: ProcessedCorpus,
    *,
    size: int = 150,
    seed: int,
    run_id: str = "adhoc",
) -> AuditSample:
    """Draw the stratified audit sample of existing links (SPEC-INLINE-LINKING §4).

    Enumerates relationships with ``kind == "explicit-link"`` whose both
    endpoints exist in ``corpus`` and which carry a ``source_span``
    (duplicate (source, target, span) triples collapse to one item). Each
    link is classified into a stratum crossing region kind, anchor
    word-count bucket (1 / 2-3 / 4+), target topic family, and source doc
    type (index-like vs note), then quotas are allocated proportionally with
    a floor of one per non-empty stratum and drawn without replacement using
    ``random.Random(seed)``.

    Output items are ordered by ``(strata_key, id)`` and ``strata_counts``
    records the selected count per stratum, so the sample is byte-identical
    across runs for fixed inputs. When ``size`` exceeds the available links
    every link is returned; callers read ``len(sample.items)`` rather than
    assuming the requested size.
    """
    documents = {document.id: document for document in corpus.documents}
    processed_docs = {document.document_id: document for document in processed.documents}

    items_by_id: dict[str, AuditItem] = {}
    for relationship in corpus.relationships.relationships:
        if relationship.kind != _AUDITED_KIND or relationship.source_span is None:
            continue
        source = documents.get(relationship.source_id)
        if source is None or relationship.target_id not in documents:
            continue
        item = _build_item(
            relationship,
            source,
            processed_docs.get(relationship.source_id),
            relationship.source_span,
        )
        items_by_id.setdefault(item.id, item)

    strata: dict[str, list[AuditItem]] = {}
    for item in items_by_id.values():
        strata.setdefault(item.strata_key, []).append(item)
    allocation = _allocate({key: len(members) for key, members in strata.items()}, max(size, 0))

    rng = random.Random(seed)
    selected: list[AuditItem] = []
    strata_counts: dict[str, int] = {}
    for key in sorted(allocation):
        pool = sorted(strata[key], key=lambda item: item.id)
        quota = allocation[key]
        selected.extend(pool if quota >= len(pool) else rng.sample(pool, quota))
        strata_counts[key] = min(quota, len(pool))
    selected.sort(key=lambda item: (item.strata_key, item.id))

    header = ArtifactHeader(
        schema_version=SCHEMA_VERSION,
        run_id=run_id,
        corpus_id=corpus.header.corpus_id,
        created_at=utc_now_iso(),
        config_fingerprint=fingerprint({"size": size, "seed": seed}),
        producer_version=PRODUCER_VERSION,
    )
    return AuditSample(header=header, items=tuple(selected), strata_counts=strata_counts)
