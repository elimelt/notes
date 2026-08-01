"""Region-by-region tests for the Markdown region parser.

Every structural claim is verified two ways: the region's typed fields and
its span sliced back out of the raw content. Inline-cleanup tests include
the no-token-concatenation property: marker stripping never joins tokens
that were separated in the source.
"""

from __future__ import annotations

import pytest

from linkdiscovery.config import PreprocessConfig
from linkdiscovery.contracts.documents import SourceDocument
from linkdiscovery.contracts.units import Region, RegionKind
from linkdiscovery_markdown._syntax import clean_inline
from linkdiscovery_markdown.parser import MarkdownRegionParser

CONFIG = PreprocessConfig(parser="linkdiscovery_markdown.parser:MarkdownRegionParser")


def make_document(content: str) -> SourceDocument:
    return SourceDocument(id="doc", revision="rev-1", media_type="text/markdown", content=content)


def parse(content: str) -> list[Region]:
    return MarkdownRegionParser().parse(make_document(content), CONFIG)


def kinds(regions: list[Region]) -> list[RegionKind]:
    return [region.kind for region in regions]


def slice_of(content: str, region: Region) -> str:
    return content[region.span.start : region.span.end]


class TestFrontmatter:
    def test_frontmatter_becomes_metadata_region_with_exact_span(self) -> None:
        content = "---\ntitle: T\ntags: [a, b]\n---\n\nBody prose.\n"
        regions = parse(content)
        assert regions[0].kind is RegionKind.METADATA
        assert slice_of(content, regions[0]) == "---\ntitle: T\ntags: [a, b]\n---\n"
        assert regions[0].text == "title: T\ntags: [a, b]"

    def test_no_frontmatter_no_metadata_region(self) -> None:
        regions = parse("Just prose.\n")
        assert kinds(regions) == [RegionKind.PROSE]

    def test_malformed_yaml_still_yields_metadata_region(self) -> None:
        content = "---\ntitle: [unclosed\n---\n\nBody.\n"
        regions = parse(content)
        assert regions[0].kind is RegionKind.METADATA
        assert regions[1].kind is RegionKind.PROSE


class TestHeadings:
    def test_levels_and_metadata(self) -> None:
        content = "# One\n\n## Two\n\n###### Six\n"
        regions = parse(content)
        assert kinds(regions) == [RegionKind.HEADING] * 3
        assert [region.metadata["level"] for region in regions] == [1, 2, 6]
        assert [region.text for region in regions] == ["One", "Two", "Six"]

    def test_span_covers_raw_heading_line(self) -> None:
        content = "intro\n\n## Foo **bar** ##\n"
        regions = parse(content)
        heading = regions[1]
        assert heading.kind is RegionKind.HEADING
        assert slice_of(content, heading) == "## Foo **bar** ##"
        assert heading.text == "Foo bar"


class TestBoilerplateTitle:
    CONTENT = "---\ntitle: My Note\n---\n\n# My  NOTE\n\n## Details\n\nProse.\n"

    def test_leading_h1_matching_frontmatter_title_is_boilerplate(self) -> None:
        regions = parse(self.CONTENT)
        assert kinds(regions) == [
            RegionKind.METADATA,
            RegionKind.BOILERPLATE,
            RegionKind.HEADING,
            RegionKind.PROSE,
        ]
        boilerplate = regions[1]
        assert boilerplate.metadata == {"level": 1}
        assert boilerplate.text == "My  NOTE"  # text kept, only the kind changes
        assert slice_of(self.CONTENT, boilerplate) == "# My  NOTE"

    def test_h1_differing_from_title_stays_heading(self) -> None:
        regions = parse("---\ntitle: My Note\n---\n\n# Another Thing\n")
        assert kinds(regions) == [RegionKind.METADATA, RegionKind.HEADING]

    def test_h1_after_content_stays_heading(self) -> None:
        regions = parse("---\ntitle: My Note\n---\n\nLead-in prose.\n\n# My Note\n")
        assert kinds(regions) == [RegionKind.METADATA, RegionKind.PROSE, RegionKind.HEADING]

    def test_h1_without_frontmatter_stays_heading(self) -> None:
        regions = parse("# My Note\n\nProse.\n")
        assert kinds(regions) == [RegionKind.HEADING, RegionKind.PROSE]


class TestCode:
    def test_fenced_block_is_code_with_verbatim_text(self) -> None:
        content = 'before\n\n```python\nx = "[[not/a/link]]"\n**kept**\n```\n\nafter\n'
        regions = parse(content)
        assert kinds(regions) == [RegionKind.PROSE, RegionKind.CODE, RegionKind.PROSE]
        code = regions[1]
        assert code.text == 'x = "[[not/a/link]]"\n**kept**'
        assert code.metadata == {"language": "python"}
        assert slice_of(content, code).startswith("```python")
        assert slice_of(content, code).endswith("```")

    def test_tilde_fence_and_no_info_string(self) -> None:
        regions = parse("~~~\nplain\n~~~\n")
        assert kinds(regions) == [RegionKind.CODE]
        assert regions[0].text == "plain"
        assert regions[0].metadata == {}

    def test_unclosed_fence_runs_to_end(self) -> None:
        content = "```\nline one\nline two\n"
        regions = parse(content)
        assert kinds(regions) == [RegionKind.CODE]
        assert regions[0].text == "line one\nline two"
        assert regions[0].span.end == len(content) - 1  # excludes final newline


