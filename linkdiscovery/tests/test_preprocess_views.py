"""Tests for the retrieval-view builders and unit identity assignment."""

from __future__ import annotations

import re

import pytest

from linkdiscovery.contracts.units import Region, RegionKind, Span
from linkdiscovery.errors import PreprocessError
from linkdiscovery.fingerprint import fingerprint
from linkdiscovery.preprocess import (
    SimpleTokenCounter,
    UnitDraft,
    assign_unit_ids,
    build_document_view,
    build_title_view,
    build_views,
)
from tests.test_preprocess_helpers import make_config, make_document

COUNTER = SimpleTokenCounter()


def prose(text: str, start: int = 0) -> Region:
    return Region(kind=RegionKind.PROSE, span=Span(start, start + len(text)), text=text)


def heading(text: str, level: int = 1, start: int = 0) -> Region:
    return Region(
        kind=RegionKind.HEADING,
        span=Span(start, start + len(text)),
        text=text,
        metadata={"level": level},
    )


class TestDocumentView:
    def test_assembles_title_metadata_headings_then_body(self) -> None:
        document = make_document(title="T", metadata={"description": "About things"})
        regions = [heading("H1"), prose("first body", start=10), heading("H2", start=30)]
        draft = build_document_view(document, regions, make_config(), COUNTER)
        assert draft is not None
        assert draft.text == "T\n\nAbout things\n\nH1\n\nH2\n\nfirst body"
        assert draft.view == "document"
        assert draft.section_path == ()
        assert draft.region_kinds == (
            RegionKind.TITLE,
            RegionKind.METADATA,
            RegionKind.HEADING,
            RegionKind.PROSE,
        )

    def test_truncates_at_region_boundaries_to_max_tokens(self) -> None:
        config = make_config(target_tokens=8, max_tokens=8, overlap_tokens=2)
        document = make_document(title="Title")
        regions = [prose("one two three four"), prose("five six seven eight"), prose("nine ten")]
        draft = build_document_view(document, regions, config, COUNTER)
        assert draft is not None
        assert draft.token_count <= config.max_tokens
        # Truncation drops whole regions: text is title plus the first region only.
        assert draft.text == "Title\n\none two three four"
        assert draft.source_spans == (Span(0, 0), regions[0].span)

    def test_metadata_allowlist_is_configurable(self) -> None:
        document = make_document(
            title="T", metadata={"description": "ignored", "summary": "chosen"}
        )
        draft = build_document_view(
            document, [], make_config(), COUNTER, metadata_keys=("summary",)
        )
        assert draft is not None
        assert "chosen" in draft.text
        assert "ignored" not in draft.text

    def test_non_string_metadata_values_skipped(self) -> None:
        document = make_document(title="T", metadata={"description": ["not", "a", "string"]})
        draft = build_document_view(document, [], make_config(), COUNTER)
        assert draft is not None
        assert draft.text == "T"

    def test_excluded_regions_skipped(self) -> None:
        document = make_document(title="T")
        regions = [
            Region(kind=RegionKind.BOILERPLATE, span=Span(0, 4), text="junk"),
            prose("real content", start=6),
        ]
        draft = build_document_view(document, regions, make_config(), COUNTER)
        assert draft is not None
        assert "junk" not in draft.text

    def test_empty_document_yields_none(self) -> None:
        document = make_document(title="", metadata={})
        assert build_document_view(document, [], make_config(), COUNTER) is None


