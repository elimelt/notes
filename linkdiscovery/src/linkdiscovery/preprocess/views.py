"""Retrieval-view builders (SPEC "Retrieval views").

Three views are supported, each producing
:class:`~linkdiscovery.preprocess.identity.UnitDraft`\\ s that the
preprocessor materializes into semantic units:

- ``document``: ONE bounded unit per document — title, descriptive metadata
  (an allowlist of metadata keys), all heading texts, then leading body
  content, truncated at region boundaries (never mid-word) to fit
  ``config.max_tokens``.
- ``section``: the section-aware chunker output
  (:func:`~linkdiscovery.preprocess.chunking.chunk_sections`).
- ``title``: title, adapter-supplied aliases (``metadata["aliases"]``), and
  descriptive metadata (``metadata["description"]``).

:func:`build_views` builds only the views listed in ``config.views``, in the
configured order. A view's construction policy lives in this module, and the
preprocessing fingerprint covers it through the preprocessor's producer
version and the preprocess configuration.
"""

from __future__ import annotations

from collections.abc import Sequence

from linkdiscovery.config import PreprocessConfig
from linkdiscovery.contracts.documents import SourceDocument
from linkdiscovery.contracts.units import Region, RegionKind, Span
from linkdiscovery.errors import PreprocessError
from linkdiscovery.interfaces import TokenCounter
from linkdiscovery.preprocess.chunking import chunk_sections
from linkdiscovery.preprocess.identity import UnitDraft

__all__ = [
    "DEFAULT_DOCUMENT_METADATA_KEYS",
    "KNOWN_VIEWS",
    "build_document_view",
    "build_section_view",
    "build_title_view",
    "build_views",
]

DEFAULT_DOCUMENT_METADATA_KEYS = ("description",)
"""Default metadata-key allowlist for the document view's descriptive metadata."""

KNOWN_VIEWS = frozenset({"document", "section", "title"})
"""Views this module can build; anything else in ``config.views`` is an error."""

_PART_SEPARATOR = "\n\n"


def _metadata_string(document: SourceDocument, key: str) -> str:
    """Return ``document.metadata[key]`` stripped when it is a non-empty string."""
    value = document.metadata.get(key)
    if isinstance(value, str):
        return value.strip()
    return ""


def build_document_view(
    document: SourceDocument,
    regions: Sequence[Region],
    config: PreprocessConfig,
    token_counter: TokenCounter,
    *,
    metadata_keys: tuple[str, ...] = DEFAULT_DOCUMENT_METADATA_KEYS,
) -> UnitDraft | None:
    """Build the single bounded document-view draft, or ``None`` when empty.

    Assembly order: title, descriptive metadata values for ``metadata_keys``
    (string values only), every heading text, then leading body content.
    Title and metadata are always included; headings and body regions are
    appended greedily, in order, while the assembled text stays within
    ``config.max_tokens`` — truncation drops whole regions, never partial
    words. Regions with kinds in ``config.exclude_regions`` and ``title``
    regions (the title is taken from ``document.title``) are skipped.
    """
    excluded = frozenset(config.exclude_regions)
    parts: list[str] = []
    kinds: list[RegionKind] = []
    spans: list[Span] = []
    title = document.title.strip()
    if title:
        parts.append(title)
        kinds.append(RegionKind.TITLE)
        spans.append(Span(0, 0))
    for key in metadata_keys:
        value = _metadata_string(document, key)
        if value:
            parts.append(value)
            if RegionKind.METADATA not in kinds:
                kinds.append(RegionKind.METADATA)
    candidates = [
        region
        for region in regions
        if region.kind is not RegionKind.TITLE
        and region.kind.value not in excluded
        and region.text.strip()
    ]
    headings = [region for region in candidates if region.kind is RegionKind.HEADING]
    body = [region for region in candidates if region.kind is not RegionKind.HEADING]
    for region in (*headings, *body):
        tentative = [*parts, region.text.strip()]
        if token_counter.count_tokens(_PART_SEPARATOR.join(tentative)) > config.max_tokens:
            break
        parts.append(region.text.strip())
        if region.kind not in kinds:
            kinds.append(region.kind)
        spans.append(region.span)
    text = _PART_SEPARATOR.join(parts)
    if not text.strip():
        return None
    return UnitDraft(
        view="document",
        section_path=(),
        region_kinds=tuple(kinds),
        source_spans=tuple(spans),
        text=text,
        token_count=token_counter.count_tokens(text),
    )


def build_section_view(
    document: SourceDocument,
    regions: Sequence[Region],
    config: PreprocessConfig,
    token_counter: TokenCounter,
) -> list[UnitDraft]:
    """Build section-view drafts: the section-aware chunker output."""
    return chunk_sections(document.title, regions, config, token_counter)


def build_title_view(
    document: SourceDocument,
    config: PreprocessConfig,
    token_counter: TokenCounter,
) -> UnitDraft | None:
    """Build the title-view draft: title, aliases, description; ``None`` when empty.

    Aliases come from ``document.metadata["aliases"]`` when it is a list;
    non-string or empty entries are ignored. The description comes from
    ``document.metadata["description"]``. Each component is one line. This
    view is naturally tiny and is not truncated. ``config`` is accepted for
    API symmetry with the other builders.
    """
    del config
    parts: list[str] = []
    has_metadata = False
    title = document.title.strip()
    if title:
        parts.append(title)
    aliases = document.metadata.get("aliases")
    if isinstance(aliases, list):
        for alias in aliases:
            if isinstance(alias, str) and alias.strip():
                parts.append(alias.strip())
                has_metadata = True
    description = _metadata_string(document, "description")
    if description:
        parts.append(description)
        has_metadata = True
    if not parts:
        return None
    kinds: list[RegionKind] = []
    if title:
        kinds.append(RegionKind.TITLE)
    if has_metadata:
        kinds.append(RegionKind.METADATA)
    text = "\n".join(parts)
    return UnitDraft(
        view="title",
        section_path=(),
        region_kinds=tuple(kinds),
        source_spans=(Span(0, 0),) if title else (),
        text=text,
        token_count=token_counter.count_tokens(text),
    )


def build_views(
    document: SourceDocument,
    regions: Sequence[Region],
    config: PreprocessConfig,
    token_counter: TokenCounter,
    *,
    document_metadata_keys: tuple[str, ...] = DEFAULT_DOCUMENT_METADATA_KEYS,
) -> list[UnitDraft]:
    """Build drafts for exactly the views named in ``config.views``, in order.

    Raises :class:`~linkdiscovery.errors.PreprocessError` for a view name
    outside :data:`KNOWN_VIEWS`, naming the document for context.
    """
    drafts: list[UnitDraft] = []
    for view in config.views:
        if view == "document":
            document_draft = build_document_view(
                document, regions, config, token_counter, metadata_keys=document_metadata_keys
            )
            if document_draft is not None:
                drafts.append(document_draft)
        elif view == "section":
            drafts.extend(build_section_view(document, regions, config, token_counter))
        elif view == "title":
            title_draft = build_title_view(document, config, token_counter)
            if title_draft is not None:
                drafts.append(title_draft)
        else:
            known = ", ".join(sorted(KNOWN_VIEWS))
            raise PreprocessError(
                f"document {document.id!r}: unknown retrieval view {view!r} in "
                f"preprocess.views; this preprocessor builds: {known}"
            )
    return drafts
