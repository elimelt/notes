"""Source-side contracts: documents, relationships, and the corpus artifact.

These types are produced by source adapters. The core treats every ID as an
opaque string: no path logic, markup knowledge, or host-repository concepts
appear here. The JSON shapes match the SPEC "SourceDocument" and
"Relationship" examples exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from linkdiscovery.contracts.base import (
    ArtifactHeader,
    check_schema_version,
    expect_bool,
    expect_header,
    expect_json_object,
    expect_list,
    expect_mapping,
    expect_str,
)
from linkdiscovery.contracts.units import Span
from linkdiscovery.errors import ContractError

__all__ = [
    "SCHEMA_VERSION",
    "Corpus",
    "DocumentFlags",
    "Relationship",
    "RelationshipSet",
    "SourceDocument",
]

SCHEMA_VERSION = 1
"""Schema version for corpus-manifest artifacts."""


@dataclass(frozen=True, slots=True)
class DocumentFlags:
    """Adapter-supplied eligibility flags for a source document.

    ``excluded`` removes the document from candidate generation entirely;
    ``generated`` and ``archived`` mark content the candidate policy excludes
    by default. Flags absent from serialized input default to ``False``.
    """

    excluded: bool = False
    generated: bool = False
    archived: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "excluded": self.excluded,
            "generated": self.generated,
            "archived": self.archived,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentFlags:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "DocumentFlags"
        mapping = expect_mapping(data, context)
        return cls(
            excluded=expect_bool(mapping, "excluded", context, default=False),
            generated=expect_bool(mapping, "generated", context, default=False),
            archived=expect_bool(mapping, "archived", context, default=False),
        )


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """A source item that may be a link endpoint.

    Invariants owned by the adapter: ``id`` stays stable across recognizable
    moves and renames; ``revision`` changes whenever content or
    embedding-relevant metadata changes. ``source_ref`` is the adapter-defined
    human-facing reference; ``metadata`` is opaque JSON-safe data passed
    through to features that opt into it.
    """

    id: str
    revision: str
    media_type: str
    content: str
    title: str = ""
    language: str = ""
    source_ref: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    flags: DocumentFlags = field(default_factory=DocumentFlags)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives matching the SPEC JSON shape."""
        return {
            "id": self.id,
            "revision": self.revision,
            "media_type": self.media_type,
            "content": self.content,
            "title": self.title,
            "language": self.language,
            "source_ref": self.source_ref,
            "metadata": dict(self.metadata),
            "flags": self.flags.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceDocument:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "SourceDocument"
        mapping = expect_mapping(data, context)
        flags_data = mapping.get("flags")
        flags = (
            DocumentFlags.from_dict(expect_mapping(flags_data, f"{context}: field 'flags'"))
            if flags_data is not None
            else DocumentFlags()
        )
        return cls(
            id=expect_str(mapping, "id", context),
            revision=expect_str(mapping, "revision", context),
            media_type=expect_str(mapping, "media_type", context),
            content=expect_str(mapping, "content", context),
            title=expect_str(mapping, "title", context, default=""),
            language=expect_str(mapping, "language", context, default=""),
            source_ref=expect_str(mapping, "source_ref", context, default=""),
            metadata=expect_json_object(mapping, "metadata", context, default={}),
            flags=flags,
        )


@dataclass(frozen=True, slots=True)
class Relationship:
    """An existing explicit connection between two document IDs.

    ``kind`` is adapter-defined; the candidate policy decides which kinds
    count as an existing direct link. ``source_span`` optionally locates the
    link in the source document's raw content.
    """

    source_id: str
    target_id: str
    kind: str
    directed: bool = True
    source_span: Span | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives matching the SPEC JSON shape."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "kind": self.kind,
            "directed": self.directed,
            "source_span": self.source_span.to_dict() if self.source_span else None,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Relationship:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "Relationship"
        mapping = expect_mapping(data, context)
        span_data = mapping.get("source_span")
        span = (
            Span.from_dict(expect_mapping(span_data, f"{context}: field 'source_span'"))
            if span_data is not None
            else None
        )
        return cls(
            source_id=expect_str(mapping, "source_id", context),
            target_id=expect_str(mapping, "target_id", context),
            kind=expect_str(mapping, "kind", context),
            directed=expect_bool(mapping, "directed", context, default=True),
            source_span=span,
            metadata=expect_json_object(mapping, "metadata", context, default={}),
        )


@dataclass(frozen=True, slots=True)
class RelationshipSet:
    """The complete set of existing relationships extracted by the adapter.

    Existing links are weak supervision: candidate generation uses them for
    exclusion, ranking uses them for redundancy signals, and evaluation uses
    them for held-out recovery. Order is preserved but not meaningful.
    """

    relationships: tuple[Relationship, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {"relationships": [rel.to_dict() for rel in self.relationships]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RelationshipSet:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "RelationshipSet"
        mapping = expect_mapping(data, context)
        items = expect_list(mapping, "relationships", context, default=[])
        return cls(
            relationships=tuple(
                Relationship.from_dict(
                    expect_mapping(item, f"{context}: field 'relationships[{index}]'")
                )
                for index, item in enumerate(items)
            )
        )


@dataclass(frozen=True, slots=True)
class Corpus:
    """The frozen source-side snapshot one run operates on: an artifact-level contract.

    Invariant (enforced at construction): document IDs are unique. A corpus is
    immutable once its manifest is written; a corpus changing after freezing
    is a detectable failure, not a supported operation.
    """

    header: ArtifactHeader
    documents: tuple[SourceDocument, ...] = ()
    relationships: RelationshipSet = field(default_factory=RelationshipSet)

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for document in self.documents:
            if document.id in seen:
                raise ContractError(f"Corpus: duplicate document id {document.id!r}")
            seen.add(document.id)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "header": self.header.to_dict(),
            "documents": [document.to_dict() for document in self.documents],
            "relationships": self.relationships.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Corpus:
        """Deserialize, raising ``ContractError`` on invalid or unknown-version input."""
        context = "Corpus"
        mapping = expect_mapping(data, context)
        header = expect_header(mapping, context)
        check_schema_version(header, SCHEMA_VERSION, context)
        documents = expect_list(mapping, "documents", context, default=[])
        relationships_data = mapping.get("relationships")
        relationships = (
            RelationshipSet.from_dict(
                expect_mapping(relationships_data, f"{context}: field 'relationships'")
            )
            if relationships_data is not None
            else RelationshipSet()
        )
        return cls(
            header=header,
            documents=tuple(
                SourceDocument.from_dict(
                    expect_mapping(item, f"{context}: field 'documents[{index}]'")
                )
                for index, item in enumerate(documents)
            ),
            relationships=relationships,
        )
