"""Self-corpus anchor dictionary and keyphraseness statistics.

Implements the Wikimedia-style weak supervision of SPEC-INLINE-LINKING §5
(Question 19): build a ``{mention -> {target: count}}`` dictionary from the
corpus's own resolved explicit links, plus title/alias "synthetic anchors"
that map each note's names back to the note. The dictionary carries the
Milne-Witten link probability ("keyphraseness": the fraction of a mention's
prose occurrences that appear *as* a link), whose eligibility floor of ~6.5%
is the SPEC §10 starting point and the §3 (Question 11) principled filter
that lets legitimate technical terms survive region masking.

Everything here is deterministic: no builtin ``hash()``, sorted iteration
order everywhere, and JSON-safe ``to_dict()``/``from_dict()`` persistence.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from linkdiscovery.contracts.base import (
    expect_bool,
    expect_float,
    expect_int,
    expect_mapping,
    expect_str_int_map,
)
from linkdiscovery.contracts.documents import Corpus, Relationship, SourceDocument
from linkdiscovery.errors import ContractError
from linkdiscovery.fingerprint import fingerprint as _fingerprint

__all__ = [
    "AnchorConfig",
    "AnchorDictionary",
    "build_anchor_dictionary",
    "mention_pattern",
    "normalize_mention",
]

_LINKED_KIND = "explicit-link"
"""The relationship kind mined for anchor statistics (resolved inline links)."""


@dataclass(frozen=True, slots=True)
class AnchorConfig:
    """Anchor-dictionary construction and eligibility policy.

    ``keyphraseness_floor`` is the SPEC §10 Milne-Witten link-probability
    floor (start near 6.5% and tune); ``max_span_words`` and
    ``min_anchor_chars`` bound which normalized mentions enter the
    dictionary; ``lowercase`` controls case folding in
    :func:`normalize_mention` and occurrence matching.
    """

    keyphraseness_floor: float = 0.065
    max_span_words: int = 5
    min_anchor_chars: int = 3
    lowercase: bool = True

    def resolved_dict(self) -> dict[str, Any]:
        """Return the fully resolved (defaults filled) JSON-safe form."""
        return {
            "keyphraseness_floor": self.keyphraseness_floor,
            "max_span_words": self.max_span_words,
            "min_anchor_chars": self.min_anchor_chars,
            "lowercase": self.lowercase,
        }

    def fingerprint(self) -> str:
        """Fingerprint of the resolved section, for artifact invalidation."""
        return _fingerprint(self.resolved_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnchorConfig:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "AnchorConfig"
        mapping = expect_mapping(data, context)
        return cls(
            keyphraseness_floor=expect_float(mapping, "keyphraseness_floor", context),
            max_span_words=expect_int(mapping, "max_span_words", context),
            min_anchor_chars=expect_int(mapping, "min_anchor_chars", context),
            lowercase=expect_bool(mapping, "lowercase", context),
        )


def _strip_surrounding_punctuation(text: str) -> str:
    """Trim Unicode punctuation and whitespace from both ends of ``text``."""
    start, end = 0, len(text)
    while start < end and (
        text[start].isspace() or unicodedata.category(text[start]).startswith("P")
    ):
        start += 1
    while end > start and (
        text[end - 1].isspace() or unicodedata.category(text[end - 1]).startswith("P")
    ):
        end -= 1
    return text[start:end]


def normalize_mention(text: str, *, lowercase: bool = True) -> str:
    """Normalize anchor text into its dictionary mention form.

    Applies the SPEC §5 anchor preprocessing: Unicode NFC, whitespace
    collapsed to single spaces, surrounding (but not interior) punctuation
    stripped, and lowercasing when ``lowercase`` is true. Deterministic and
    idempotent.
    """
    normalized = " ".join(unicodedata.normalize("NFC", text).split())
    normalized = _strip_surrounding_punctuation(normalized)
    return normalized.lower() if lowercase else normalized


def mention_pattern(mention: str, *, lowercase: bool = True) -> re.Pattern[str]:
    """A compiled word-boundary pattern matching ``mention`` in raw text.

    Words of the normalized mention are joined by ``\\s+`` (so collapsed
    whitespace still matches raw newlines/indentation) and guarded by
    non-word lookarounds instead of ``\\b`` so mentions that start or end
    with a symbol still get boundary semantics. ``lowercase`` selects
    case-insensitive matching, mirroring :func:`normalize_mention`.
    """
    parts = [re.escape(word) for word in mention.split()]
    body = r"\s+".join(parts) if parts else re.escape(mention)
    flags = re.IGNORECASE if lowercase else 0
    return re.compile(rf"(?<!\w){body}(?!\w)", flags)


def _validated_table(
    table: Mapping[str, Mapping[str, int]] | None, name: str, config: AnchorConfig
) -> dict[str, dict[str, int]]:
    """Copy a mention->target->count table, enforcing normalization and counts."""
    result: dict[str, dict[str, int]] = {}
    for mention, targets in (table or {}).items():
        if normalize_mention(mention, lowercase=config.lowercase) != mention:
            raise ContractError(
                f"AnchorDictionary: {name} mention {mention!r} is not normalized; "
                "keys must be normalize_mention() output"
            )
        counts: dict[str, int] = {}
        for target, count in targets.items():
            if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
                raise ContractError(
                    f"AnchorDictionary: {name} count for ({mention!r}, {target!r}) "
                    f"must be a positive integer, got {count!r}"
                )
            counts[target] = count
        result[mention] = dict(sorted(counts.items()))
    return dict(sorted(result.items()))


class AnchorDictionary:
    """The self-corpus anchor dictionary (SPEC-INLINE-LINKING §5, Question 19).

    Holds two separately countable mention tables: ``linked`` (real
    explicit-link anchors, the numerator of keyphraseness) and the synthetic
    ``titles``/``aliases`` tables (note names mapped to their note). Keeping
    synthetic anchors separate means they bootstrap candidate generation and
    the commonness prior without inflating the keyphraseness statistic.

    Mention keys must already be :func:`normalize_mention` output for the
    given config; every query normalizes its argument, so callers may pass
    raw surface text. All iteration and serialization order is sorted.
    """

    def __init__(
        self,
        config: AnchorConfig,
        *,
        linked: Mapping[str, Mapping[str, int]] | None = None,
        titles: Mapping[str, Mapping[str, int]] | None = None,
        aliases: Mapping[str, Mapping[str, int]] | None = None,
        occurrences: Mapping[str, int] | None = None,
    ) -> None:
        self._config = config
        self._linked = _validated_table(linked, "linked", config)
        self._titles = _validated_table(titles, "titles", config)
        self._aliases = _validated_table(aliases, "aliases", config)
        self._occurrences: dict[str, int] | None = None
        if occurrences is not None:
            self.attach_occurrences(occurrences)

    @property
    def config(self) -> AnchorConfig:
        """The construction/eligibility policy this dictionary was built with."""
        return self._config

    @property
    def has_occurrences(self) -> bool:
        """Whether corpus occurrence counts have been attached."""
        return self._occurrences is not None

    def _norm(self, mention: str) -> str:
        return normalize_mention(mention, lowercase=self._config.lowercase)

    def mentions(self) -> tuple[str, ...]:
        """Every dictionary mention (linked and synthetic), sorted."""
        return tuple(sorted(set(self._linked) | set(self._titles) | set(self._aliases)))

    def lookup(self, mention: str) -> dict[str, int]:
        """Candidate targets for ``mention``: target id -> total count.

        Merges linked-anchor counts with synthetic title/alias counts (one
        per contributing document), sorted by target id. Unknown mentions
        return an empty mapping.
        """
        norm = self._norm(mention)
        merged: dict[str, int] = {}
        for table in (self._linked, self._titles, self._aliases):
            for target, count in table.get(norm, {}).items():
                merged[target] = merged.get(target, 0) + count
        return dict(sorted(merged.items()))

    def commonness(self, mention: str, target: str) -> float:
        """The commonness prior P(target | mention): count / total for the mention.

        Returns 0.0 for unknown mentions or targets never seen for it.
        """
        counts = self.lookup(mention)
        total = sum(counts.values())
        if total == 0:
            return 0.0
        return counts.get(target, 0) / total

    def linked_count(self, mention: str) -> int:
        """Total real explicit-link count for ``mention`` (synthetic excluded)."""
        return sum(self._linked.get(self._norm(mention), {}).values())

    def keyphraseness(self, mention: str, occurrence_count: int) -> float:
        """The Milne-Witten link probability: linked_count / occurrence_count.

        Only real linked anchors count in the numerator (SPEC §5: synthetic
        title/alias anchors must not inflate it). The caller supplies the
        corpus occurrence count (see :meth:`occurrence_counts`). Returns 0.0
        when either count is non-positive; capped at 1.0 because metadata
        anchor text can diverge from the surface text being counted.
        """
        linked = self.linked_count(mention)
        if linked <= 0 or occurrence_count <= 0:
            return 0.0
        return min(1.0, linked / occurrence_count)

    def occurrence_counts(self, corpus: Corpus) -> dict[str, int]:
        """Count each dictionary mention's occurrences in the corpus text.

        Pure and deterministic: counts non-overlapping word-boundary matches
        of every mention (case per config) over each document's raw content
        and returns a sorted mention -> count mapping; the instance is not
        modified (cache the result explicitly via :meth:`attach_occurrences`).
        This is the keyphraseness denominator; counting over full raw content
        rather than prose-only regions makes the statistic conservative.
        """
        counts = dict.fromkeys(self.mentions(), 0)
        patterns = {
            mention: mention_pattern(mention, lowercase=self._config.lowercase)
            for mention in counts
        }
        for document in corpus.documents:
            for mention, pattern in patterns.items():
                counts[mention] += sum(1 for _ in pattern.finditer(document.content))
        return counts

    def attach_occurrences(self, counts: Mapping[str, int]) -> None:
        """Cache corpus occurrence counts on the instance for :meth:`eligible`.

        This is the explicit caching step paired with the pure
        :meth:`occurrence_counts`; counts must be non-negative integers.
        """
        validated: dict[str, int] = {}
        for mention, count in counts.items():
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ContractError(
                    f"AnchorDictionary.attach_occurrences: count for {mention!r} must be "
                    f"a non-negative integer, got {count!r}"
                )
            validated[mention] = count
        self._occurrences = dict(sorted(validated.items()))

    def occurrence_count(self, mention: str) -> int:
        """The attached corpus occurrence count for ``mention`` (0 if unseen).

        Raises ``ContractError`` when occurrence counts were never attached.
        """
        if self._occurrences is None:
            raise ContractError(
                "AnchorDictionary.occurrence_count: occurrence counts not attached; "
                "call attach_occurrences(occurrence_counts(corpus)) first"
            )
        return self._occurrences.get(self._norm(mention), 0)

    def is_title(self, mention: str) -> bool:
        """Whether ``mention`` is a synthetic title anchor of some document."""
        return self._norm(mention) in self._titles

    def is_alias(self, mention: str) -> bool:
        """Whether ``mention`` is a synthetic alias anchor of some document."""
        return self._norm(mention) in self._aliases

    def eligible(self, mention: str) -> bool:
        """Anchor eligibility per SPEC §10: keyphraseness >= floor, or synthetic.

        Title/alias synthetic anchors are always eligible (they are clean
        in-domain signal, SPEC §5). Linked mentions require attached
        occurrence counts — ``ContractError`` names the missing
        :meth:`attach_occurrences` step. Unknown mentions are ineligible.
        """
        norm = self._norm(mention)
        if norm in self._titles or norm in self._aliases:
            return True
        if norm not in self._linked:
            return False
        if self._occurrences is None:
            raise ContractError(
                "AnchorDictionary.eligible: occurrence counts not attached; "
                "call attach_occurrences(occurrence_counts(corpus)) first"
            )
        keyphraseness = self.keyphraseness(norm, self._occurrences.get(norm, 0))
        return keyphraseness >= self._config.keyphraseness_floor

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives for artifact persistence."""
        return {
            "config": self._config.resolved_dict(),
            "linked": {mention: dict(targets) for mention, targets in self._linked.items()},
            "titles": {mention: dict(targets) for mention, targets in self._titles.items()},
            "aliases": {mention: dict(targets) for mention, targets in self._aliases.items()},
            "occurrences": dict(self._occurrences) if self._occurrences is not None else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnchorDictionary:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "AnchorDictionary"
        mapping = expect_mapping(data, context)
        config = AnchorConfig.from_dict(
            expect_mapping(mapping.get("config"), f"{context}: field 'config'")
        )
        occurrences = (
            expect_str_int_map(mapping, "occurrences", context)
            if mapping.get("occurrences") is not None
            else None
        )
        return cls(
            config,
            linked=_count_table(mapping, "linked", context),
            titles=_count_table(mapping, "titles", context),
            aliases=_count_table(mapping, "aliases", context),
            occurrences=occurrences,
        )


def _count_table(data: Mapping[str, Any], field: str, context: str) -> dict[str, dict[str, int]]:
    """Read a serialized mention -> target -> count table."""
    raw = expect_mapping(data.get(field, {}), f"{context}: field '{field}'")
    return {
        mention: expect_str_int_map(raw, mention, f"{context}: field '{field}'") for mention in raw
    }


def _anchor_surface(relationship: Relationship, source: SourceDocument) -> str:
    """The link's anchor text: adapter metadata when present, else the span slice."""
    metadata_anchor = relationship.metadata.get("anchor_text")
    if isinstance(metadata_anchor, str) and metadata_anchor:
        return metadata_anchor
    if relationship.source_span is None:
        return ""
    return source.content[relationship.source_span.start : relationship.source_span.end]


def _admissible(mention: str, config: AnchorConfig) -> bool:
    """Whether a normalized mention may enter the dictionary at all."""
    return len(mention) >= config.min_anchor_chars and len(mention.split()) <= config.max_span_words


def build_anchor_dictionary(corpus: Corpus, *, config: AnchorConfig) -> AnchorDictionary:
    """Build the anchor dictionary from a corpus (SPEC-INLINE-LINKING §5).

    Mines every resolved ``explicit-link`` relationship (both endpoints
    present in the corpus) that carries anchor text — the adapter's
    ``metadata["anchor_text"]`` or the raw ``source_span`` slice — into the
    linked table, then adds synthetic anchors: each document's ``title`` and
    each string in ``metadata["aliases"]`` maps to that document with count
    one per contributing document, kept in separate tables so keyphraseness
    stays honest. Mentions shorter than ``min_anchor_chars`` or longer than
    ``max_span_words`` words after normalization are dropped. Output is
    deterministic for a fixed corpus and config.
    """
    documents = {document.id: document for document in corpus.documents}
    linked: dict[str, dict[str, int]] = {}
    for relationship in corpus.relationships.relationships:
        if relationship.kind != _LINKED_KIND:
            continue
        source = documents.get(relationship.source_id)
        if source is None or relationship.target_id not in documents:
            continue
        surface = _anchor_surface(relationship, source)
        if not surface:
            continue
        mention = normalize_mention(surface, lowercase=config.lowercase)
        if not mention or not _admissible(mention, config):
            continue
        targets = linked.setdefault(mention, {})
        targets[relationship.target_id] = targets.get(relationship.target_id, 0) + 1

    titles: dict[str, dict[str, int]] = {}
    aliases: dict[str, dict[str, int]] = {}
    for document in corpus.documents:
        names: list[tuple[str, dict[str, dict[str, int]]]] = []
        if document.title:
            names.append((document.title, titles))
        raw_aliases = document.metadata.get("aliases")
        if isinstance(raw_aliases, list):
            names.extend((alias, aliases) for alias in raw_aliases if isinstance(alias, str))
        for surface, table in names:
            mention = normalize_mention(surface, lowercase=config.lowercase)
            if not mention or not _admissible(mention, config):
                continue
            targets = table.setdefault(mention, {})
            targets[document.id] = targets.get(document.id, 0) + 1

    return AnchorDictionary(config, linked=linked, titles=titles, aliases=aliases)
