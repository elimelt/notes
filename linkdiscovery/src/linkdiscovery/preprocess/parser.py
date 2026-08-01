"""Plain-text region parser: the built-in fallback ``RegionParser``.

:class:`PlainTextParser` handles ``text/plain`` and serves as the fallback
for unknown media types: it treats any content as plain text. Format-specific
parsers (Markdown, HTML, …) are adapter plugins; this parser knows no markup.

Regions are emitted against the ORIGINAL raw content: every span indexes
``document.content`` exactly as the adapter supplied it, and every region's
``text`` is the raw slice at its span (``document.content[start:end]``).
Normalization of region text is the preprocessor's job — applying the
canonicalization policy after parsing keeps spans valid against the raw
content (SPEC: "Source spans locate evidence in the raw content").
"""

from __future__ import annotations

from linkdiscovery.config import PreprocessConfig
from linkdiscovery.contracts.documents import SourceDocument
from linkdiscovery.contracts.units import Region, RegionKind, Span

__all__ = ["PlainTextParser"]

_PARSER_VERSION = "plain-text-parser:v1"


def _line_body_length(line: str) -> int:
    """Length of ``line`` without its trailing line terminator.

    ``line`` comes from ``str.splitlines(keepends=True)``, so it ends with at
    most one terminator sequence (possibly ``\\r\\n``) or none (final line).
    """
    parts = line.splitlines()
    return len(parts[0]) if parts else 0


def _paragraph_regions(content: str) -> list[Region]:
    """Split ``content`` into ``prose`` regions at blank lines.

    A blank line is any line that is empty or whitespace-only. Each region
    spans from the first character of its first line to the last content
    character (excluding the line terminator) of its last non-blank line, and
    its text is exactly the raw slice at that span.
    """
    regions: list[Region] = []
    offset = 0
    start: int | None = None
    end = 0
    for line in content.splitlines(keepends=True):
        if line.strip():
            if start is None:
                start = offset
            end = offset + _line_body_length(line)
        elif start is not None:
            regions.append(
                Region(kind=RegionKind.PROSE, span=Span(start, end), text=content[start:end])
            )
            start = None
        offset += len(line)
    if start is not None:
        regions.append(
            Region(kind=RegionKind.PROSE, span=Span(start, end), text=content[start:end])
        )
    return regions


class PlainTextParser:
    """Parses any document as plain text: a title region plus blank-line paragraphs.

    Contract: deterministic for a fixed fingerprint; spans index the raw
    ``document.content``; region text equals the raw slice at the span (the
    synthetic title region, whose text comes from ``document.title``, uses
    the empty span ``(0, 0)``); no two paragraphs are ever joined.
    """

    def parse(self, document: SourceDocument, config: PreprocessConfig) -> list[Region]:
        """Emit a ``title`` region (when the document has a title) then ``prose`` regions.

        ``config`` is accepted per the ``RegionParser`` Protocol but unused:
        this parser emits every region and leaves inclusion policy to the
        preprocessor.
        """
        del config
        regions: list[Region] = []
        if document.title:
            regions.append(Region(kind=RegionKind.TITLE, span=Span(0, 0), text=document.title))
        regions.extend(_paragraph_regions(document.content))
        return regions

    @property
    def fingerprint(self) -> str:
        """Parser identity and version; part of the preprocessing fingerprint."""
        return _PARSER_VERSION
