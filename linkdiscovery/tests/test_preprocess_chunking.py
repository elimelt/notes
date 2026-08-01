"""Tests for the section-aware chunker."""

from __future__ import annotations

import itertools
from collections.abc import Sequence

from linkdiscovery.contracts.units import Region, RegionKind, Span
from linkdiscovery.preprocess import SimpleTokenCounter, UnitDraft, chunk_sections
from tests.test_preprocess_helpers import make_config

COUNTER = SimpleTokenCounter()


def prose(text: str, start: int = 0) -> Region:
    return Region(kind=RegionKind.PROSE, span=Span(start, start + len(text)), text=text)


def code(text: str, start: int = 0) -> Region:
    return Region(kind=RegionKind.CODE, span=Span(start, start + len(text)), text=text)


def boilerplate(text: str, start: int = 0) -> Region:
    return Region(kind=RegionKind.BOILERPLATE, span=Span(start, start + len(text)), text=text)


def heading(text: str, level: int | None = None, start: int = 0) -> Region:
    metadata: dict[str, object] = {"level": level} if level is not None else {}
    return Region(
        kind=RegionKind.HEADING,
        span=Span(start, start + len(text)),
        text=text,
        metadata=metadata,
    )


def words(n: int, prefix: str = "w") -> str:
    return " ".join(f"{prefix}{i}" for i in range(n))


class TestSectionPaths:
    def test_nested_heading_levels(self) -> None:
        regions = [
            heading("Alpha", level=1),
            prose("alpha text"),
            heading("Beta", level=2),
            prose("beta text"),
            heading("Gamma", level=1),
            prose("gamma text"),
        ]
        drafts = chunk_sections("Title", regions, make_config(), COUNTER)
        assert [d.section_path for d in drafts] == [("Alpha",), ("Alpha", "Beta"), ("Gamma",)]

    def test_sibling_heading_replaces_same_level(self) -> None:
        regions = [
            heading("A", level=1),
            heading("A1", level=2),
            prose("one"),
            heading("A2", level=2),
            prose("two"),
        ]
        drafts = chunk_sections("", regions, make_config(), COUNTER)
        assert [d.section_path for d in drafts] == [("A", "A1"), ("A", "A2")]

    def test_headings_without_level_default_to_level_one(self) -> None:
        regions = [heading("First"), prose("one"), heading("Second"), prose("two")]
        drafts = chunk_sections("", regions, make_config(), COUNTER)
        assert [d.section_path for d in drafts] == [("First",), ("Second",)]

    def test_content_before_any_heading_has_empty_path(self) -> None:
        regions = [prose("intro"), heading("Later", level=1), prose("body")]
        drafts = chunk_sections("", regions, make_config(), COUNTER)
        assert drafts[0].section_path == ()
        assert drafts[1].section_path == ("Later",)


class TestContext:
    def test_context_prefix_carries_title_and_path(self) -> None:
        regions = [heading("Section", level=1), heading("Sub", level=2), prose("body words")]
        drafts = chunk_sections("Title", regions, make_config(), COUNTER)
        assert drafts[0].text == "Title > Section > Sub\n\nbody words"

    def test_no_context_without_title_or_headings(self) -> None:
        drafts = chunk_sections("", [prose("just body")], make_config(), COUNTER)
        assert drafts[0].text == "just body"

    def test_context_counted_in_token_accounting(self) -> None:
        regions = [heading("Section", level=1), prose("body words")]
        (draft,) = chunk_sections("Title", regions, make_config(), COUNTER)
        assert draft.token_count == COUNTER.count_tokens(draft.text)
        assert draft.token_count > COUNTER.count_tokens("body words")


