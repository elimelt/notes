"""Proposal contracts: evidence, link proposals, review state, proposal sets.

A proposal is a ranked candidate with direction, evidence, and review state.
Raw feature values are required: a scalar score without component features
and evidence is not a valid proposal. The JSON shape matches the SPEC
"LinkProposal" example exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from linkdiscovery.contracts.base import (
    ArtifactHeader,
    check_schema_version,
    expect_bool,
    expect_float,
    expect_header,
    expect_int,
    expect_list,
    expect_mapping,
    expect_nullable_str,
    expect_str,
    expect_str_float_map,
)
from linkdiscovery.contracts.units import Span
from linkdiscovery.errors import ContractError

__all__ = [
    "DIRECTIONS",
    "REVIEW_STATUSES",
    "SCHEMA_VERSION",
    "Confidence",
    "Evidence",
    "LinkProposal",
    "ProposalSet",
    "ReviewState",
]

SCHEMA_VERSION = 1
"""Schema version for proposal-set artifacts."""

DIRECTIONS = frozenset({"source-to-target", "target-to-source", "undirected"})
"""Valid values for ``LinkProposal.direction``."""

REVIEW_STATUSES = frozenset({"unreviewed", "accepted", "rejected", "deferred"})
"""Valid values for ``ReviewState.status``."""


class Confidence(StrEnum):
    """Calibrated confidence band for a proposal.

    Bands derive from the ranker's relatedness, usefulness, and missingness
    estimates plus calibration data; they are presentation-level and never a
    substitute for the raw features.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class Evidence:
    """One supporting unit match with source locations, per the SPEC JSON shape.

    ``similarity`` is the raw value for this unit pair; spans locate the
    matched text in each document's raw content so a reviewer can inspect the
    exact passages behind the proposal.
    """

    source_unit_id: str
    target_unit_id: str
    similarity: float
    source_spans: tuple[Span, ...] = ()
    target_spans: tuple[Span, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives matching the SPEC JSON shape."""
        return {
            "source_unit_id": self.source_unit_id,
            "target_unit_id": self.target_unit_id,
            "similarity": self.similarity,
            "source_spans": [span.to_dict() for span in self.source_spans],
            "target_spans": [span.to_dict() for span in self.target_spans],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Evidence:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "Evidence"
        mapping = expect_mapping(data, context)

        def spans(name: str) -> tuple[Span, ...]:
            items = expect_list(mapping, name, context, default=[])
            return tuple(
                Span.from_dict(expect_mapping(item, f"{context}: field '{name}[{index}]'"))
                for index, item in enumerate(items)
            )

        return cls(
            source_unit_id=expect_str(mapping, "source_unit_id", context),
            target_unit_id=expect_str(mapping, "target_unit_id", context),
            similarity=expect_float(mapping, "similarity", context),
            source_spans=spans("source_spans"),
            target_spans=spans("target_spans"),
        )


@dataclass(frozen=True, slots=True)
class ReviewState:
    """The review status embedded in a proposal.

    ``status`` is one of ``unreviewed``, ``accepted``, ``rejected``,
    ``deferred`` (enforced at construction); ``reason`` is an optional reason
    code or free-form note recorded at review time. Durable review decisions
    live in :class:`~linkdiscovery.contracts.reviews.ReviewHistory`; this is
    the denormalized snapshot a reporter shows.
    """

    status: str = "unreviewed"
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in REVIEW_STATUSES:
            allowed = ", ".join(sorted(REVIEW_STATUSES))
            raise ContractError(
                f"ReviewState: unknown status {self.status!r}; expected one of: {allowed}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {"status": self.status, "reason": self.reason}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewState:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "ReviewState"
        mapping = expect_mapping(data, context)
        return cls(
            status=expect_str(mapping, "status", context, default="unreviewed"),
            reason=expect_nullable_str(mapping, "reason", context),
        )


@dataclass(frozen=True, slots=True)
class LinkProposal:
    """A ranked candidate with direction, evidence, and review state.

    Matches the SPEC "LinkProposal" JSON shape exactly. Invariants (enforced
    at construction): ``direction`` is a member of :data:`DIRECTIONS`;
    ``rank`` is >= 1; ``id`` is stable for a fixed pair and ranking version;
    ``ranking_version`` is the ranker fingerprint, so scores are never
    compared across incompatible ranking versions.
    """

    id: str
    source_document_id: str
    target_document_id: str
    direction: str
    rank: int
    score: float
    confidence: Confidence
    features: dict[str, float] = field(default_factory=dict)
    evidence: tuple[Evidence, ...] = ()
    existing_relationship: bool = False
    ranking_version: str = ""
    review: ReviewState = field(default_factory=ReviewState)

    def __post_init__(self) -> None:
        if self.direction not in DIRECTIONS:
            allowed = ", ".join(sorted(DIRECTIONS))
            raise ContractError(
                f"LinkProposal {self.id!r}: unknown direction {self.direction!r}; "
                f"expected one of: {allowed}"
            )
        if self.rank < 1:
            raise ContractError(f"LinkProposal {self.id!r}: rank must be >= 1, got {self.rank}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives matching the SPEC JSON shape."""
        return {
            "id": self.id,
            "source_document_id": self.source_document_id,
            "target_document_id": self.target_document_id,
            "direction": self.direction,
            "rank": self.rank,
            "score": self.score,
            "confidence": self.confidence.value,
            "features": dict(self.features),
            "evidence": [item.to_dict() for item in self.evidence],
            "existing_relationship": self.existing_relationship,
            "ranking_version": self.ranking_version,
            "review": self.review.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LinkProposal:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "LinkProposal"
        mapping = expect_mapping(data, context)
        confidence_value = expect_str(mapping, "confidence", context)
        try:
            confidence = Confidence(confidence_value)
        except ValueError as exc:
            allowed = ", ".join(band.value for band in Confidence)
            raise ContractError(
                f"{context}: unknown confidence {confidence_value!r}; expected one of: {allowed}"
            ) from exc
        evidence_items = expect_list(mapping, "evidence", context, default=[])
        review_data = mapping.get("review")
        review = (
            ReviewState.from_dict(expect_mapping(review_data, f"{context}: field 'review'"))
            if review_data is not None
            else ReviewState()
        )
        return cls(
            id=expect_str(mapping, "id", context),
            source_document_id=expect_str(mapping, "source_document_id", context),
            target_document_id=expect_str(mapping, "target_document_id", context),
            direction=expect_str(mapping, "direction", context),
            rank=expect_int(mapping, "rank", context),
            score=expect_float(mapping, "score", context),
            confidence=confidence,
            features=expect_str_float_map(mapping, "features", context, default={}),
            evidence=tuple(
                Evidence.from_dict(expect_mapping(item, f"{context}: field 'evidence[{index}]'"))
                for index, item in enumerate(evidence_items)
            ),
            existing_relationship=expect_bool(
                mapping, "existing_relationship", context, default=False
            ),
            ranking_version=expect_str(mapping, "ranking_version", context, default=""),
            review=review,
        )


@dataclass(frozen=True, slots=True)
class ProposalSet:
    """The ranked output of one run: an artifact-level contract.

    Invariant (enforced at construction): proposal IDs are unique. Order
    follows presentation rank after the diversity policy; the raw candidate
    record is never suppressed by diversity, only re-ranked.
    """

    header: ArtifactHeader
    proposals: tuple[LinkProposal, ...] = ()

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for proposal in self.proposals:
            if proposal.id in seen:
                raise ContractError(f"ProposalSet: duplicate proposal id {proposal.id!r}")
            seen.add(proposal.id)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "header": self.header.to_dict(),
            "proposals": [proposal.to_dict() for proposal in self.proposals],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProposalSet:
        """Deserialize, raising ``ContractError`` on invalid or unknown-version input."""
        context = "ProposalSet"
        mapping = expect_mapping(data, context)
        header = expect_header(mapping, context)
        check_schema_version(header, SCHEMA_VERSION, context)
        proposals = expect_list(mapping, "proposals", context, default=[])
        return cls(
            header=header,
            proposals=tuple(
                LinkProposal.from_dict(
                    expect_mapping(item, f"{context}: field 'proposals[{index}]'")
                )
                for index, item in enumerate(proposals)
            ),
        )
