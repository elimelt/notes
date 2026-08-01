"""Shared factories and fixtures for the preprocessing test modules.

This module intentionally contains no tests; it provides small builders for
configs, documents, and corpora, plus ``TinyMarkupParser`` — a minimal
heading-aware ``RegionParser`` used to exercise section paths and region
kinds without depending on any real markup format.
"""

from __future__ import annotations

from linkdiscovery.config import PreprocessConfig
from linkdiscovery.contracts.base import ArtifactHeader
from linkdiscovery.contracts.documents import Corpus, DocumentFlags, SourceDocument
from linkdiscovery.contracts.units import Region, RegionKind, Span

__all__ = [
    "TinyMarkupParser",
    "make_config",
    "make_corpus",
    "make_document",
    "make_header",
]


def make_header(**overrides: object) -> ArtifactHeader:
    """A fully populated artifact header; keyword overrides replace fields."""
    values: dict[str, object] = {
        "schema_version": 1,
        "run_id": "run-0001",
        "corpus_id": "corpus-test",
        "created_at": "2026-07-31T12:00:00+00:00",
        "config_fingerprint": "sha256:cfg",
        "producer_version": "test-producer",
    }
    values.update(overrides)
    return ArtifactHeader(**values)  # type: ignore[arg-type]


def make_config(**overrides: object) -> PreprocessConfig:
    """A preprocess config with roomy defaults; keyword overrides replace fields."""
    values: dict[str, object] = {
        "parser": "linkdiscovery.preprocess:PlainTextParser",
        "views": ("document", "section", "title"),
        "target_tokens": 64,
        "max_tokens": 96,
        "overlap_tokens": 8,
    }
    values.update(overrides)
    return PreprocessConfig(**values)  # type: ignore[arg-type]


def make_document(
    doc_id: str = "doc-a",
    content: str = "First paragraph.\n\nSecond paragraph.",
    *,
    title: str = "Doc Title",
    media_type: str = "text/plain",
    metadata: dict[str, object] | None = None,
    excluded: bool = False,
) -> SourceDocument:
    """A source document; content and metadata are the interesting knobs."""
    return SourceDocument(
        id=doc_id,
        revision=f"rev-{doc_id}",
        media_type=media_type,
        content=content,
        title=title,
        metadata=dict(metadata or {}),
        flags=DocumentFlags(excluded=excluded),
    )


def make_corpus(*documents: SourceDocument) -> Corpus:
    """A corpus wrapping the given documents under a fixed header."""
    return Corpus(header=make_header(), documents=tuple(documents))


class TinyMarkupParser:
    """A minimal heading-aware parser for tests.

    Line syntax: lines starting with one or more ``#`` become ``heading``
    regions (level = number of ``#``); lines starting with ``%%`` become
    ``boilerplate``; lines starting with ``$$`` become ``code``; blank lines
    separate ``prose`` paragraphs. Spans index the raw content.
    """

    def parse(self, document: SourceDocument, config: PreprocessConfig) -> list[Region]:
        del config
        regions: list[Region] = []
        if document.title:
            regions.append(Region(kind=RegionKind.TITLE, span=Span(0, 0), text=document.title))
        offset = 0
        paragraph_start: int | None = None
        paragraph_end = 0
        content = document.content

        def flush() -> None:
            nonlocal paragraph_start
            if paragraph_start is not None:
                regions.append(
                    Region(
                        kind=RegionKind.PROSE,
                        span=Span(paragraph_start, paragraph_end),
                        text=content[paragraph_start:paragraph_end],
                    )
                )
                paragraph_start = None

        for line in content.splitlines(keepends=True):
            body = line.splitlines()[0] if line else ""
            stripped = body.strip()
            end = offset + len(body)
            if stripped.startswith("#"):
                flush()
                level = len(stripped) - len(stripped.lstrip("#"))
                regions.append(
                    Region(
                        kind=RegionKind.HEADING,
                        span=Span(offset, end),
                        text=stripped.lstrip("#").strip(),
                        metadata={"level": level},
                    )
                )
            elif stripped.startswith("%%"):
                flush()
                regions.append(
                    Region(
                        kind=RegionKind.BOILERPLATE,
                        span=Span(offset, end),
                        text=stripped[2:].strip(),
                    )
                )
            elif stripped.startswith("$$"):
                flush()
                regions.append(
                    Region(kind=RegionKind.CODE, span=Span(offset, end), text=stripped[2:].strip())
                )
            elif stripped:
                if paragraph_start is None:
                    paragraph_start = offset
                paragraph_end = end
            else:
                flush()
            offset += len(line)
        flush()
        return regions

    @property
    def fingerprint(self) -> str:
        return "tiny-markup-parser:v1"