class TestSplitting:
    def test_group_within_max_stays_whole_even_above_target(self) -> None:
        config = make_config(target_tokens=8, max_tokens=32, overlap_tokens=2)
        regions = [prose(words(10)), prose(words(10, "x"))]
        drafts = chunk_sections("", regions, config, COUNTER)
        assert len(drafts) == 1

    def test_oversized_group_splits_at_region_boundaries_first(self) -> None:
        config = make_config(target_tokens=12, max_tokens=15, overlap_tokens=2)
        texts = [words(10, "a"), words(10, "b"), words(10, "c")]
        drafts = chunk_sections("", [prose(t) for t in texts], config, COUNTER)
        assert [d.text for d in drafts] == texts

    def test_oversized_region_splits_at_paragraph_boundaries(self) -> None:
        config = make_config(target_tokens=12, max_tokens=15, overlap_tokens=4)
        paragraph_a, paragraph_b = words(10, "a"), words(10, "b")
        region = prose(f"{paragraph_a}\n\n{paragraph_b}")
        drafts = chunk_sections("", [region], config, COUNTER)
        # Paragraph boundaries are semantic breaks: split there, no overlap.
        assert [d.text for d in drafts] == [paragraph_a, paragraph_b]

    def test_all_chunks_respect_max_tokens(self) -> None:
        config = make_config(target_tokens=16, max_tokens=24, overlap_tokens=4)
        regions = [
            heading("Big Section", level=1),
            prose(words(100)),
            prose(f"{words(30, 'p')}\n\n{words(30, 'q')}"),
            code(words(50, "c")),
        ]
        drafts = chunk_sections("Doc", regions, config, COUNTER)
        assert len(drafts) > 1
        for draft in drafts:
            assert draft.token_count <= config.max_tokens
            assert draft.token_count == COUNTER.count_tokens(draft.text)


class TestOverlap:
    def _bodies(self, drafts: Sequence[UnitDraft], context: str) -> list[str]:
        prefix = f"{context}\n\n" if context else ""
        return [d.text.removeprefix(prefix) for d in drafts]

    def test_word_splits_of_continuous_prose_overlap(self) -> None:
        config = make_config(target_tokens=16, max_tokens=20, overlap_tokens=4)
        drafts = chunk_sections("T", [prose(words(40))], config, COUNTER)
        bodies = self._bodies(drafts, "T")
        assert len(bodies) >= 2
        for previous, current in itertools.pairwise(bodies):
            overlap_words = current.split()[:4]
            assert previous.split()[-4:] == overlap_words

    def test_non_prose_splits_get_no_overlap(self) -> None:
        config = make_config(target_tokens=16, max_tokens=20, overlap_tokens=4)
        original = words(40, "c")
        drafts = chunk_sections("T", [code(original)], config, COUNTER)
        bodies = self._bodies(drafts, "T")
        assert len(bodies) >= 2
        assert " ".join(" ".join(body.split()) for body in bodies) == original

    def test_zero_overlap_config_produces_no_overlap(self) -> None:
        config = make_config(target_tokens=16, max_tokens=20, overlap_tokens=0)
        original = words(40)
        drafts = chunk_sections("", [prose(original)], config, COUNTER)
        bodies = self._bodies(drafts, "")
        assert " ".join(" ".join(body.split()) for body in bodies) == original


class TestRegionPolicy:
    def test_excluded_regions_omitted_from_text_and_kinds(self) -> None:
        regions = [prose("keep this"), boilerplate("drop this"), prose("keep too")]
        drafts = chunk_sections("", regions, make_config(), COUNTER)
        assert len(drafts) == 1
        assert "drop this" not in drafts[0].text
        assert RegionKind.BOILERPLATE not in drafts[0].region_kinds

    def test_region_kinds_accurate_for_included_content(self) -> None:
        regions = [prose("some prose"), code("some code")]
        (draft,) = chunk_sections("", regions, make_config(), COUNTER)
        assert draft.region_kinds == (RegionKind.PROSE, RegionKind.CODE)

    def test_source_spans_cover_included_regions(self) -> None:
        first, second = prose("one two", start=0), prose("three four", start=20)
        (draft,) = chunk_sections("", [first, second], make_config(), COUNTER)
        assert draft.source_spans == (first.span, second.span)

    def test_title_regions_skipped_as_body(self) -> None:
        title_region = Region(kind=RegionKind.TITLE, span=Span(0, 0), text="The Title")
        drafts = chunk_sections("The Title", [title_region, prose("body")], make_config(), COUNTER)
        assert len(drafts) == 1
        assert drafts[0].text == "The Title\n\nbody"

    def test_heading_only_section_yields_no_chunk(self) -> None:
        drafts = chunk_sections("", [heading("Lonely", level=1)], make_config(), COUNTER)
        assert drafts == []

    def test_empty_and_whitespace_regions_skipped(self) -> None:
        drafts = chunk_sections("", [prose("  \n "), prose("real")], make_config(), COUNTER)
        assert len(drafts) == 1
        assert drafts[0].text == "real"


class TestDeterminism:
    def test_identical_inputs_identical_output(self) -> None:
        config = make_config(target_tokens=12, max_tokens=16, overlap_tokens=3)
        regions = [heading("S", level=1), prose(words(40)), code(words(20, "c"))]
        first = chunk_sections("T", regions, config, COUNTER)
        second = chunk_sections("T", regions, config, COUNTER)
        assert first == second
