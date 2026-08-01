"""Tests for the plain-text region parser."""

from __future__ import annotations

from linkdiscovery.contracts.units import RegionKind, Span
from linkdiscovery.preprocess import PlainTextParser
from tests.test_preprocess_helpers import make_config, make_document


class TestPlainTextParser:
    def test_title_region_emitted_first(self) -> None:
        document = make_document(content="Body text.", title="My Title")
        regions = PlainTextParser().parse(document, make_config())
        assert regions[0].kind is RegionKind.TITLE
        assert regions[0].span == Span(0, 0)
        assert regions[0].text == "My Title"

    def test_no_title_region_without_title(self) -> None:
        document = make_document(content="Body text.", title="")
        regions = PlainTextParser().parse(document, make_config())
        assert all(region.kind is not RegionKind.TITLE for region in regions)

    def test_paragraphs_split_on_blank_lines(self) -> None:
        content = "First para line one\nline two.\n\nSecond para.\n\n\nThird para."
        document = make_document(content=content, title="")
        regions = PlainTextParser().parse(document, make_config())
        assert [region.kind for region in regions] == [RegionKind.PROSE] * 3
        assert regions[0].text == "First para line one\nline two."
        assert regions[1].text == "Second para."
        assert regions[2].text == "Third para."

    def test_spans_index_original_raw_content(self) -> None:
        content = "Alpha one.\r\n\r\nBeta two.\r\nstill beta.\r\n"
        document = make_document(content=content, title="T")
        regions = PlainTextParser().parse(document, make_config())
        for region in regions[1:]:
            assert content[region.span.start : region.span.end] == region.text

    def test_whitespace_only_lines_are_blank(self) -> None:
        content = "para one\n   \t\npara two"
        document = make_document(content=content, title="")
        regions = PlainTextParser().parse(document, make_config())
        assert [region.text for region in regions] == ["para one", "para two"]

    def test_empty_and_whitespace_content(self) -> None:
        parser = PlainTextParser()
        assert parser.parse(make_document(content="", title=""), make_config()) == []
        assert parser.parse(make_document(content="  \n \n", title=""), make_config()) == []

    def test_unknown_media_type_treated_as_plain_text(self) -> None:
        document = make_document(
            content="Some content.", title="", media_type="application/x-unknown"
        )
        regions = PlainTextParser().parse(document, make_config())
        assert len(regions) == 1
        assert regions[0].kind is RegionKind.PROSE

    def test_deterministic(self) -> None:
        document = make_document(content="a\n\nb\n\nc", title="T")
        parser = PlainTextParser()
        config = make_config()
        assert parser.parse(document, config) == parser.parse(document, config)

    def test_fingerprint_versioned(self) -> None:
        assert PlainTextParser().fingerprint == "plain-text-parser:v1"