class TestTitleView:
    def test_title_aliases_and_description(self) -> None:
        document = make_document(
            title="Main Title",
            metadata={"aliases": ["Alias One", "Alias Two"], "description": "A doc."},
        )
        draft = build_title_view(document, make_config(), COUNTER)
        assert draft is not None
        assert draft.text == "Main Title\nAlias One\nAlias Two\nA doc."
        assert draft.view == "title"
        assert draft.region_kinds == (RegionKind.TITLE, RegionKind.METADATA)
        assert draft.source_spans == (Span(0, 0),)

    def test_malformed_aliases_ignored(self) -> None:
        document = make_document(title="T", metadata={"aliases": [42, "", "  ", "Good"]})
        draft = build_title_view(document, make_config(), COUNTER)
        assert draft is not None
        assert draft.text == "T\nGood"

    def test_aliases_must_be_a_list(self) -> None:
        document = make_document(title="T", metadata={"aliases": "not-a-list"})
        draft = build_title_view(document, make_config(), COUNTER)
        assert draft is not None
        assert draft.text == "T"

    def test_nothing_to_say_yields_none(self) -> None:
        document = make_document(title="", metadata={})
        assert build_title_view(document, make_config(), COUNTER) is None


class TestBuildViews:
    def test_only_configured_views_built(self) -> None:
        document = make_document(title="T", metadata={"description": "D"})
        regions = [prose("body")]
        drafts = build_views(document, regions, make_config(views=("title",)), COUNTER)
        assert [draft.view for draft in drafts] == ["title"]

    def test_view_order_follows_config(self) -> None:
        document = make_document(title="T")
        regions = [prose("body")]
        drafts = build_views(
            document, regions, make_config(views=("title", "section", "document")), COUNTER
        )
        assert [draft.view for draft in drafts] == ["title", "section", "document"]

    def test_unknown_view_raises_naming_document(self) -> None:
        document = make_document(doc_id="doc-x", title="T")
        with pytest.raises(PreprocessError, match=r"doc-x.*bogus"):
            build_views(document, [], make_config(views=("bogus",)), COUNTER)


class TestUnitIdentity:
    def _draft(self, text: str, view: str = "section", path: tuple[str, ...] = ()) -> UnitDraft:
        return UnitDraft(
            view=view,
            section_path=path,
            region_kinds=(RegionKind.PROSE,),
            source_spans=(Span(0, len(text)),),
            text=text,
            token_count=COUNTER.count_tokens(text),
        )

    def test_id_format(self) -> None:
        (unit,) = assign_unit_ids("doc-a", [self._draft("hello world")])
        assert re.fullmatch(r"doc-a#section#[0-9a-f]{12}", unit.id)

    def test_content_hash_is_full_fingerprint_of_text(self) -> None:
        (unit,) = assign_unit_ids("doc-a", [self._draft("hello world")])
        assert unit.content_hash == fingerprint("hello world")

    def test_identity_ignores_spans(self) -> None:
        draft_a = self._draft("same text")
        draft_b = UnitDraft(
            view=draft_a.view,
            section_path=draft_a.section_path,
            region_kinds=draft_a.region_kinds,
            source_spans=(Span(500, 509),),
            text=draft_a.text,
            token_count=draft_a.token_count,
        )
        (unit_a,) = assign_unit_ids("doc-a", [draft_a])
        (unit_b,) = assign_unit_ids("doc-a", [draft_b])
        assert unit_a.id == unit_b.id
        assert unit_a.content_hash == unit_b.content_hash

    def test_identity_depends_on_view_path_and_text(self) -> None:
        base = self._draft("text", view="section", path=("A",))
        (unit,) = assign_unit_ids("d", [base])
        (other_view,) = assign_unit_ids("d", [self._draft("text", view="document", path=("A",))])
        (other_path,) = assign_unit_ids("d", [self._draft("text", view="section", path=("B",))])
        (other_text,) = assign_unit_ids("d", [self._draft("other", view="section", path=("A",))])
        assert len({unit.id, other_view.id, other_path.id, other_text.id}) == 4

    def test_collisions_get_deterministic_positional_suffixes(self) -> None:
        drafts = [self._draft("dup"), self._draft("dup"), self._draft("dup")]
        units = assign_unit_ids("doc-a", drafts)
        assert units[0].id == units[1].id.removesuffix("~1")
        assert units[1].id.endswith("~1")
        assert units[2].id.endswith("~2")
        assert len({unit.id for unit in units}) == 3
