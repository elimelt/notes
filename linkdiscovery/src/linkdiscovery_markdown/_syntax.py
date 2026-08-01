"""Low-level Markdown syntax primitives shared by the adapter and parser.

Internal to :mod:`linkdiscovery_markdown`: this module owns the regular
expressions and span-preserving helpers for the host corpus's markup ---
YAML frontmatter, fenced code blocks, Obsidian/Quartz wikilinks, standard
Markdown links and images, and inline markup cleanup.

Everything operates on raw document content and reports positions as
character offsets into that raw content, so callers can build
:class:`~linkdiscovery.contracts.units.Span` values that slice the source
exactly. Helpers that rewrite text (masking) are length-preserving so
offsets computed on the rewritten text remain valid in the original.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

import yaml

from linkdiscovery.contracts.units import Span

__all__ = [
    "FENCE_OPEN_RE",
    "HEADING_RE",
    "MAX_FENCE_INDENT",
    "Frontmatter",
    "LinkOccurrence",
    "clean_heading",
    "clean_inline",
    "fenced_code_spans",
    "humanize_target",
    "is_external_target",
    "iter_links",
    "mask_spans",
    "split_frontmatter",
]

FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(.*?)^(?:---|\.\.\.)[ \t]*(?:\r?\n|\Z)",
    re.DOTALL | re.MULTILINE,
)
"""A leading YAML frontmatter block delimited by ``---`` lines."""

FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*([^`]*)$")
"""An opening code fence (backtick or tilde) with an optional info string."""

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.*)$")
"""An ATX heading line; group 1 is the hash run, group 2 the raw text."""

_WIKILINK_RE = re.compile(r"\[\[([^\[\]|\n]+?)(?:\|([^\[\]\n]*))?\]\]")
_MDLINK_RE = re.compile(r"(!?)\[([^\]\n]*)\]\(([^()\s]+)(?:\s+\"[^\"]*\")?\)")
_INLINE_CODE_RE = re.compile(r"(`+)(.+?)\1")
_INLINE_MATH_RE = re.compile(r"\$(?!\$)([^$\n]+?)\$")
_UNDERSCORE_EMPHASIS_RE = re.compile(r"(?<!\w)_([^_\n]+)_(?!\w)")
_TRAILING_HASHES_RE = re.compile(r"[ \t]+#+[ \t]*$")

MAX_FENCE_INDENT = 3
"""CommonMark allows up to three spaces of indentation on a fence line."""


@dataclass(frozen=True, slots=True)
class Frontmatter:
    """A parsed leading YAML frontmatter block.

    ``mapping`` is the parsed YAML (empty when the YAML is malformed or not
    a mapping --- a broken frontmatter block never crashes ingestion),
    ``span`` covers the whole block including both delimiter lines, and
    ``body`` is the raw YAML text between the delimiters.
    """

    mapping: dict[str, Any]
    span: Span
    body: str


def split_frontmatter(content: str) -> Frontmatter | None:
    """Return the leading frontmatter block, or ``None`` when absent.

    Malformed YAML inside a well-delimited block yields an empty mapping
    (with the span still reported) rather than an exception, per the SPEC's
    permissive failure handling for malformed source content.
    """
    match = FRONTMATTER_RE.match(content)
    if match is None:
        return None
    span = Span(start=0, end=match.end())
    body = match.group(1)
    try:
        data = yaml.safe_load(body)
    except yaml.YAMLError:
        return Frontmatter(mapping={}, span=span, body=body)
    if not isinstance(data, dict):
        return Frontmatter(mapping={}, span=span, body=body)
    return Frontmatter(
        mapping={str(key): value for key, value in data.items()}, span=span, body=body
    )


def fenced_code_spans(content: str) -> list[Span]:
    """Locate every fenced code block (``` or ~~~) as a span into ``content``.

    Spans include the fence lines themselves. An unclosed fence extends to
    the end of the content, matching CommonMark behavior.
    """
    spans: list[Span] = []
    offset = 0
    open_start: int | None = None
    fence_char = ""
    fence_len = 0
    for raw_line in content.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        if open_start is None:
            match = FENCE_OPEN_RE.match(line)
            if match is not None:
                open_start = offset
                fence_char = match.group(1)[0]
                fence_len = len(match.group(1))
        elif _is_fence_close(line, fence_char, fence_len):
            spans.append(Span(start=open_start, end=offset + len(raw_line)))
            open_start = None
        offset += len(raw_line)
    if open_start is not None:
        spans.append(Span(start=open_start, end=len(content)))
    return spans


def _is_fence_close(line: str, fence_char: str, fence_len: int) -> bool:
    stripped = line.strip()
    indent = len(line) - len(line.lstrip(" "))
    return (
        indent <= MAX_FENCE_INDENT and len(stripped) >= fence_len and set(stripped) == {fence_char}
    )


def mask_spans(content: str, spans: Iterable[Span]) -> str:
    """Replace each span with spaces, preserving length (and thus offsets).

    Used to hide frontmatter and fenced code from link extraction and title
    detection without invalidating character offsets into the raw content.
    """
    masked = content
    for span in spans:
        masked = masked[: span.start] + " " * (span.end - span.start) + masked[span.end :]
    return masked


def humanize_target(target: str) -> str:
    """Turn a bare wikilink target into display text.

    The last path segment with dashes replaced by spaces: for example
    ``distributed-systems/dynamo-db#ring`` becomes ``"dynamo db"``. A
    pure-anchor target (``#section``) humanizes its anchor instead.
    """
    path, _, anchor = target.partition("#")
    base = posixpath.basename(path.rstrip("/")) or anchor
    humanized = base.replace("-", " ").strip()
    return humanized or target.strip()


def is_external_target(target: str) -> bool:
    """True for URLs and other non-corpus targets of a Markdown link."""
    return "://" in target or target.startswith(("mailto:", "tel:", "#", "//"))


@dataclass(frozen=True, slots=True)
class LinkOccurrence:
    """One internal link found in (masked) document content.

    ``start``/``end`` are character offsets of the full link markup in the
    raw content; ``target`` is the raw target as written (anchor included);
    ``path`` and ``anchor`` are the target split at ``#``; ``text`` is the
    display text (empty when the link has none); ``kind`` is ``"wikilink"``
    or ``"markdown"``.
    """

    start: int
    end: int
    target: str
    path: str
    anchor: str
    text: str
    kind: str


def iter_links(masked_content: str) -> Iterator[LinkOccurrence]:
    """Yield internal links in offset order from masked content.

    Callers mask frontmatter and fenced code first (:func:`mask_spans`) so
    links inside those regions are never reported. External URLs, anchors,
    and images are skipped; images are Markdown-image syntax only, so a
    wikilink is always reported.
    """
    occurrences: list[LinkOccurrence] = []
    for match in _WIKILINK_RE.finditer(masked_content):
        target = match.group(1).strip()
        display = match.group(2)
        path, _, anchor = target.partition("#")
        occurrences.append(
            LinkOccurrence(
                start=match.start(),
                end=match.end(),
                target=target,
                path=path.strip(),
                anchor=anchor.strip(),
                text=(display or "").strip(),
                kind="wikilink",
            )
        )
    for match in _MDLINK_RE.finditer(masked_content):
        if match.group(1):
            continue  # image: not a relationship
        target = match.group(3).strip()
        if is_external_target(target):
            continue
        path, _, anchor = target.partition("#")
        occurrences.append(
            LinkOccurrence(
                start=match.start(),
                end=match.end(),
                target=target,
                path=path.strip(),
                anchor=anchor.strip(),
                text=match.group(2).strip(),
                kind="markdown",
            )
        )
    occurrences.sort(key=lambda occurrence: (occurrence.start, occurrence.end))
    yield from occurrences


def clean_inline(text: str) -> str:
    """Strip inline markup per the SPEC canonicalization rules.

    - ``[[target|text]]`` becomes ``text``; ``[[target]]`` becomes the
      humanized last path segment (:func:`humanize_target`).
    - ``[text](url)`` becomes ``text``; images collapse to their alt text
      (anchor text is semantic evidence; URLs and paths are not embedded).
    - Inline code loses its backticks but keeps its content verbatim.
    - Inline ``$...$`` math is kept verbatim, dollars included.
    - ``**``/``__``/``*`` emphasis markers are removed; ``_`` is removed
      only when it wraps a word (so ``snake_case`` survives). Removal never
      deletes whitespace, so tokens separated in the source stay separated.
    """
    protected: list[str] = []

    def protect(value: str) -> str:
        protected.append(value)
        return f"\x00{len(protected) - 1}\x00"

    cleaned = _INLINE_CODE_RE.sub(lambda m: protect(m.group(2)), text)
    cleaned = _INLINE_MATH_RE.sub(lambda m: protect(m.group(0)), cleaned)
    cleaned = _WIKILINK_RE.sub(
        lambda m: m.group(2).strip() if m.group(2) is not None else humanize_target(m.group(1)),
        cleaned,
    )
    cleaned = _MDLINK_RE.sub(lambda m: m.group(2), cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "").replace("*", "")
    cleaned = _UNDERSCORE_EMPHASIS_RE.sub(r"\1", cleaned)
    for index, value in enumerate(protected):
        cleaned = cleaned.replace(f"\x00{index}\x00", value)
    return cleaned.strip()


def clean_heading(text: str) -> str:
    """Clean an ATX heading's raw text: drop closing hashes, then inline markup."""
    return clean_inline(_TRAILING_HASHES_RE.sub("", text.strip()))