class TestEquations:
    def test_single_line_display_math(self) -> None:
        content = "text\n\n$$E = mc^2$$\n\nmore\n"
        regions = parse(content)
        assert kinds(regions) == [RegionKind.PROSE, RegionKind.EQUATION, RegionKind.PROSE]
        assert regions[1].text == "E = mc^2"
        assert slice_of(content, regions[1]) == "$$E = mc^2$$"

    def test_multi_line_display_math(self) -> None:
        content = "$$\nR + W > N\n$$\n"
        regions = parse(content)
        assert kinds(regions) == [RegionKind.EQUATION]
        assert regions[0].text == "R + W > N"
        assert slice_of(content, regions[0]) == "$$\nR + W > N\n$$"


class TestLists:
    def test_bullets_with_continuation(self) -> None:
        content = "- alpha\n- beta line\n  continues here\n* gamma\n"
        regions = parse(content)
        assert kinds(regions) == [RegionKind.LIST]
        assert regions[0].text == "alpha\nbeta line\ncontinues here\ngamma"
        assert slice_of(content, regions[0]) == content.rstrip("\n")

    def test_ordered_list_and_loose_items(self) -> None:
        content = "1. first\n2. second\n\n3. third after blank\n"
        regions = parse(content)
        assert kinds(regions) == [RegionKind.LIST]
        assert regions[0].text == "first\nsecond\nthird after blank"

    def test_list_markers_cleaned_but_inline_markup_too(self) -> None:
        regions = parse("- **bold** item with [[a/b|a link]]\n")
        assert regions[0].kind is RegionKind.LIST
        assert regions[0].text == "bold item with a link"


class TestTables:
    CONTENT = (
        "| Model | Ordering |\n"
        "| ----- | -------- |\n"
        "| Linearizable | real-time |\n"
        "| Sequential | program order |\n"
    )

    def test_table_region_excludes_separator_row(self) -> None:
        regions = parse(self.CONTENT)
        assert kinds(regions) == [RegionKind.TABLE]
        assert regions[0].text == (
            "Model | Ordering\nLinearizable | real-time\nSequential | program order"
        )
        assert slice_of(self.CONTENT, regions[0]) == self.CONTENT.rstrip("\n")

    def test_pipe_line_without_separator_stays_prose(self) -> None:
        regions = parse("a | b without a separator row\n")
        assert kinds(regions) == [RegionKind.PROSE]


class TestQuotes:
    def test_blockquote_region(self) -> None:
        content = "> Strong consistency is a spectrum,\n> not a switch.\n"
        regions = parse(content)
        assert kinds(regions) == [RegionKind.QUOTE]
        assert regions[0].text == "Strong consistency is a spectrum,\nnot a switch."
        assert slice_of(content, regions[0]) == content.rstrip("\n")


class TestProse:
    def test_split_on_blank_lines(self) -> None:
        content = "first paragraph\nstill first\n\nsecond paragraph\n"
        regions = parse(content)
        assert kinds(regions) == [RegionKind.PROSE, RegionKind.PROSE]
        assert regions[0].text == "first paragraph\nstill first"
        assert regions[1].text == "second paragraph"
        assert slice_of(content, regions[0]) == "first paragraph\nstill first"
        assert slice_of(content, regions[1]) == "second paragraph"

    def test_thematic_break_produces_no_region(self) -> None:
        regions = parse("above\n\n---\n\nbelow\n")
        assert kinds(regions) == [RegionKind.PROSE, RegionKind.PROSE]


class TestInlineCleanup:
    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            # separated tokens stay separated; adjacent tokens stay adjacent
            ("foo **bar** baz", "foo bar baz"),
            ("foo**bar** baz", "foobar baz"),
            ("a*b* c", "ab c"),
            ("x _y_ z", "x y z"),
            # identifiers survive underscore emphasis stripping
            ("snake_case stays intact", "snake_case stays intact"),
            # wikilinks
            ("[[systems/dynamo-db]]", "dynamo db"),
            ("[[a/b#anchor]]", "b"),
            ("[[a/b|display text]]", "display text"),
            # markdown links and images keep only human-readable text
            ("[text](https://example.com)", "text"),
            ("![alt text](img.png)", "alt text"),
            # inline code loses backticks, keeps content verbatim
            ("run `a_b**c` now", "run a_b**c now"),
            # inline math kept verbatim, dollars included
            ("value $d_k$ here", "value $d_k$ here"),
            ("$a*b$", "$a*b$"),
        ],
    )
    def test_clean_inline(self, source: str, expected: str) -> None:
        assert clean_inline(source) == expected

    def test_cleanup_applies_to_prose_regions(self) -> None:
        regions = parse("See [[a/deep-topic|the topic]] and **emphasis**.\n")
        assert regions[0].text == "See the topic and emphasis."


class TestContract:
    def test_fingerprint_is_versioned(self) -> None:
        assert MarkdownRegionParser().fingerprint == "linkdiscovery-markdown-parser/0.1.0"

    def test_deterministic(self) -> None:
        content = "---\ntitle: T\n---\n\n# T\n\n## S\n\nprose\n\n- item\n\n```\ncode\n```\n"
        assert parse(content) == parse(content)

    def test_all_spans_within_bounds_and_slice_matches_structure(self) -> None:
        content = (
            "---\ntitle: Full\n---\n\n# Full\n\nIntro with [[x/y|link]].\n\n"
            "## Section\n\n> quote\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n\n"
            "$$\nx\n$$\n\n- one\n- two\n"
        )
        regions = parse(content)
        assert kinds(regions) == [
            RegionKind.METADATA,
            RegionKind.BOILERPLATE,
            RegionKind.PROSE,
            RegionKind.HEADING,
            RegionKind.QUOTE,
            RegionKind.TABLE,
            RegionKind.EQUATION,
            RegionKind.LIST,
        ]
        previous_end = 0
        for region in regions:
            assert 0 <= region.span.start <= region.span.end <= len(content)
            assert region.span.start >= previous_end
            previous_end = region.span.end
