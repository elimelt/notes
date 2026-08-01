"""Stratified audit sampling: enumeration, strata, determinism."""

from __future__ import annotations

from typing import Any

from linkdiscovery.contracts import (
    Corpus,
    ProcessedCorpus,
    ProcessedDocument,
    Region,
    RegionKind,
    Relationship,
    RelationshipSet,
    SemanticUnit,
    SourceDocument,
    Span,
)
from linkdiscovery.inline import AuditItem, LinkRegionKind, build_audit_sample
from tests.conftest import make_header


def make_document(doc_id: str, content: str) -> SourceDocument:
    """A minimal source document."""
    return SourceDocument(id=doc_id, revision="rev-1", media_type="text/markdown", content=content)


def make_link(
    source_id: str,
    target_id: str,
    span: Span | None,
    *,
    kind: str = "explicit-link",
    metadata: dict[str, Any] | None = None,
) -> Relationship:
    """An explicit-link relationship with an optional span and metadata."""
    return Relationship(
        source_id=source_id,
        target_id=target_id,
        kind=kind,
        source_span=span,
        metadata=metadata or {},
    )


def make_corpus(documents: list[SourceDocument], relationships: list[Relationship]) -> Corpus:
    """A corpus wrapping the given documents and relationships."""
    return Corpus(
        header=make_header(),
        documents=tuple(documents),
        relationships=RelationshipSet(relationships=tuple(relationships)),
    )


def make_processed(documents: list[ProcessedDocument]) -> ProcessedCorpus:
    """A processed corpus wrapping the given processed documents."""
    return ProcessedCorpus(
        header=make_header(),
        preprocessing_fingerprint="sha256:preproc",
        documents=tuple(documents),
    )


def region(kind: RegionKind, start: int, end: int) -> Region:
    """A typed region over [start, end)."""
    return Region(kind=kind, span=Span(start=start, end=end), text="")


def related_notes_unit(doc_id: str, start: int, end: int) -> SemanticUnit:
    """A unit inside a section whose heading path ends in 'Related Notes'."""
    return SemanticUnit(
        id=f"{doc_id}:related:0",
        document_id=doc_id,
        view="section",
        section_path=("Doc", "Related Notes"),
        region_kinds=(RegionKind.LIST,),
        source_spans=(Span(start=start, end=end),),
        text="",
        token_count=0,
        content_hash="sha256:unit",
    )


def item_by_span_start(items: tuple[AuditItem, ...], start: int) -> AuditItem:
    """The single sampled item whose source span begins at ``start``."""
    matches = [item for item in items if item.source_span and item.source_span.start == start]
    assert len(matches) == 1
    return matches[0]


class TestEnumeration:
    def test_only_resolvable_explicit_links_with_spans_are_sampled(self) -> None:
        docs = [make_document("a", "x" * 100), make_document("b", "y" * 100)]
        relationships = [
            make_link("a", "b", Span(start=10, end=20)),  # kept
            make_link("a", "b", None),  # no span
            make_link("a", "missing", Span(start=10, end=20)),  # unresolved target
            make_link("missing", "b", Span(start=10, end=20)),  # unresolved source
            make_link("a", "b", Span(start=30, end=40), kind="unresolved-link"),  # wrong kind
        ]
        sample = build_audit_sample(
            make_corpus(docs, relationships), make_processed([]), size=100, seed=1
        )
        assert len(sample.items) == 1
        assert sample.items[0].source_span == Span(start=10, end=20)

    def test_duplicate_source_target_span_triples_collapse(self) -> None:
        docs = [make_document("a", "x" * 100), make_document("b", "y" * 100)]
        link = make_link("a", "b", Span(start=10, end=20))
        sample = build_audit_sample(
            make_corpus(docs, [link, link]), make_processed([]), size=100, seed=1
        )
        assert len(sample.items) == 1

    def test_empty_corpus_yields_empty_sample(self) -> None:
        sample = build_audit_sample(make_corpus([], []), make_processed([]), size=150, seed=1)
        assert sample.items == ()
        assert sample.strata_counts == {}


