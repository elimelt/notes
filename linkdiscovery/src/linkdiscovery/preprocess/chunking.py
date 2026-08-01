"""Section-aware, tokenizer-measured chunking (SPEC "Chunking").

The strategy follows the SPEC exactly:

1. A section path (the stack of enclosing heading texts) accompanies every
   chunk. ``heading`` regions drive the path via ``metadata["level"]``;
   headings without a usable level are treated as level 1.
2. Adjacent non-heading regions under the same lowest-level heading form one
   group.
3. Groups whose embedded text exceeds ``config.max_tokens`` split at region
   boundaries first, then at paragraph boundaries, then (as a last resort so
   the bound still holds) at word boundaries — never mid-word.
4. Token overlap applies ONLY when a split crosses continuous prose, i.e. a
   word-boundary split inside a single ``prose`` region. Region and paragraph
   boundaries are semantic breaks and get no overlap.
5. Every chunk's embedded text carries context: the document title and the
   heading path as a ``"Title > Section > Subsection"`` prefix, separated
   from the chunk body by a blank line. The prefix is included in token
   accounting.

All sizes are measured with the injected
:class:`~linkdiscovery.interfaces.TokenCounter`. Regions whose kind is listed
in ``config.exclude_regions`` are omitted from chunk text, spans, and region
kinds, so ``region_kinds`` stays accurate for what a chunk actually contains.
Headings excluded that way still drive the section path (they are context,
never chunk body). Output is deterministic for fixed inputs.

Size guarantee: each chunk's total token count (context included) is at most
``config.max_tokens`` provided the context prefix itself leaves at least one
token of budget; a pathologically long single word may exceed the bound
rather than be split mid-word.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from linkdiscovery.config import PreprocessConfig
from linkdiscovery.contracts.units import Region, RegionKind, Span
from linkdiscovery.interfaces import TokenCounter
from linkdiscovery.preprocess.identity import UnitDraft

__all__ = ["chunk_sections"]

_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n+")
_WORD = re.compile(r"\S+")

_SECTION_VIEW = "section"


@dataclass(frozen=True, slots=True)
class _Piece:
    """An indivisible packing unit: a region, paragraph, or word-window slice."""

    text: str
    region: Region


def _heading_level(region: Region) -> int:
    """Read ``metadata["level"]`` (a positive int); anything else is level 1."""
    level = region.metadata.get("level")
    if isinstance(level, int) and not isinstance(level, bool) and level >= 1:
        return level
    return 1


def _grouped(
    regions: Sequence[Region], excluded: frozenset[str]
) -> list[tuple[tuple[str, ...], list[Region]]]:
    """Group adjacent includable non-heading regions under their heading path.

    ``title`` regions are skipped (the title travels in the context prefix),
    excluded and empty regions are dropped, and each ``heading`` region
    flushes the open group and updates the path stack by level.
    """
    groups: list[tuple[tuple[str, ...], list[Region]]] = []
    path: list[tuple[int, str]] = []
    current: list[Region] = []

    def flush() -> None:
        if current:
            groups.append((tuple(text for _, text in path), list(current)))
            current.clear()

    for region in regions:
        if region.kind is RegionKind.HEADING:
            flush()
            level = _heading_level(region)
            while path and path[-1][0] >= level:
                path.pop()
            heading_text = region.text.strip()
            if heading_text:
                path.append((level, heading_text))
            continue
        if region.kind is RegionKind.TITLE:
            continue
        if region.kind.value in excluded or not region.text.strip():
            continue
        current.append(region)
    flush()
    return groups


def _split_paragraph(
    text: str,
    region: Region,
    context_tokens: int,
    config: PreprocessConfig,
    counter: TokenCounter,
) -> list[_Piece]:
    """Split one oversized paragraph at word boundaries, overlapping prose.

    The word-window budget reserves room for the context prefix and (for
    prose) the overlap tail, so ``context + overlap + window`` stays within
    ``config.max_tokens``. Words are never split; window text is a substring
    of ``text``, so internal whitespace is preserved exactly.
    """
    overlap = config.overlap_tokens if region.kind is RegionKind.PROSE else 0
    budget = max(1, min(config.target_tokens, config.max_tokens - overlap) - context_tokens)
    segments: list[str] = []
    start: int | None = None
    end = 0
    tokens = 0
    for match in _WORD.finditer(text):
        word_tokens = counter.count_tokens(match.group())
        if start is not None and tokens + word_tokens > budget:
            segments.append(text[start:end])
            start = None
            tokens = 0
        if start is None:
            start = match.start()
        end = match.end()
        tokens += word_tokens
    if start is not None:
        segments.append(text[start:end])

    pieces: list[_Piece] = []
    previous: str | None = None
    for segment in segments:
        body = segment
        if previous is not None and overlap > 0:
            tail = _overlap_tail(previous, overlap, counter)
            if tail:
                body = f"{tail} {segment}"
        pieces.append(_Piece(text=body, region=region))
        previous = segment
    return pieces


def _overlap_tail(text: str, overlap_tokens: int, counter: TokenCounter) -> str:
    """The longest word-aligned suffix of ``text`` within ``overlap_tokens`` tokens."""
    tokens = 0
    start: int | None = None
    for match in reversed(list(_WORD.finditer(text))):
        word_tokens = counter.count_tokens(match.group())
        if tokens + word_tokens > overlap_tokens:
            break
        tokens += word_tokens
        start = match.start()
    return text[start:] if start is not None else ""


def _split_region(
    region: Region,
    embed: Callable[[str], str],
    context_tokens: int,
    config: PreprocessConfig,
    counter: TokenCounter,
) -> list[_Piece]:
    """Split one oversized region at paragraph boundaries, then word boundaries."""
    pieces: list[_Piece] = []
    for paragraph in _PARAGRAPH_BREAK.split(region.text):
        text = paragraph.strip()
        if not text:
            continue
        if counter.count_tokens(embed(text)) <= config.max_tokens:
            pieces.append(_Piece(text=text, region=region))
        else:
            pieces.extend(_split_paragraph(text, region, context_tokens, config, counter))
    return pieces


def _pack(
    pieces: Sequence[_Piece],
    embed: Callable[[str], str],
    config: PreprocessConfig,
    counter: TokenCounter,
) -> list[list[_Piece]]:
    """Greedily pack pieces into chunks of at most ``target_tokens`` (measured)."""
    chunks: list[list[_Piece]] = []
    current: list[_Piece] = []
    for piece in pieces:
        if current:
            body = "\n\n".join(p.text for p in (*current, piece))
            if counter.count_tokens(embed(body)) > config.target_tokens:
                chunks.append(current)
                current = []
        current.append(piece)
    if current:
        chunks.append(current)
    return chunks


def _make_draft(
    path: tuple[str, ...],
    pieces: Sequence[_Piece],
    embed: Callable[[str], str],
    counter: TokenCounter,
) -> UnitDraft:
    """Build a section-view draft from packed pieces, with accurate kinds and spans."""
    body = "\n\n".join(piece.text for piece in pieces)
    text = embed(body)
    kinds: list[RegionKind] = []
    spans: list[Span] = []
    seen_regions: set[int] = set()
    for piece in pieces:
        if piece.region.kind not in kinds:
            kinds.append(piece.region.kind)
        if id(piece.region) not in seen_regions:
            seen_regions.add(id(piece.region))
            spans.append(piece.region.span)
    return UnitDraft(
        view=_SECTION_VIEW,
        section_path=path,
        region_kinds=tuple(kinds),
        source_spans=tuple(spans),
        text=text,
        token_count=counter.count_tokens(text),
    )


def _chunk_group(
    title: str,
    path: tuple[str, ...],
    group: Sequence[Region],
    config: PreprocessConfig,
    counter: TokenCounter,
) -> list[UnitDraft]:
    """Chunk one heading group: whole when it fits, otherwise split and pack."""
    context = " > ".join(part for part in (title.strip(), *path) if part)

    def embed(body: str) -> str:
        return f"{context}\n\n{body}" if context else body

    whole = "\n\n".join(region.text for region in group)
    if counter.count_tokens(embed(whole)) <= config.max_tokens:
        pieces = [_Piece(text=region.text, region=region) for region in group]
        return [_make_draft(path, pieces, embed, counter)]

    context_tokens = counter.count_tokens(context)
    split_pieces: list[_Piece] = []
    for region in group:
        if counter.count_tokens(embed(region.text)) <= config.max_tokens:
            split_pieces.append(_Piece(text=region.text, region=region))
        else:
            split_pieces.extend(_split_region(region, embed, context_tokens, config, counter))
    packed = _pack(split_pieces, embed, config, counter)
    return [_make_draft(path, chunk, embed, counter) for chunk in packed]


def chunk_sections(
    title: str,
    regions: Sequence[Region],
    config: PreprocessConfig,
    token_counter: TokenCounter,
) -> list[UnitDraft]:
    """Chunk parsed regions into section-view unit drafts.

    ``title`` is the document title used (with the heading path) as the
    context prefix of every chunk; pass an empty string when the document has
    none. Returns drafts in document order; identity assignment is the
    caller's job (:func:`~linkdiscovery.preprocess.identity.assign_unit_ids`).
    Deterministic for fixed inputs.
    """
    excluded = frozenset(config.exclude_regions)
    drafts: list[UnitDraft] = []
    for path, group in _grouped(regions, excluded):
        drafts.extend(_chunk_group(title, path, group, config, token_counter))
    return drafts
