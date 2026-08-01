"""Candidate contracts: unit matches, document pairs, and the candidate set.

Candidate generation optimizes recall and leaves precision to the ranker, so
these types deliberately carry raw retrieval evidence (the strongest unit
matches per pair, with views and similarities) rather than a judgment.
Evidence survives aggregation: a document pair always points back to the unit
matches that produced it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from linkdiscovery.contracts.base import (
    ArtifactHeader,
    check_schema_version,
    expect_float,
    expect_header,
    expect_list,
    expect_mapping,
    expect_str,
    expect_str_float_map,
)
from linkdiscovery.errors import ContractError

__all__ = [
    "SCHEMA_VERSION",
    "CandidatePair",
    "CandidateSet",
    "UnitMatch",
]

SCHEMA_VERSION = 1
"""Schema version for candidate-set artifacts."""


@dataclass(frozen=True, slots=True)
class UnitMatch:
    """One retrieved semantic-unit pair with its similarity.

    ``view`` names the retrieval view the match came from (``document``,
    ``section``, ``title``, or a registered extension). ``similarity`` is the
    raw cosine (or equivalent normalized dot product) value, unadjusted.
    """

    source_unit_id: str
    target_unit_id: str
    view: str
    similarity: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "source_unit_id": self.source_unit_id,
            "target_unit_id": self.target_unit_id,
            "view": self.view,
            "similarity": self.similarity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnitMatch:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "UnitMatch"
        mapping = expect_mapping(data, context)
        return cls(
            source_unit_id=expect_str(mapping, "source_unit_id", context),
            target_unit_id=expect_str(mapping, "target_unit_id", context),
            view=expect_str(mapping, "view", context),
            similarity=expect_float(mapping, "similarity", context),
        )


@dataclass(frozen=True, slots=True)
class CandidatePair:
    """A canonical (deduplicated, alias-resolved) document pair.

    Invariant (enforced at construction): no self-pairs — the generator must
    resolve aliases before pair construction. ``matches`` preserves the
    strongest supporting unit pairs across views; ``features`` carries
    aggregation outputs (document similarity, top-r means, breadth, length
    stats) computed in the pair-aggregation phase.
    """

    source_document_id: str
    target_document_id: str
    matches: tuple[UnitMatch, ...] = ()
    features: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.source_document_id == self.target_document_id:
            raise ContractError(
                f"CandidatePair: self-pair for document {self.source_document_id!r}; "
                "candidate generation must remove self-pairs and resolve aliases first"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "source_document_id": self.source_document_id,
            "target_document_id": self.target_document_id,
            "matches": [match.to_dict() for match in self.matches],
            "features": dict(self.features),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CandidatePair:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "CandidatePair"
        mapping = expect_mapping(data, context)
        matches = expect_list(mapping, "matches", context, default=[])
        return cls(
            source_document_id=expect_str(mapping, "source_document_id", context),
            target_document_id=expect_str(mapping, "target_document_id", context),
            matches=tuple(
                UnitMatch.from_dict(expect_mapping(item, f"{context}: field 'matches[{index}]'"))
                for index, item in enumerate(matches)
            ),
            features=expect_str_float_map(mapping, "features", context, default={}),
        )


@dataclass(frozen=True, slots=True)
class CandidateSet:
    """The bounded, high-recall retrieval output: an artifact-level contract.

    Pairs are ordered deterministically by the generator (its tie-breaking
    policy is part of its fingerprint, carried in the header's
    ``config_fingerprint``). This set contains no existing direct links, no
    excluded documents, and no self or alias-equivalent pairs.
    """

    header: ArtifactHeader
    pairs: tuple[CandidatePair, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "header": self.header.to_dict(),
            "pairs": [pair.to_dict() for pair in self.pairs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CandidateSet:
        """Deserialize, raising ``ContractError`` on invalid or unknown-version input."""
        context = "CandidateSet"
        mapping = expect_mapping(data, context)
        header = expect_header(mapping, context)
        check_schema_version(header, SCHEMA_VERSION, context)
        pairs = expect_list(mapping, "pairs", context, default=[])
        return cls(
            header=header,
            pairs=tuple(
                CandidatePair.from_dict(expect_mapping(item, f"{context}: field 'pairs[{index}]'"))
                for index, item in enumerate(pairs)
            ),
        )
