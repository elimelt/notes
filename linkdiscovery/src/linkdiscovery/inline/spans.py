"""High-recall Markdown-aware candidate span proposal.

Implements the first stage of the SPEC-INLINE-LINKING §1 pipeline: enumerate
candidate anchor spans inside prose/list regions only, with code, tables,
math, frontmatter, and headings masked out by construction (§3, Question 11).
Three high-recall sources feed the pool — dictionary-eligible mentions,
title/alias n-gram matches, and capitalized/technical-term extras — and two
hard exclusions apply regardless of any learned score: never overlap an
existing link's span and never propose inside inline code or math (SPEC
caveat: "preserve Markdown correctness and never overlap existing links").

:func:`span_recall` is the phase-2 recall-ceiling check of §11: the fraction
of audited prose anchors covered by some candidate, gated at >= ~85% by the
§12 candidate-generation kill criterion.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from linkdiscovery.contracts.documents import RelationshipSet, SourceDocument
from linkdiscovery.contracts.units import ProcessedDocument, Region, RegionKind, Span
from linkdiscovery.errors import ContractError
from linkdiscovery.fingerprint import fingerprint as _fingerprint
from linkdiscovery.inline.anchors import AnchorDictionary, mention_pattern, normalize_mention
from linkdiscovery.inline.records import AuditItem, LinkRegionKind, SpanCandidate

__all__ = ["SpanConfig", "propose_spans", "span_recall"]

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
"""Parser region kinds mapped onto the link-region taxonomy (audit sampler convention)."""

_RELATED_SECTION_TITLES = frozenset({"related", "related notes"})
"""Normalized section titles marking a Related-notes zone (graph edges, not anchors)."""

_INLINE_CODE = re.compile(r"`+[^`]+`+")
"""Backtick runs: inline code inside prose text."""

_INLINE_MATH = re.compile(r"\$[^$\n]+\$")
"""Dollar-delimited inline math inside prose text."""

_TOKEN = re.compile(r"\S+")
_TITLECASE_WORD = re.compile(r"[A-Z][A-Za-z0-9]*")
_ACRONYM = re.compile(r"[A-Z][A-Z0-9]+")
_HYPHENATED = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+")

_OVERLAP_COVERAGE = 0.8
"""Gold-anchor coverage required by the relaxed span_recall variant."""


@dataclass(frozen=True, slots=True)
class SpanConfig:
    """Candidate span proposal policy.

    ``max_words`` caps candidate length; ``context_chars`` is the context
    window radius downstream featurization reads around each span (recorded
    here so it participates in the stage fingerprint); ``allowed_regions``
    whitelists the link-region kinds spans may be proposed in — everything
    else (code, tables, math, frontmatter, headings) is masked out by
    construction (SPEC §3, Question 11).
    """

    max_words: int = 5
    context_chars: int = 240
    allowed_regions: tuple[LinkRegionKind, ...] = (LinkRegionKind.PROSE, LinkRegionKind.LIST)

    def resolved_dict(self) -> dict[str, Any]:
        """Return the fully resolved (defaults filled) JSON-safe form."""
        return {
            "max_words": self.max_words,
            "context_chars": self.context_chars,
            "allowed_regions": [kind.value for kind in self.allowed_regions],
        }

    def fingerprint(self) -> str:
        """Fingerprint of the resolved section, for candidate invalidation."""
        return _fingerprint(self.resolved_dict())


def _normalize_title(title: str) -> str:
    """Lowercase a heading title and collapse punctuation to single spaces."""
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _contains(outer: Span, inner: Span) -> bool:
    """True when ``inner`` lies fully within ``outer`` (half-open ranges)."""
    return outer.start <= inner.start and inner.end <= outer.end


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """True when two half-open ranges share at least one position."""
    return a_start < b_end and b_start < a_end


def _related_notes_spans(processed_doc: ProcessedDocument) -> tuple[Span, ...]:
    """Source spans of units under a "Related notes"-style heading (Tier-C zone)."""
    spans: list[Span] = []
    for unit in processed_doc.units:
        if not unit.section_path:
            continue
        if _normalize_title(unit.section_path[-1]) in _RELATED_SECTION_TITLES:
            spans.extend(unit.source_spans)
    return tuple(spans)


def _smallest_region_kind(regions: Sequence[Region], span: Span) -> LinkRegionKind | None:
    """The mapped kind of the smallest region containing ``span`` (sampler rule)."""
    containing = [region for region in regions if _contains(region.span, span)]
    if not containing:
        return None
    smallest = min(
        containing,
        key=lambda region: (
            region.span.end - region.span.start,
            region.span.start,
            region.kind.value,
        ),
    )
    return _REGION_KIND_MAP[smallest.kind]


def _masked_ranges(text: str) -> tuple[tuple[int, int], ...]:
    """Inline-code and inline-math ranges within a region's raw text slice."""
    ranges = [
        (match.start(), match.end())
        for pattern in (_INLINE_CODE, _INLINE_MATH)
        for match in pattern.finditer(text)
    ]
    return tuple(sorted(ranges))


