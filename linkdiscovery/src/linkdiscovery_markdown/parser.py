"""Markdown region parser: types raw note content into SPEC regions.

Implements :class:`linkdiscovery.interfaces.RegionParser`. The parser is
zero-arg constructible and carries a versioned ``fingerprint`` that feeds
the preprocessing fingerprint --- bump :data:`PARSER_VERSION` on any
behavior change.

Input is ``document.content`` exactly as the adapter loaded it (RAW file
text, frontmatter included). Output regions carry spans that index that raw
content; the region ``text`` is the cleaned, embedding-ready form and may
therefore differ from the span slice --- spans locate evidence in the
source, text is what gets embedded, which is exactly the contract's design.

Region mapping (regex/line-based; no Markdown dependency):

- leading YAML frontmatter block -> ``metadata`` (text: the raw YAML body)
- ATX headings ``#``-``######`` -> ``heading`` with ``metadata={"level": n}``
- fenced code blocks (``` or ~~~, any info string; text kept verbatim,
  info string in ``metadata["language"]``) -> ``code``
- display math ``$$...$$`` (single- or multi-line, text kept verbatim)
  -> ``equation``
- consecutive ``-``/``*``/``+``/``1.``/``1)`` items, including indented
  continuation lines and blank-separated (loose) items -> ``list``
- pipe-delimited tables with a separator row (separator excluded from
  text) -> ``table``
- ``>`` blockquotes -> ``quote``
- everything else non-blank -> ``prose``, split on blank lines

Thematic breaks (``---``/``***``/``___``) are structural markup with no
semantic content and produce no region. Setext headings and indented
(4-space) code blocks are not recognized; the host corpus uses ATX
headings and fenced code exclusively.

Boilerplate-title decision: a leading H1 that equals the frontmatter title
(case-insensitively, whitespace-normalized) is emitted as ``boilerplate``
rather than ``heading`` --- the SPEC requires detecting repeated titles,
and preprocessing profiles exclude boilerplate from embedding. Section
structure therefore starts at the next heading: the repeated H1 carries no
information beyond the document title, which every retrieval view already
carries, so omitting it from section paths loses nothing. Only the first
content region of the document qualifies, and only when the title comes
from frontmatter (an H1 that *is* the title's source stays a heading).

Inline cleanup within region text follows the SPEC canonicalization rules
(see :func:`linkdiscovery_markdown._syntax.clean_inline`): wikilinks and
Markdown links keep their anchor text only, images collapse to alt text,
emphasis markers are stripped without concatenating separated tokens, and
inline ``$...$`` math and inline-code content are kept verbatim.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from linkdiscovery.config import PreprocessConfig
from linkdiscovery.contracts.documents import SourceDocument
from linkdiscovery.contracts.units import Region, RegionKind, Span
from linkdiscovery_markdown._syntax import (
    FENCE_OPEN_RE,
    HEADING_RE,
    MAX_FENCE_INDENT,
    clean_heading,
    clean_inline,
    split_frontmatter,
)

__all__ = ["PARSER_VERSION", "MarkdownRegionParser"]

PARSER_VERSION = "0.1.0"
"""Version component of the parser fingerprint; bump on any behavior change."""

_LIST_ITEM_RE = re.compile(r"^ {0,3}(?:[-*+]|\d{1,9}[.)])\s+")
_QUOTE_RE = re.compile(r"^ {0,3}>")
_QUOTE_MARKER_RE = re.compile(r"^ {0,3}> ?")
_TABLE_SEP_RE = re.compile(r"^ {0,3}\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)*\|?\s*$")
_HRULE_RE = re.compile(r"^ {0,3}(?:(?:-[ \t]*){3,}|(?:\*[ \t]*){3,}|(?:_[ \t]*){3,})$")
_MIN_INLINE_EQUATION_LEN = 5  # shortest single-line display math: "$$x$$"


class MarkdownRegionParser:
    """Parses one Markdown document's raw content into typed regions.

    Zero-arg constructible for plugin loading
    (``linkdiscovery_markdown.parser:MarkdownRegionParser``). Deterministic:
    the same content always yields the same region list. See the module
    docstring for the full region mapping and cleanup contract.
    """

    @property
    def fingerprint(self) -> str:
        """Parser identity (name and version); part of the preprocessing fingerprint."""
        return f"linkdiscovery-markdown-parser/{PARSER_VERSION}"

    def parse(self, document: SourceDocument, config: PreprocessConfig) -> list[Region]:
        """Emit typed regions covering the document's embedding-relevant content.

        ``config`` is accepted per the ``RegionParser`` Protocol but unused:
        view construction, chunking, and region inclusion policy belong to
        the core preprocessor, not the format parser.
        """
        del config
        content = document.content
        regions: list[Region] = []
        offset = 0
        title: str | None = None
        frontmatter = split_frontmatter(content)
        if frontmatter is not None:
            offset = frontmatter.span.end
            regions.append(
                Region(
                    kind=RegionKind.METADATA,
                    span=frontmatter.span,
                    text=frontmatter.body.strip(),
                )
            )
            raw_title = frontmatter.mapping.get("title")
            if raw_title is not None and str(raw_title).strip():
                title = str(raw_title).strip()
        _Scanner(lines=_split_lines(content, offset), title=title, regions=regions).run()
        return regions


@dataclass(frozen=True, slots=True)
class _Line:
    """One content line: ``[start, end)`` excludes the line terminator."""

    start: int
    end: int
    text: str


def _split_lines(content: str, offset: int) -> list[_Line]:
    """Split ``content[offset:]`` into lines with raw-content offsets."""
    lines: list[_Line] = []
    position = offset
    for raw_line in content[offset:].splitlines(keepends=True):
        text = raw_line.rstrip("\r\n")
        lines.append(_Line(start=position, end=position + len(text), text=text))
        position += len(raw_line)
    return lines


def _normalize_title(value: str) -> str:
    return " ".join(value.split()).casefold()


@dataclass(slots=True)
class _Scanner:
    """Single-pass line scanner producing body regions in document order."""

    lines: list[_Line]
    title: str | None
    regions: list[Region]
    _prose: list[_Line] = field(default_factory=list)
    _content_emitted: bool = False

    def run(self) -> None:
        index = 0
        while index < len(self.lines):
            line = self.lines[index]
            heading = HEADING_RE.match(line.text)
            if not line.text.strip() or _HRULE_RE.match(line.text):
                self._flush_prose()
                index += 1
            elif FENCE_OPEN_RE.match(line.text):
                self._flush_prose()
                index = self._consume_code(index)
            elif line.text.strip().startswith("$$"):
                self._flush_prose()
                index = self._consume_equation(index)
            elif heading is not None:
                self._flush_prose()
                self._emit_heading(line, heading)
                index += 1
            elif _QUOTE_RE.match(line.text):
                self._flush_prose()
                index = self._consume_quote(index)
            elif self._is_table_start(index):
                self._flush_prose()
                index = self._consume_table(index)
            elif _LIST_ITEM_RE.match(line.text):
                self._flush_prose()
                index = self._consume_list(index)
            else:
                self._prose.append(line)
                index += 1
        self._flush_prose()

    def _emit(
        self, kind: RegionKind, first: _Line, last: _Line, text: str, **metadata: int | str
    ) -> None:
        self.regions.append(
            Region(
                kind=kind,
                span=Span(start=first.start, end=last.end),
                text=text,
                metadata=dict(metadata),
            )
        )
        self._content_emitted = True

    def _flush_prose(self) -> None:
        if not self._prose:
            return
        text = clean_inline("\n".join(line.text for line in self._prose))
        self._emit(RegionKind.PROSE, self._prose[0], self._prose[-1], text)
        self._prose.clear()

    def _emit_heading(self, line: _Line, match: re.Match[str]) -> None:
        level = len(match.group(1))
        text = clean_heading(match.group(2))
        is_repeated_title = (
            level == 1
            and not self._content_emitted
            and self.title is not None
            and _normalize_title(text) == _normalize_title(self.title)
        )
        kind = RegionKind.BOILERPLATE if is_repeated_title else RegionKind.HEADING
        self._emit(kind, line, line, text, level=level)

    def _consume_code(self, index: int) -> int:
        open_match = FENCE_OPEN_RE.match(self.lines[index].text)
        assert open_match is not None  # guarded by run()
        fence = open_match.group(1)
        info = open_match.group(2).strip()
        last = len(self.lines) - 1
        inner: list[str] = []
        for position in range(index + 1, len(self.lines)):
            text = self.lines[position].text
            stripped = text.strip()
            indent = len(text) - len(text.lstrip(" "))
            if (
                indent <= MAX_FENCE_INDENT
                and len(stripped) >= len(fence)
                and set(stripped) == {fence[0]}
            ):
                last = position
                break
            inner.append(text)
        metadata: dict[str, str] = {"language": info} if info else {}
        self._emit(
            RegionKind.CODE,
            self.lines[index],
            self.lines[last],
            "\n".join(inner),
            **metadata,
        )
        return last + 1

    def _consume_equation(self, index: int) -> int:
        first = self.lines[index].text.strip()
        if first.endswith("$$") and len(first) >= _MIN_INLINE_EQUATION_LEN:
            self._emit(
                RegionKind.EQUATION,
                self.lines[index],
                self.lines[index],
                first[2:-2].strip(),
            )
            return index + 1
        last = len(self.lines) - 1
        for position in range(index + 1, len(self.lines)):
            if self.lines[position].text.rstrip().endswith("$$"):
                last = position
                break
        parts = [first[2:]]
        parts.extend(self.lines[position].text for position in range(index + 1, last))
        if last > index:
            closing = self.lines[last].text.rstrip()
            parts.append(closing[:-2] if closing.endswith("$$") else closing)
        text = "\n".join(part for part in parts if part.strip()).strip()
        self._emit(RegionKind.EQUATION, self.lines[index], self.lines[last], text)
        return last + 1

    def _consume_quote(self, index: int) -> int:
        end = index
        while end < len(self.lines) and _QUOTE_RE.match(self.lines[end].text):
            end += 1
        text = clean_inline(
            "\n".join(
                _QUOTE_MARKER_RE.sub("", self.lines[position].text)
                for position in range(index, end)
            )
        )
        self._emit(RegionKind.QUOTE, self.lines[index], self.lines[end - 1], text)
        return end

    def _is_table_start(self, index: int) -> bool:
        if "|" not in self.lines[index].text or index + 1 >= len(self.lines):
            return False
        separator = self.lines[index + 1].text
        return "|" in separator and _TABLE_SEP_RE.match(separator) is not None

    def _consume_table(self, index: int) -> int:
        end = index
        while (
            end < len(self.lines) and self.lines[end].text.strip() and "|" in self.lines[end].text
        ):
            end += 1
        rows: list[str] = []
        for position in range(index, end):
            text = self.lines[position].text
            if _TABLE_SEP_RE.match(text):
                continue
            cells = [cell.strip() for cell in text.strip().strip("|").split("|")]
            rows.append(clean_inline(" | ".join(cell for cell in cells if cell)))
        self._emit(RegionKind.TABLE, self.lines[index], self.lines[end - 1], "\n".join(rows))
        return end

    def _consume_list(self, index: int) -> int:
        last = index
        position = index
        while position < len(self.lines):
            text = self.lines[position].text
            if not text.strip():
                lookahead = position
                while lookahead < len(self.lines) and not self.lines[lookahead].text.strip():
                    lookahead += 1
                if lookahead < len(self.lines) and _LIST_ITEM_RE.match(self.lines[lookahead].text):
                    position = lookahead
                    continue
                break
            if position > index and not (_LIST_ITEM_RE.match(text) or text[0] in (" ", "\t")):
                break
            last = position
            position += 1
        items: list[str] = []
        for line in self.lines[index : last + 1]:
            if not line.text.strip():
                continue
            stripped = _LIST_ITEM_RE.sub("", line.text) or line.text.strip()
            items.append(clean_inline(stripped))
        self._emit(
            RegionKind.LIST,
            self.lines[index],
            self.lines[last],
            "\n".join(item for item in items if item),
        )
        return last + 1
