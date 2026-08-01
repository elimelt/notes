"""Preprocessing contracts: regions, spans, semantic units, processed corpora.

These types are the boundary between preprocessing and embedding. They match
the SPEC "SemanticUnit" JSON shape exactly and are deterministic products of a
fixed parser version and configuration. Source spans locate evidence in the
raw content; they may shift after unrelated edits and therefore are never the
sole identity input for a unit (``content_hash`` is).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from linkdiscovery.contracts.base import (
    ArtifactHeader,
    check_schema_version,
    expect_header,
    expect_int,
    expect_json_object,
    expect_list,
    expect_mapping,
    expect_str,
    expect_str_tuple,
)
from linkdiscovery.errors import ContractError

__all__ = [
    "SCHEMA_VERSION",
    "ProcessedCorpus",
    "ProcessedDocument",
    "Region",
    "RegionKind",
    "SemanticUnit",
    "Span",
]

SCHEMA_VERSION = 1
"""Schema version for processed-corpus artifacts."""


class RegionKind(StrEnum):
    """Portable typed-region kinds from the SPEC "Regions" section.

    Parsers must map any source-specific kind onto one of these; unknown
    kinds are preserved as ``OTHER`` at parse time. Deserialization is strict:
    a serialized kind outside this enum is a contract violation.
    """

    TITLE = "title"
    HEADING = "heading"
    PROSE = "prose"
    LIST = "list"
    CODE = "code"
    EQUATION = "equation"
    TABLE = "table"
    QUOTE = "quote"
    CITATION = "citation"
    METADATA = "metadata"
    BOILERPLATE = "boilerplate"
    OTHER = "other"


def _region_kind(value: str, context: str) -> RegionKind:
    try:
        return RegionKind(value)
    except ValueError as exc:
        allowed = ", ".join(kind.value for kind in RegionKind)
        raise ContractError(
            f"{context}: unknown region kind {value!r}; expected one of: {allowed}"
        ) from exc


@dataclass(frozen=True, slots=True)
class Span:
    """A half-open character range ``[start, end)`` in a document's raw content.

    Invariants (enforced at construction): ``start >= 0`` and ``end >= start``.
    Empty spans are permitted.
    """

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ContractError(
                f"Span: invalid range [{self.start}, {self.end}); "
                "start must be >= 0 and end must be >= start"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {"start": self.start, "end": self.end}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Span:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "Span"
        mapping = expect_mapping(data, context)
        return cls(
            start=expect_int(mapping, "start", context),
            end=expect_int(mapping, "end", context),
        )


def _span_tuple(data: dict[str, Any], name: str, context: str) -> tuple[Span, ...]:
    """Read a required array of span objects."""
    items = expect_list(data, name, context)
    return tuple(
        Span.from_dict(expect_mapping(item, f"{context}: field '{name}[{index}]'"))
        for index, item in enumerate(items)
    )


@dataclass(frozen=True, slots=True)
class Region:
    """A typed span of source content emitted by a region parser.

    ``text`` is the normalized text of the region (empty for regions that are
    tracked but not embedded); ``span`` locates the region in the source
    document's raw content; ``metadata`` carries parser-specific extras (for
    example a heading level) and must stay JSON-safe.
    """

    kind: RegionKind
    span: Span
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "kind": self.kind.value,
            "span": self.span.to_dict(),
            "text": self.text,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Region:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "Region"
        mapping = expect_mapping(data, context)
        return cls(
            kind=_region_kind(expect_str(mapping, "kind", context), context),
            span=Span.from_dict(expect_mapping(mapping.get("span"), f"{context}: field 'span'")),
            text=expect_str(mapping, "text", context),
            metadata=expect_json_object(mapping, "metadata", context, default={}),
        )


@dataclass(frozen=True, slots=True)
class SemanticUnit:
    """A deterministic piece of a document presented to the embedding model.

    Matches the SPEC "SemanticUnit" JSON shape. ``id`` is stable for unchanged
    semantic content; ``content_hash`` fingerprints ``text`` (and any context
    the preprocessor prepends) and is the identity input for embedding cache
    keys. ``view`` names the retrieval view (``document``, ``section``,
    ``title``, or a registered extension). ``token_count`` is measured with
    the selected model's tokenizer, never a word-count approximation.
    """

    id: str
    document_id: str
    view: str
    section_path: tuple[str, ...]
    region_kinds: tuple[RegionKind, ...]
    source_spans: tuple[Span, ...]
    text: str
    token_count: int
    content_hash: str

    def __post_init__(self) -> None:
        if self.token_count < 0:
            raise ContractError(
                f"SemanticUnit {self.id!r}: token_count must be >= 0, got {self.token_count}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives matching the SPEC JSON shape."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "view": self.view,
            "section_path": list(self.section_path),
            "region_kinds": [kind.value for kind in self.region_kinds],
            "source_spans": [span.to_dict() for span in self.source_spans],
            "text": self.text,
            "token_count": self.token_count,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SemanticUnit:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "SemanticUnit"
        mapping = expect_mapping(data, context)
        kinds = expect_str_tuple(mapping, "region_kinds", context)
        return cls(
            id=expect_str(mapping, "id", context),
            document_id=expect_str(mapping, "document_id", context),
            view=expect_str(mapping, "view", context),
            section_path=expect_str_tuple(mapping, "section_path", context),
            region_kinds=tuple(_region_kind(kind, context) for kind in kinds),
            source_spans=_span_tuple(mapping, "source_spans", context),
            text=expect_str(mapping, "text", context),
            token_count=expect_int(mapping, "token_count", context),
            content_hash=expect_str(mapping, "content_hash", context),
        )


@dataclass(frozen=True, slots=True)
class ProcessedDocument:
    """One document's typed regions and semantic units.

    Invariant (enforced at construction): every unit belongs to this document
    (``unit.document_id == document_id``). ``revision`` echoes the source
    document revision that was processed, so staleness is detectable.
    """

    document_id: str
    revision: str
    regions: tuple[Region, ...] = ()
    units: tuple[SemanticUnit, ...] = ()

    def __post_init__(self) -> None:
        for unit in self.units:
            if unit.document_id != self.document_id:
                raise ContractError(
                    f"ProcessedDocument {self.document_id!r}: unit {unit.id!r} belongs to "
                    f"document {unit.document_id!r}"
                )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "document_id": self.document_id,
            "revision": self.revision,
            "regions": [region.to_dict() for region in self.regions],
            "units": [unit.to_dict() for unit in self.units],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProcessedDocument:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "ProcessedDocument"
        mapping = expect_mapping(data, context)
        regions = expect_list(mapping, "regions", context, default=[])
        units = expect_list(mapping, "units", context, default=[])
        return cls(
            document_id=expect_str(mapping, "document_id", context),
            revision=expect_str(mapping, "revision", context),
            regions=tuple(
                Region.from_dict(expect_mapping(item, f"{context}: field 'regions[{index}]'"))
                for index, item in enumerate(regions)
            ),
            units=tuple(
                SemanticUnit.from_dict(expect_mapping(item, f"{context}: field 'units[{index}]'"))
                for index, item in enumerate(units)
            ),
        )


@dataclass(frozen=True, slots=True)
class ProcessedCorpus:
    """The full preprocessing output: an artifact-level contract.

    ``preprocessing_fingerprint`` covers the parser version and preprocessing
    configuration; it is one component of embedding cache keys. Invariant:
    document IDs are unique within the corpus.
    """

    header: ArtifactHeader
    preprocessing_fingerprint: str
    documents: tuple[ProcessedDocument, ...] = ()

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for document in self.documents:
            if document.document_id in seen:
                raise ContractError(
                    f"ProcessedCorpus: duplicate document id {document.document_id!r}"
                )
            seen.add(document.document_id)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "header": self.header.to_dict(),
            "preprocessing_fingerprint": self.preprocessing_fingerprint,
            "documents": [document.to_dict() for document in self.documents],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProcessedCorpus:
        """Deserialize, raising ``ContractError`` on invalid or unknown-version input."""
        context = "ProcessedCorpus"
        mapping = expect_mapping(data, context)
        header = expect_header(mapping, context)
        check_schema_version(header, SCHEMA_VERSION, context)
        documents = expect_list(mapping, "documents", context, default=[])
        return cls(
            header=header,
            preprocessing_fingerprint=expect_str(mapping, "preprocessing_fingerprint", context),
            documents=tuple(
                ProcessedDocument.from_dict(
                    expect_mapping(item, f"{context}: field 'documents[{index}]'")
                )
                for index, item in enumerate(documents)
            ),
        )