class TestItemDerivation:
    def test_region_kind_from_smallest_containing_region(self) -> None:
        content = "z" * 300
        docs = [make_document("src", content), make_document("t/a", "target")]
        processed = make_processed(
            [
                ProcessedDocument(
                    document_id="src",
                    revision="rev-1",
                    regions=(
                        region(RegionKind.PROSE, 0, 300),  # encloses everything
                        region(RegionKind.CODE, 0, 100),
                        region(RegionKind.HEADING, 100, 150),
                        region(RegionKind.LIST, 220, 260),
                    ),
                    units=(related_notes_unit("src", 220, 260),),
                )
            ]
        )
        relationships = [
            make_link("src", "t/a", Span(start=10, end=20)),  # inside code
            make_link("src", "t/a", Span(start=110, end=120)),  # inside heading
            make_link("src", "t/a", Span(start=200, end=210)),  # only outer prose
            make_link("src", "t/a", Span(start=230, end=240)),  # related-notes unit
        ]
        sample = build_audit_sample(make_corpus(docs, relationships), processed, size=100, seed=1)
        assert item_by_span_start(sample.items, 10).region_kind == LinkRegionKind.CODE
        assert item_by_span_start(sample.items, 110).region_kind == LinkRegionKind.HEADING
        assert item_by_span_start(sample.items, 200).region_kind == LinkRegionKind.PROSE
        assert item_by_span_start(sample.items, 230).region_kind == LinkRegionKind.RELATED_NOTES

    def test_document_without_processed_form_defaults_to_prose(self) -> None:
        docs = [make_document("src", "plain text link here"), make_document("t/a", "t")]
        sample = build_audit_sample(
            make_corpus(docs, [make_link("src", "t/a", Span(start=11, end=15))]),
            make_processed([]),
            size=10,
            seed=1,
        )
        assert sample.items[0].region_kind == LinkRegionKind.PROSE

    def test_anchor_text_prefers_relationship_metadata(self) -> None:
        content = "see the MapReduce paper for details"
        docs = [make_document("src", content), make_document("t/a", "t")]
        span = Span(start=8, end=17)  # "MapReduce"
        relationships = [
            make_link("src", "t/a", span),
            make_link(
                "src",
                "t/a",
                Span(start=22, end=27),
                metadata={"anchor_text": "one two three four five"},
            ),
        ]
        sample = build_audit_sample(
            make_corpus(docs, relationships), make_processed([]), size=10, seed=1
        )
        sliced = item_by_span_start(sample.items, 8)
        assert sliced.anchor_text == "MapReduce"
        assert sliced.anchor_word_count == 1
        from_metadata = item_by_span_start(sample.items, 22)
        assert from_metadata.anchor_text == "one two three four five"
        assert from_metadata.anchor_word_count == 5
        assert from_metadata.strata_key == "prose|4+|t|note"

    def test_context_window_is_collapsed_and_ellipsized(self) -> None:
        content = "x" * 500 + "  hello\n\n  world  " + "y" * 500
        docs = [make_document("src", content), make_document("t/a", "t")]
        span = Span(start=502, end=507)  # "hello"
        sample = build_audit_sample(
            make_corpus(docs, [make_link("src", "t/a", span)]),
            make_processed([]),
            size=10,
            seed=1,
        )
        context = sample.items[0].context
        assert context.startswith("...")
        assert context.endswith("...")
        assert "hello world" in context
        assert "\n" not in context

    def test_short_document_context_has_no_ellipsis(self) -> None:
        docs = [make_document("src", "tiny hello doc"), make_document("t/a", "t")]
        sample = build_audit_sample(
            make_corpus(docs, [make_link("src", "t/a", Span(start=5, end=10))]),
            make_processed([]),
            size=10,
            seed=1,
        )
        assert sample.items[0].context == "tiny hello doc"

    def test_topic_family_and_index_source_fold_into_strata_key(self) -> None:
        docs = [
            make_document("index", "root index page linking out"),
            make_document("networks/index", "section index page too"),
            make_document("networks/tcp", "leaf note content here"),
        ]
        relationships = [
            make_link("index", "networks/tcp", Span(start=0, end=4)),
            make_link("networks/index", "networks/tcp", Span(start=0, end=7)),
            make_link("networks/tcp", "networks/index", Span(start=0, end=4)),
        ]
        sample = build_audit_sample(
            make_corpus(docs, relationships), make_processed([]), size=10, seed=1
        )
        by_source = {item.source_document_id: item for item in sample.items}
        assert by_source["index"].strata_key == "prose|1|networks|index"
        assert by_source["networks/index"].strata_key == "prose|1|networks|index"
        assert by_source["networks/tcp"].strata_key == "prose|1|networks|note"
        assert by_source["index"].topic_family == "networks"


