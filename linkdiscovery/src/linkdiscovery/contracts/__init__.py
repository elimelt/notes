"""Typed, serializable, versioned data contracts for every stage boundary.

Stages exchange these types, never framework objects (SPEC design principle
2). Every type is a frozen dataclass with ``to_dict``/``from_dict`` producing
JSON-safe primitives; deserialization validates strictly and raises
:class:`~linkdiscovery.errors.ContractError` on bad input.
"""

from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.contracts.candidates import CandidatePair, CandidateSet, UnitMatch
from linkdiscovery.contracts.documents import (
    Corpus,
    DocumentFlags,
    Relationship,
    RelationshipSet,
    SourceDocument,
)
from linkdiscovery.contracts.embeddings import EmbeddingIndex, EmbeddingRecord, RuntimeReport
from linkdiscovery.contracts.manifests import (
    ArtifactRef,
    ReportManifest,
    RunManifest,
    StageStats,
)
from linkdiscovery.contracts.proposals import (
    Confidence,
    Evidence,
    LinkProposal,
    ProposalSet,
    ReviewState,
)
from linkdiscovery.contracts.reviews import (
    DecisionKind,
    ReasonCode,
    ReviewDecision,
    ReviewHistory,
)
from linkdiscovery.contracts.units import (
    ProcessedCorpus,
    ProcessedDocument,
    Region,
    RegionKind,
    SemanticUnit,
    Span,
)

__all__ = [
    "ArtifactHeader",
    "ArtifactRef",
    "CandidatePair",
    "CandidateSet",
    "Confidence",
    "Corpus",
    "DecisionKind",
    "DocumentFlags",
    "EmbeddingIndex",
    "EmbeddingRecord",
    "Evidence",
    "LinkProposal",
    "ProcessedCorpus",
    "ProcessedDocument",
    "ProposalSet",
    "ReasonCode",
    "Region",
    "RegionKind",
    "Relationship",
    "RelationshipSet",
    "ReportManifest",
    "ReviewDecision",
    "ReviewHistory",
    "ReviewState",
    "RunManifest",
    "RuntimeReport",
    "SemanticUnit",
    "SourceDocument",
    "Span",
    "StageStats",
    "UnitMatch",
    "utc_now_iso",
]