def _clean_tokens(text: str) -> list[tuple[int, int]]:
    """Word-token ranges in ``text`` with surrounding punctuation trimmed."""
    tokens: list[tuple[int, int]] = []
    for match in _TOKEN.finditer(text):
        start, end = match.start(), match.end()
        while start < end and not (text[start].isalnum() or text[start] == "_"):
            start += 1
        while end > start and not (text[end - 1].isalnum() or text[end - 1] in "+_"):
            end -= 1
        if start < end:
            tokens.append((start, end))
    return tokens


def _is_titlecase_token(token: str) -> bool:
    """A TitleCase/CamelCase word: starts uppercase and contains a lowercase char."""
    return bool(_TITLECASE_WORD.fullmatch(token)) and any(char.islower() for char in token)


def _is_acronym_token(token: str) -> bool:
    """An ALL-CAPS acronym of at least two characters (digits allowed)."""
    return bool(_ACRONYM.fullmatch(token))


def _is_hyphenated_token(token: str) -> bool:
    """A hyphenated technical term such as ``head-of-line`` or ``type-safe``."""
    return bool(_HYPHENATED.fullmatch(token)) and any(char.isalpha() for char in token)


def _titlecase_runs(text: str, tokens: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    """Maximal runs of consecutive TitleCase tokens, as (start, end) ranges."""
    runs: list[tuple[int, int]] = []
    run: list[tuple[int, int]] = []
    for token in [*tokens, None]:
        if token is not None and _is_titlecase_token(text[token[0] : token[1]]):
            run.append(token)
            continue
        if run:
            runs.append((run[0][0], run[-1][1]))
            run = []
    return runs


def _dictionary_matches(
    text: str, dictionary: AnchorDictionary, eligible_mentions: Sequence[str]
) -> list[tuple[int, int]]:
    """Occurrences of every eligible dictionary mention in a raw text slice."""
    lowercase = dictionary.config.lowercase
    return [
        (match.start(), match.end())
        for mention in eligible_mentions
        for match in mention_pattern(mention, lowercase=lowercase).finditer(text)
    ]


def _name_ngram_matches(
    text: str,
    tokens: Sequence[tuple[int, int]],
    dictionary: AnchorDictionary,
    max_words: int,
) -> list[tuple[int, int]]:
    """Word n-grams (1..max_words) whose normalized form is a note title/alias."""
    matches: list[tuple[int, int]] = []
    lowercase = dictionary.config.lowercase
    for first in range(len(tokens)):
        for last in range(first, min(first + max_words, len(tokens))):
            start, end = tokens[first][0], tokens[last][1]
            mention = normalize_mention(text[start:end], lowercase=lowercase)
            if mention and (dictionary.is_title(mention) or dictionary.is_alias(mention)):
                matches.append((start, end))
    return matches


def _technical_extras(
    text: str, tokens: Sequence[tuple[int, int]], max_words: int
) -> list[tuple[int, int]]:
    """High-recall extras: TitleCase runs, ALL-CAPS acronyms, hyphenated terms."""
    extras = [
        (start, end)
        for start, end in _titlecase_runs(text, tokens)
        if len(text[start:end].split()) <= max_words
    ]
    for start, end in tokens:
        token = text[start:end]
        if _is_acronym_token(token) or _is_hyphenated_token(token):
            extras.append((start, end))
    return extras


def _text_shape_features(text: str) -> dict[str, float]:
    """Casing/shape features computed from the candidate surface text."""
    words = text.split()
    is_titlecase = (
        bool(words)
        and all(word[:1].isupper() for word in words)
        and any(char.islower() for char in text)
    )
    return {
        "is_acronym": 1.0 if _is_acronym_token(text) else 0.0,
        "is_titlecase": 1.0 if is_titlecase else 0.0,
        "is_hyphenated": 1.0 if _is_hyphenated_token(text) else 0.0,
    }


def _unit_id_for(processed_doc: ProcessedDocument, span: Span) -> str | None:
    """The semantic unit containing ``span`` (smallest source span, ties by id)."""
    best: tuple[int, int, str] | None = None
    for unit in processed_doc.units:
        for unit_span in unit.source_spans:
            if _contains(unit_span, span):
                key = (unit_span.end - unit_span.start, unit_span.start, unit.id)
                if best is None or key < best:
                    best = key
    return best[2] if best else None


def _build_candidate(
    document: SourceDocument,
    processed_doc: ProcessedDocument,
    region: Region,
    region_kind: LinkRegionKind,
    span: Span,
    dictionary: AnchorDictionary,
) -> SpanCandidate:
    """Assemble one :class:`SpanCandidate` with its full feature vector."""
    text = document.content[span.start : span.end]
    targets = dictionary.lookup(text)
    total = sum(targets.values())
    commonness_top = max((count / total for count in targets.values()), default=0.0)
    region_length = max(1, region.span.end - region.span.start)
    position = (span.start - region.span.start) / region_length
    words = text.split()
    features: dict[str, float] = {
        "keyphraseness": dictionary.keyphraseness(text, dictionary.occurrence_count(text)),
        "commonness_top": commonness_top,
        "anchor_count": float(total),
        "target_count": float(len(targets)),
        "word_count": float(len(words)),
        "char_count": float(len(text)),
        "is_title_match": 1.0 if dictionary.is_title(text) else 0.0,
        "is_alias_match": 1.0 if dictionary.is_alias(text) else 0.0,
        "sentence_position": min(1.0, max(0.0, position)),
        "region_prose": 1.0 if region_kind is LinkRegionKind.PROSE else 0.0,
    }
    features.update(_text_shape_features(text))
    return SpanCandidate(
        id=_fingerprint([document.id, span.start, span.end, text]),
        document_id=document.id,
        unit_id=_unit_id_for(processed_doc, span),
        span=span,
        text=text,
        region_kind=region_kind,
        word_count=len(words),
        features=features,
    )


def propose_spans(
    document: SourceDocument,
    processed_doc: ProcessedDocument,
    relationships: RelationshipSet,
    dictionary: AnchorDictionary,
    *,
    config: SpanConfig,
) -> tuple[SpanCandidate, ...]:
    """Propose high-recall candidate anchor spans for one document (SPEC §1).

    Enumerates three candidate sources inside allowed (prose/list) regions:
    (a) occurrences of every dictionary-eligible mention, (b) word n-grams
    matching a note title or alias, and (c) TitleCase runs, ALL-CAPS
    acronyms, and hyphenated technical terms as recall extras marked by the
    ``is_titlecase``/``is_acronym``/``is_hyphenated`` features. All spans
    index the raw document content (region span + in-region offset).

    Hard exclusions, applied outside any learned score: spans overlapping an
    existing link's ``source_span``; spans inside inline code (backticks) or
    inline math (``$...$``); spans in Related-notes zones; spans whose
    smallest containing region is not an allowed kind; spans longer than
    ``max_words``. Region-boundary crossing is impossible by construction.

    Identical spans from different sources merge into one candidate;
    overlapping distinct spans are all kept — the SPEC scores overlapping
    candidates independently and lets global selection dedup. Output is
    sorted by span start, then length descending; ids are deterministic
    fingerprints of (document id, span, text). Requires the dictionary's
    occurrence counts to be attached (``ContractError`` otherwise).
    """
    if not dictionary.has_occurrences:
        raise ContractError(
            "propose_spans: dictionary occurrence counts not attached; call "
            "dictionary.attach_occurrences(dictionary.occurrence_counts(corpus)) first"
        )
    link_spans = tuple(
        relationship.source_span
        for relationship in relationships.relationships
        if relationship.source_id == document.id and relationship.source_span is not None
    )
    related_spans = _related_notes_spans(processed_doc)
    eligible_mentions = [
        mention for mention in dictionary.mentions() if dictionary.eligible(mention)
    ]

    found: dict[tuple[int, int], SpanCandidate] = {}
    for region in processed_doc.regions:
        region_kind = _REGION_KIND_MAP[region.kind]
        if region_kind not in config.allowed_regions:
            continue
        raw = document.content[region.span.start : region.span.end]
        masks = _masked_ranges(raw)
        tokens = _clean_tokens(raw)
        proposals = (
            _dictionary_matches(raw, dictionary, eligible_mentions)
            + _name_ngram_matches(raw, tokens, dictionary, config.max_words)
            + _technical_extras(raw, tokens, config.max_words)
        )
        base = region.span.start
        for rel_start, rel_end in proposals:
            if rel_start >= rel_end:
                continue
            if any(_overlaps(rel_start, rel_end, m_start, m_end) for m_start, m_end in masks):
                continue
            span = Span(start=base + rel_start, end=base + rel_end)
            key = (span.start, span.end)
            if key in found:
                continue
            text = document.content[span.start : span.end]
            if not text.strip() or len(text.split()) > config.max_words:
                continue
            if any(_overlaps(span.start, span.end, link.start, link.end) for link in link_spans):
                continue
            if any(_contains(related, span) for related in related_spans):
                continue
            smallest = _smallest_region_kind(processed_doc.regions, span)
            if smallest is not None and smallest not in config.allowed_regions:
                continue
            found[key] = _build_candidate(
                document, processed_doc, region, region_kind, span, dictionary
            )

    ordered = sorted(
        found.values(), key=lambda candidate: (candidate.span.start, -len(candidate.text))
    )
    return tuple(ordered)


def span_recall(
    items: Sequence[AuditItem],
    candidates_by_doc: Mapping[str, Sequence[SpanCandidate]],
) -> dict[str, float]:
    """The phase-2 recall-ceiling check (SPEC §11 step 2, §12 kill criterion).

    Over audited PROSE-region items that carry a source span, reports the
    fraction whose anchor span is covered by some candidate for the same
    document: ``exact_recall`` requires an identical span; ``overlap_recall``
    accepts a candidate covering >= 80% of the gold anchor's characters
    (empty gold spans fall back to the exact test). ``n_prose_items`` is the
    denominator. Both recalls are 0.0 when there are no prose items — an
    empty audit cannot certify the >= 85% generation ceiling of §12.
    """
    prose_items = [
        item
        for item in items
        if item.region_kind is LinkRegionKind.PROSE and item.source_span is not None
    ]
    exact = 0
    overlap = 0
    for item in prose_items:
        gold = item.source_span
        assert gold is not None  # narrowed by the filter above
        candidates = candidates_by_doc.get(item.source_document_id, ())
        if any(candidate.span == gold for candidate in candidates):
            exact += 1
            overlap += 1
            continue
        gold_length = gold.end - gold.start
        if gold_length <= 0:
            continue
        covered = any(
            min(candidate.span.end, gold.end) - max(candidate.span.start, gold.start)
            >= _OVERLAP_COVERAGE * gold_length
            for candidate in candidates
        )
        if covered:
            overlap += 1
    count = len(prose_items)
    return {
        "exact_recall": exact / count if count else 0.0,
        "overlap_recall": overlap / count if count else 0.0,
        "n_prose_items": float(count),
    }
