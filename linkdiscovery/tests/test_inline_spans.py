"""Candidate span proposal: sources, exclusions, features, and the recall ceiling."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from linkdiscovery.contracts import (
    ProcessedDocument,
    Region,
    RegionKind,
    Relationship,
    RelationshipSet,
    SemanticUnit,
    SourceDocument,
    Span,
)
from linkdiscovery.errors import ContractError
from linkdiscovery.inline.anchors import AnchorConfig, AnchorDictionary
from linkdiscovery.inline.records import AuditItem, LinkRegionKind, SpanCandidate
from linkdiscovery.inline.spans import SpanConfig, propose_spans, span_recall

DOC_ID = "notes/src"


def build_document(
    parts: Sequence[tuple[RegionKind, str]],
) -> tuple[SourceDocument, ProcessedDocument]:
    """Assemble raw content and matching regions from (kind, text) parts."""
    content = ""
    regions: list[Region] = []
    for kind, text in parts:
        start = len(content)
        content += text
        regions.append(Region(kind=kind, span=Span(start=start, end=len(content)), text=""))
        content += "\n\n"
    document = SourceDocument(
        id=DOC_ID, revision="rev-1", media_type="text/markdown", content=content
    )
    processed = ProcessedDocument(document_id=DOC_ID, revision="rev-1", regions=tuple(regions))
    return document, processed


def make_dictionary() -> AnchorDictionary:
    """A dictionary with a strong mention, a weak one, a title, and an alias."""
    dictionary = AnchorDictionary(
        AnchorConfig(),
        linked={"paxos": {"topics/paxos": 4}, "rare term": {"topics/rare": 1}},
        titles={"raft consensus": {"topics/raft": 1}},
        aliases={"log replication": {"topics/raft": 1}, "raft": {"topics/raft": 1}},
    )
    # keyphraseness: paxos 4/10 = 0.4 (eligible); rare term 1/100 = 0.01 (not).
    dictionary.attach_occurrences(
        {"paxos": 10, "rare term": 100, "raft consensus": 2, "log replication": 1, "raft": 3}
    )
    return dictionary


def propose(
    parts: Sequence[tuple[RegionKind, str]],
    *,
    relationships: RelationshipSet | None = None,
    processed: ProcessedDocument | None = None,
    config: SpanConfig | None = None,
    dictionary: AnchorDictionary | None = None,
) -> tuple[SourceDocument, tuple[SpanCandidate, ...]]:
    """Build a document from parts and run propose_spans over it."""
    document, default_processed = build_document(parts)
    candidates = propose_spans(
        document,
        processed or default_processed,
        relationships or RelationshipSet(),
        dictionary or make_dictionary(),
        config=config or SpanConfig(),
    )
    return document, candidates


def texts(candidates: Sequence[SpanCandidate]) -> list[str]:
    """The candidate surface texts, in output order."""
    return [candidate.text for candidate in candidates]


def by_text(candidates: Sequence[SpanCandidate], text: str) -> SpanCandidate:
    """The single candidate with the given surface text."""
    matches = [candidate for candidate in candidates if candidate.text == text]
    assert len(matches) == 1, f"expected one candidate {text!r}, got {matches}"
    return matches[0]


class TestSpanConfig:
    def test_defaults_and_fingerprint(self) -> None:
        config = SpanConfig()
        assert config.max_words == 5
        assert config.context_chars == 240
        assert config.allowed_regions == (LinkRegionKind.PROSE, LinkRegionKind.LIST)
        assert config.resolved_dict()["allowed_regions"] == ["prose", "list"]
        assert config.fingerprint() != SpanConfig(max_words=3).fingerprint()


class TestDictionarySource:
    def test_eligible_mention_found_with_raw_span(self) -> None:
        document, candidates = propose([(RegionKind.PROSE, "we compare paxos with others")])
        candidate = by_text(candidates, "paxos")
        assert document.content[candidate.span.start : candidate.span.end] == "paxos"
        assert candidate.region_kind is LinkRegionKind.PROSE
        assert candidate.document_id == DOC_ID

    def test_case_insensitive_match_keeps_raw_text(self) -> None:
        document, candidates = propose([(RegionKind.PROSE, "all about PAXOS here")])
        candidate = by_text(candidates, "PAXOS")
        assert document.content[candidate.span.start : candidate.span.end] == "PAXOS"

    def test_word_boundaries_respected(self) -> None:
        _, candidates = propose([(RegionKind.PROSE, "the paxosy protocol")])
        assert "paxos" not in texts(candidates)

    def test_ineligible_mention_not_proposed(self) -> None:
        _, candidates = propose([(RegionKind.PROSE, "a rare term appears")])
        assert "rare term" not in texts(candidates)

    def test_title_and_alias_matches(self) -> None:
        _, candidates = propose(
            [(RegionKind.PROSE, "see Raft Consensus and log replication details")]
        )
        title = by_text(candidates, "Raft Consensus")
        assert title.features["is_title_match"] == 1.0
        assert title.features["is_alias_match"] == 0.0
        alias = by_text(candidates, "log replication")
        assert alias.features["is_alias_match"] == 1.0
        assert alias.features["is_title_match"] == 0.0

    def test_overlapping_candidates_are_kept(self) -> None:
        # "Raft" (alias) nests inside "Raft Consensus" (title): both proposed,
        # sorted by start then length descending.
        _, candidates = propose([(RegionKind.PROSE, "read Raft Consensus first")])
        long, short = by_text(candidates, "Raft Consensus"), by_text(candidates, "Raft")
        assert long.span.start == short.span.start
        assert candidates.index(long) < candidates.index(short)

    def test_requires_attached_occurrences(self) -> None:
        document, processed = build_document([(RegionKind.PROSE, "paxos")])
        detached = AnchorDictionary(AnchorConfig(), linked={"paxos": {"t": 4}})
        with pytest.raises(ContractError, match="attach_occurrences"):
            propose_spans(document, processed, RelationshipSet(), detached, config=SpanConfig())


class TestTechnicalExtras:
    def test_titlecase_run_acronym_and_hyphenated(self) -> None:
        _, candidates = propose(
            [(RegionKind.PROSE, "using Vector Clocks over TCP avoids head-of-line blocking")]
        )
        run = by_text(candidates, "Vector Clocks")
        assert run.features["is_titlecase"] == 1.0
        assert run.features["keyphraseness"] == 0.0  # unknown to the dictionary
        assert run.features["anchor_count"] == 0.0
        acronym = by_text(candidates, "TCP")
        assert acronym.features["is_acronym"] == 1.0
        assert acronym.features["is_titlecase"] == 0.0
        hyphenated = by_text(candidates, "head-of-line")
        assert hyphenated.features["is_hyphenated"] == 1.0

    def test_surrounding_punctuation_trimmed_from_extras(self) -> None:
        document, candidates = propose([(RegionKind.PROSE, "then (MapReduce), obviously")])
        candidate = by_text(candidates, "MapReduce")
        assert document.content[candidate.span.start : candidate.span.end] == "MapReduce"

    def test_short_acronyms_and_plain_words_are_not_extras(self) -> None:
        _, candidates = propose([(RegionKind.PROSE, "a B plain words only here")])
        assert texts(candidates) == []

    def test_titlecase_run_longer_than_max_words_dropped(self) -> None:
        _, candidates = propose(
            [(RegionKind.PROSE, "the One Two Three Four Five Six Seven story")],
            config=SpanConfig(max_words=5),
        )
        assert texts(candidates) == []


class TestRegionMasking:
    def test_code_heading_table_regions_excluded(self) -> None:
        _, candidates = propose(
            [
                (RegionKind.HEADING, "paxos overview"),
                (RegionKind.CODE, "run(paxos)"),
                (RegionKind.TABLE, "| paxos | 1 |"),
                (RegionKind.METADATA, "title: paxos"),
                (RegionKind.PROSE, "but paxos in prose"),
            ]
        )
        assert texts(candidates) == ["paxos"]
        assert by_text(candidates, "paxos").region_kind is LinkRegionKind.PROSE

    def test_list_regions_allowed(self) -> None:
        _, candidates = propose([(RegionKind.LIST, "- paxos in a list")])
        candidate = by_text(candidates, "paxos")
        assert candidate.region_kind is LinkRegionKind.LIST
        assert candidate.features["region_prose"] == 0.0

    def test_inline_code_and_math_excluded(self) -> None:
        _, candidates = propose([(RegionKind.PROSE, "call `paxos` or $paxos$ but paxos in text")])
        assert texts(candidates) == ["paxos"]

    def test_nested_code_region_wins_over_enclosing_prose(self) -> None:
        document, processed = build_document([(RegionKind.PROSE, "prose with paxos inside")])
        outer = processed.regions[0]
        start = document.content.find("paxos")
        nested = Region(
            kind=RegionKind.CODE, span=Span(start=start, end=start + len("paxos")), text=""
        )
        processed = ProcessedDocument(document_id=DOC_ID, revision="rev-1", regions=(outer, nested))
        candidates = propose_spans(
            document, processed, RelationshipSet(), make_dictionary(), config=SpanConfig()
        )
        assert "paxos" not in texts(candidates)

    def test_related_notes_units_excluded(self) -> None:
        document, processed = build_document(
            [(RegionKind.LIST, "- paxos"), (RegionKind.PROSE, "paxos in prose")]
        )
        list_region = processed.regions[0]
        related_unit = SemanticUnit(
            id=f"{DOC_ID}:related:0",
            document_id=DOC_ID,
            view="section",
            section_path=("Doc", "Related Notes"),
            region_kinds=(RegionKind.LIST,),
            source_spans=(list_region.span,),
            text="",
            token_count=0,
            content_hash="sha256:unit",
        )
        processed = ProcessedDocument(
            document_id=DOC_ID,
            revision="rev-1",
            regions=processed.regions,
            units=(related_unit,),
        )
        candidates = propose_spans(
            document, processed, RelationshipSet(), make_dictionary(), config=SpanConfig()
        )
        assert len(candidates) == 1
        assert candidates[0].region_kind is LinkRegionKind.PROSE


class TestExistingLinkExclusion:
    def test_spans_overlapping_existing_links_are_dropped(self) -> None:
        document, processed = build_document(
            [(RegionKind.PROSE, "first paxos is linked but second paxos is free")]
        )
        first = document.content.find("paxos")
        relationships = RelationshipSet(
            relationships=(
                Relationship(
                    source_id=DOC_ID,
                    target_id="topics/paxos",
                    kind="explicit-link",
                    source_span=Span(start=first, end=first + len("paxos")),
                ),
            )
        )
        candidates = propose_spans(
            document, processed, relationships, make_dictionary(), config=SpanConfig()
        )
        spans = [candidate.span for candidate in candidates if candidate.text == "paxos"]
        assert len(spans) == 1
        assert spans[0].start == document.content.find("paxos", first + 1)

    def test_partial_overlap_also_excluded(self) -> None:
        document, processed = build_document([(RegionKind.PROSE, "about paxos here")])
        start = document.content.find("paxos")
        relationships = RelationshipSet(
            relationships=(
                Relationship(
                    source_id=DOC_ID,
                    target_id="topics/paxos",
                    kind="explicit-link",
                    source_span=Span(start=start + 2, end=start + 20),
                ),
            )
        )
        candidates = propose_spans(
            document, processed, relationships, make_dictionary(), config=SpanConfig()
        )
        assert "paxos" not in texts(candidates)

    def test_other_documents_links_do_not_exclude(self) -> None:
        document, processed = build_document([(RegionKind.PROSE, "about paxos here")])
        start = document.content.find("paxos")
        relationships = RelationshipSet(
            relationships=(
                Relationship(
                    source_id="other/doc",
                    target_id="topics/paxos",
                    kind="explicit-link",
                    source_span=Span(start=start, end=start + len("paxos")),
                ),
            )
        )
        candidates = propose_spans(
            document, processed, relationships, make_dictionary(), config=SpanConfig()
        )
        assert "paxos" in texts(candidates)


class TestFeaturesAndDeterminism:
    def test_hand_checked_feature_vector(self) -> None:
        prose = "an intro sentence then paxos appears"
        _, candidates = propose([(RegionKind.PROSE, prose)])
        candidate = by_text(candidates, "paxos")
        offset = prose.find("paxos")
        assert candidate.features == {
            "keyphraseness": pytest.approx(0.4),  # 4 links / 10 occurrences
            "commonness_top": 1.0,  # single target
            "anchor_count": 4.0,
            "target_count": 1.0,
            "word_count": 1.0,
            "char_count": 5.0,
            "is_title_match": 0.0,
            "is_alias_match": 0.0,
            "is_acronym": 0.0,
            "is_titlecase": 0.0,
            "is_hyphenated": 0.0,
            "sentence_position": pytest.approx(offset / len(prose)),
            "region_prose": 1.0,
        }
        assert candidate.word_count == 1

    def test_unicode_offsets_verified_by_slicing(self) -> None:
        document, candidates = propose(
            [(RegionKind.PROSE, "café notes — naïve 🧠 emoji then paxos wins")]
        )
        candidate = by_text(candidates, "paxos")
        assert document.content[candidate.span.start : candidate.span.end] == "paxos"

    def test_duplicate_sources_merge_into_one_candidate(self) -> None:
        # "Paxos" is a dictionary mention AND a TitleCase extra: one candidate.
        _, candidates = propose([(RegionKind.PROSE, "then Paxos appears")])
        assert texts(candidates).count("Paxos") == 1
        merged = by_text(candidates, "Paxos")
        assert merged.features["keyphraseness"] == pytest.approx(0.4)
        assert merged.features["is_titlecase"] == 1.0

    def test_output_sorted_and_ids_deterministic(self) -> None:
        parts = [(RegionKind.PROSE, "Raft Consensus with paxos and log replication")]
        _, first = propose(parts)
        _, second = propose(parts)
        assert first == second
        keys = [(candidate.span.start, -len(candidate.text)) for candidate in first]
        assert keys == sorted(keys)
        assert all(candidate.id.startswith("sha256:") for candidate in first)
        assert len({candidate.id for candidate in first}) == len(first)

    def test_max_words_config_drops_long_candidates(self) -> None:
        _, candidates = propose(
            [(RegionKind.PROSE, "read Raft Consensus and log replication notes")],
            config=SpanConfig(max_words=1),
        )
        assert "Raft Consensus" not in texts(candidates)
        assert "log replication" not in texts(candidates)
        assert "Raft" in texts(candidates)  # the one-word alias still fits

    def test_unit_id_resolution(self) -> None:
        document, processed = build_document([(RegionKind.PROSE, "prose with paxos inside")])
        prose_region = processed.regions[0]
        unit = SemanticUnit(
            id=f"{DOC_ID}:body:0",
            document_id=DOC_ID,
            view="section",
            section_path=("Doc",),
            region_kinds=(RegionKind.PROSE,),
            source_spans=(prose_region.span,),
            text="",
            token_count=0,
            content_hash="sha256:unit",
        )
        with_units = ProcessedDocument(
            document_id=DOC_ID, revision="rev-1", regions=processed.regions, units=(unit,)
        )
        candidates = propose_spans(
            document, with_units, RelationshipSet(), make_dictionary(), config=SpanConfig()
        )
        assert by_text(candidates, "paxos").unit_id == f"{DOC_ID}:body:0"
        without_units = propose_spans(
            document, processed, RelationshipSet(), make_dictionary(), config=SpanConfig()
        )
        assert by_text(without_units, "paxos").unit_id is None


def make_audit_item(
    item_id: str,
    span: Span | None,
    *,
    doc_id: str = DOC_ID,
    region_kind: LinkRegionKind = LinkRegionKind.PROSE,
) -> AuditItem:
    """A minimal audit item for recall computation."""
    return AuditItem(
        id=item_id,
        source_document_id=doc_id,
        target_document_id="topics/t",
        anchor_text="anchor",
        source_span=span,
        region_kind=region_kind,
        context="",
        anchor_word_count=1,
        topic_family="topics",
        strata_key="prose|1|topics|note",
    )


def make_candidate(span: Span, *, doc_id: str = DOC_ID) -> SpanCandidate:
    """A minimal span candidate covering ``span``."""
    return SpanCandidate(
        id=f"cand-{doc_id}-{span.start}-{span.end}",
        document_id=doc_id,
        unit_id=None,
        span=span,
        text="x",
        region_kind=LinkRegionKind.PROSE,
        word_count=1,
        features={},
    )


class TestSpanRecall:
    def test_exact_and_overlap_variants_hand_computed(self) -> None:
        items = [
            make_audit_item("exact", Span(start=10, end=20)),
            make_audit_item("partial", Span(start=30, end=40)),
            make_audit_item("missed", Span(start=50, end=60)),
        ]
        candidates = {
            DOC_ID: [
                make_candidate(Span(start=10, end=20)),  # exact
                make_candidate(Span(start=32, end=40)),  # covers 8/10 = 80%
                make_candidate(Span(start=58, end=60)),  # covers 2/10, misses
            ]
        }
        result = span_recall(items, candidates)
        assert result == {
            "exact_recall": pytest.approx(1 / 3),
            "overlap_recall": pytest.approx(2 / 3),
            "n_prose_items": 3.0,
        }

    def test_coverage_just_below_threshold_not_counted(self) -> None:
        items = [make_audit_item("partial", Span(start=30, end=40))]
        candidates = {DOC_ID: [make_candidate(Span(start=33, end=40))]}  # 7/10
        result = span_recall(items, candidates)
        assert result["overlap_recall"] == 0.0

    def test_only_prose_items_with_spans_count(self) -> None:
        items = [
            make_audit_item("prose", Span(start=10, end=20)),
            make_audit_item("heading", Span(start=10, end=20), region_kind=LinkRegionKind.HEADING),
            make_audit_item("spanless", None),
        ]
        result = span_recall(items, {DOC_ID: [make_candidate(Span(start=10, end=20))]})
        assert result == {"exact_recall": 1.0, "overlap_recall": 1.0, "n_prose_items": 1.0}

    def test_candidates_from_other_documents_do_not_cover(self) -> None:
        items = [make_audit_item("exact", Span(start=10, end=20))]
        candidates = {"other/doc": [make_candidate(Span(start=10, end=20), doc_id="other/doc")]}
        result = span_recall(items, candidates)
        assert result == {"exact_recall": 0.0, "overlap_recall": 0.0, "n_prose_items": 1.0}

    def test_empty_items_yield_zeros(self) -> None:
        assert span_recall([], {}) == {
            "exact_recall": 0.0,
            "overlap_recall": 0.0,
            "n_prose_items": 0.0,
        }
