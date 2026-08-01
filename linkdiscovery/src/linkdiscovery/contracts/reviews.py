"""Review contracts: durable human decisions and the review history artifact.

Human decisions are durable data (SPEC design principle 7): accepted,
rejected, and deferred candidates become reusable evaluation and calibration
records. A rejection is not a universal negative — it may be specific to
direction, placement, timing, or corpus structure — which is why decisions
carry reason codes and free-form notes rather than a bare boolean.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from linkdiscovery.contracts.base import (
    ArtifactHeader,
    check_schema_version,
    expect_header,
    expect_list,
    expect_mapping,
    expect_nullable_str,
    expect_str,
)
from linkdiscovery.errors import ContractError

__all__ = [
    "SCHEMA_VERSION",
    "DecisionKind",
    "ReasonCode",
    "ReviewDecision",
    "ReviewHistory",
]

SCHEMA_VERSION = 1
"""Schema version for review-history artifacts."""


class DecisionKind(StrEnum):
    """The three review verdicts defined by the SPEC."""

    ACCEPT = "accept"
    REJECT = "reject"
    DEFER = "defer"


class ReasonCode(StrEnum):
    """Recommended reason codes from the SPEC "Human review set" section."""

    ALREADY_RELATED = "already_related"
    USEFUL_BRIDGE = "useful_bridge"
    TOO_GENERIC = "too_generic"
    DUPLICATE = "duplicate"
    WEAK_EVIDENCE = "weak_evidence"
    WRONG_DIRECTION = "wrong_direction"
    BAD_PLACEMENT = "bad_placement"


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    """One durable human decision about one proposal.

    ``proposal_id`` refers to a :class:`~linkdiscovery.contracts.proposals.
    LinkProposal` id, which embeds the pair and ranking version, so decisions
    remain interpretable after re-ranking. ``reason`` is optional and drawn
    from :class:`ReasonCode`; ``note`` is free-form reviewer text;
    ``decided_at`` is an ISO-8601 timestamp string.
    """

    proposal_id: str
    decision: DecisionKind
    reason: ReasonCode | None = None
    note: str = ""
    reviewer: str = ""
    decided_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "proposal_id": self.proposal_id,
            "decision": self.decision.value,
            "reason": self.reason.value if self.reason else None,
            "note": self.note,
            "reviewer": self.reviewer,
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewDecision:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "ReviewDecision"
        mapping = expect_mapping(data, context)
        decision_value = expect_str(mapping, "decision", context)
        try:
            decision = DecisionKind(decision_value)
        except ValueError as exc:
            allowed = ", ".join(kind.value for kind in DecisionKind)
            raise ContractError(
                f"{context}: unknown decision {decision_value!r}; expected one of: {allowed}"
            ) from exc
        reason_value = expect_nullable_str(mapping, "reason", context)
        reason: ReasonCode | None = None
        if reason_value is not None:
            try:
                reason = ReasonCode(reason_value)
            except ValueError as exc:
                allowed = ", ".join(code.value for code in ReasonCode)
                raise ContractError(
                    f"{context}: unknown reason code {reason_value!r}; expected one of: {allowed}"
                ) from exc
        return cls(
            proposal_id=expect_str(mapping, "proposal_id", context),
            decision=decision,
            reason=reason,
            note=expect_str(mapping, "note", context, default=""),
            reviewer=expect_str(mapping, "reviewer", context, default=""),
            decided_at=expect_str(mapping, "decided_at", context, default=""),
        )


@dataclass(frozen=True, slots=True)
class ReviewHistory:
    """All durable review decisions available to a run: an artifact-level contract.

    Multiple decisions may exist for one proposal (a reviewer can revise);
    order is chronological append order and the latest decision per proposal
    is authoritative for calibration.
    """

    header: ArtifactHeader
    decisions: tuple[ReviewDecision, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "header": self.header.to_dict(),
            "decisions": [decision.to_dict() for decision in self.decisions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewHistory:
        """Deserialize, raising ``ContractError`` on invalid or unknown-version input."""
        context = "ReviewHistory"
        mapping = expect_mapping(data, context)
        header = expect_header(mapping, context)
        check_schema_version(header, SCHEMA_VERSION, context)
        decisions = expect_list(mapping, "decisions", context, default=[])
        return cls(
            header=header,
            decisions=tuple(
                ReviewDecision.from_dict(
                    expect_mapping(item, f"{context}: field 'decisions[{index}]'")
                )
                for index, item in enumerate(decisions)
            ),
        )