def make_two_strata_inputs() -> Corpus:
    """A corpus with 30 one-word-anchor links and 10 two-word-anchor links."""
    content = "alpha beta " * 200
    docs = [make_document("notes/src", content), make_document("topics/t", "target")]
    relationships = [
        make_link("notes/src", "topics/t", Span(start=i * 11, end=i * 11 + 5)) for i in range(30)
    ] + [
        make_link(
            "notes/src",
            "topics/t",
            Span(start=1000 + i * 11, end=1000 + i * 11 + 5),
            metadata={"anchor_text": "alpha beta"},
        )
        for i in range(10)
    ]
    return make_corpus(docs, relationships)


class TestStratification:
    def test_proportional_allocation_with_floor(self) -> None:
        sample = build_audit_sample(make_two_strata_inputs(), make_processed([]), size=8, seed=7)
        assert len(sample.items) == 8
        assert sample.strata_counts == {
            "prose|1|topics|note": 6,
            "prose|2-3|topics|note": 2,
        }

    def test_floor_of_one_keeps_tiny_strata_represented(self) -> None:
        content = "alpha beta " * 200
        docs = [make_document("notes/src", content), make_document("topics/t", "target")]
        relationships = [
            make_link("notes/src", "topics/t", Span(start=i * 11, end=i * 11 + 5))
            for i in range(50)
        ] + [
            make_link(
                "notes/src",
                "topics/t",
                Span(start=1000, end=1005),
                metadata={"anchor_text": "alpha beta"},
            )
        ]
        sample = build_audit_sample(
            make_corpus(docs, relationships), make_processed([]), size=5, seed=3
        )
        assert sample.strata_counts["prose|2-3|topics|note"] == 1
        assert sample.strata_counts["prose|1|topics|note"] == 4

    def test_size_beyond_available_returns_everything(self) -> None:
        sample = build_audit_sample(make_two_strata_inputs(), make_processed([]), size=150, seed=7)
        assert len(sample.items) == 40
        assert sum(sample.strata_counts.values()) == 40

    def test_same_seed_is_deterministic(self) -> None:
        corpus = make_two_strata_inputs()
        first = build_audit_sample(corpus, make_processed([]), size=8, seed=42)
        second = build_audit_sample(corpus, make_processed([]), size=8, seed=42)
        assert [item.id for item in first.items] == [item.id for item in second.items]
        assert first.strata_counts == second.strata_counts

    def test_different_seeds_draw_different_subsets(self) -> None:
        corpus = make_two_strata_inputs()
        seeds = {
            tuple(
                item.id
                for item in build_audit_sample(corpus, make_processed([]), size=8, seed=seed).items
            )
            for seed in range(5)
        }
        assert len(seeds) > 1

    def test_output_is_ordered_by_strata_key_then_id(self) -> None:
        sample = build_audit_sample(make_two_strata_inputs(), make_processed([]), size=8, seed=42)
        keys = [(item.strata_key, item.id) for item in sample.items]
        assert keys == sorted(keys)

    def test_item_ids_are_stable_fingerprints(self) -> None:
        corpus = make_two_strata_inputs()
        first = build_audit_sample(corpus, make_processed([]), size=150, seed=1)
        second = build_audit_sample(corpus, make_processed([]), size=150, seed=99)
        assert {item.id for item in first.items} == {item.id for item in second.items}

    def test_header_records_run_and_corpus(self) -> None:
        sample = build_audit_sample(
            make_two_strata_inputs(), make_processed([]), size=8, seed=1, run_id="audit-1"
        )
        assert sample.header.run_id == "audit-1"
        assert sample.header.corpus_id == "corpus-alpha"
        assert sample.header.schema_version == 1
