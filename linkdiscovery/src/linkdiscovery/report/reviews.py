"""Durable review decisions: persistence, merging, application, and queueing.

Human decisions are durable data (SPEC design principle 7): accepted,
rejected, and deferred candidates become reusable evaluation and calibration
records. This module persists :class:`~linkdiscovery.contracts.reviews.
ReviewHistory` artifacts atomically, merges new decisions (newest per
proposal wins), projects the latest decisions onto a proposal set's
denormalized :class:`~linkdiscovery.contracts.proposals.ReviewState`, and
builds the SPEC "Human review set" stratified queue.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING

from linkdiscovery.contracts.proposals import ProposalSet, ReviewState
from linkdiscovery.contracts.reviews import DecisionKind, ReviewDecision, ReviewHistory
from linkdiscovery.errors import LinkDiscoveryError, ReportError
from linkdiscovery.fingerprint import canonical_json
from linkdiscovery.report._io import atomic_write_text

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from linkdiscovery.contracts.proposals import LinkProposal

__all__ = [
    "apply_reviews",
    "build_review_queue",
    "latest_decisions",
    "load_review_history",
    "merge_decisions",
    "save_review_history",
]

_STATUS_BY_DECISION = {
    DecisionKind.ACCEPT: "accepted",
    DecisionKind.REJECT: "rejected",
    DecisionKind.DEFER: "deferred",
}


def save_review_history(history: ReviewHistory, path: Path) -> None:
    """Atomically persist a review history as canonical JSON at ``path``.

    The file is the artifact's ``to_dict()`` form, so it round-trips through
    :func:`load_review_history`. Raises
    :class:`~linkdiscovery.errors.ReportError` on write failure.
    """
    atomic_write_text(path, canonical_json(history.to_dict()) + "\n")


def load_review_history(path: Path) -> ReviewHistory:
    """Load a review history saved by :func:`save_review_history`.

    Raises :class:`~linkdiscovery.errors.ReportError` with an actionable
    message when the file is missing, unreadable, not valid JSON, or does
    not satisfy the ``ReviewHistory`` contract.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReportError(
            f"cannot read review history {path}: {exc}; "
            "pass the path produced by save_review_history"
        ) from exc
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ReportError(
            f"review history {path} is not valid JSON: {exc}; "
            "the file may be corrupt or not a review-history artifact"
        ) from exc
    if not isinstance(data, dict):
        raise ReportError(
            f"review history {path} must contain a JSON object, got {type(data).__name__}"
        )
    try:
        return ReviewHistory.from_dict(data)
    except LinkDiscoveryError as exc:
        raise ReportError(f"review history {path} violates the contract: {exc}") from exc


def latest_decisions(history: ReviewHistory) -> dict[str, ReviewDecision]:
    """The authoritative (latest) decision per proposal id.

    Decision order is chronological append order, so a later decision for
    the same proposal supersedes an earlier one.
    """
    latest: dict[str, ReviewDecision] = {}
    for decision in history.decisions:
        latest.pop(decision.proposal_id, None)
        latest[decision.proposal_id] = decision
    return latest


def merge_decisions(history: ReviewHistory, new: Sequence[ReviewDecision]) -> ReviewHistory:
    """Merge ``new`` decisions into ``history``, newest per proposal winning.

    Ordering rule: existing decisions come first, then ``new`` in sequence
    order; the decision appearing latest for a proposal id wins (so a
    decision later in ``new`` overrides both the history and earlier entries
    of ``new``). The result keeps one decision per proposal, ordered by when
    the winning decision was appended, preserving the contract's
    chronological-append semantics. The header is carried over unchanged.
    """
    merged = ReviewHistory(header=history.header, decisions=history.decisions + tuple(new))
    return ReviewHistory(header=history.header, decisions=tuple(latest_decisions(merged).values()))


def apply_reviews(proposals: ProposalSet, history: ReviewHistory) -> ProposalSet:
    """Return a new proposal set carrying the latest review decisions.

    Each proposal whose id has a decision in ``history`` gets a fresh
    :class:`~linkdiscovery.contracts.proposals.ReviewState` with the mapped
    status (``accept`` → ``accepted``, ``reject`` → ``rejected``, ``defer``
    → ``deferred``) and the decision's reason code (or ``None``). Decisions
    that match no proposal are ignored: proposal ids embed the ranking
    version, so a history legitimately contains decisions for proposals of
    older ranking versions. Inputs are immutable and unchanged.
    """
    latest = latest_decisions(history)
    updated: list[LinkProposal] = []
    for proposal in proposals.proposals:
        decision = latest.get(proposal.id)
        if decision is None:
            updated.append(proposal)
            continue
        review = ReviewState(
            status=_STATUS_BY_DECISION[decision.decision],
            reason=decision.reason.value if decision.reason is not None else None,
        )
        updated.append(replace(proposal, review=review))
    return ProposalSet(header=proposals.header, proposals=tuple(updated))


def build_review_queue(
    proposals: ProposalSet,
    *,
    size: int,
    seed: int,
    near_threshold_band: tuple[float, float] = (0.4, 0.6),
) -> tuple[LinkProposal, ...]:
    """Build the SPEC "Human review set" stratified queue, deterministically.

    Strata (filled in this order, skipping already-selected proposals):

    - ~40% top-ranked proposals (``size - 3 * (size // 5)``),
    - ~20% proposals whose score lies within ``near_threshold_band``
      (inclusive) — candidates near decision thresholds,
    - ~20% random sample of the remaining proposals, drawn with
      ``random.Random(seed)`` from a rank-sorted pool, so the same seed
      always yields the same queue,
    - ~20% proposals from underrepresented source documents (documents with
      the fewest proposals in the set).

    Any stratum that runs short is backfilled from the top-ranked remainder.
    The result contains no duplicates and is returned in rank order (ties
    broken by proposal id). When ``size`` covers the whole set, every
    proposal is returned; a non-positive ``size`` yields an empty queue.
    """
    ordered = sorted(proposals.proposals, key=lambda p: (p.rank, p.id))
    if size <= 0:
        return ()
    if size >= len(ordered):
        return tuple(ordered)

    per_stratum = size // 5
    n_top = size - 3 * per_stratum
    selected: dict[str, LinkProposal] = {}

    def take(candidates: Sequence[LinkProposal], count: int) -> None:
        taken = 0
        for proposal in candidates:
            if taken >= count:
                break
            if proposal.id in selected:
                continue
            selected[proposal.id] = proposal
            taken += 1

    take(ordered, n_top)

    low, high = near_threshold_band
    take([p for p in ordered if low <= p.score <= high], per_stratum)

    pool = [p for p in ordered if p.id not in selected]
    rng = random.Random(seed)
    for proposal in rng.sample(pool, min(per_stratum, len(pool))):
        selected[proposal.id] = proposal

    counts = Counter(p.source_document_id for p in ordered)
    underrepresented = sorted(
        (p for p in ordered if p.id not in selected),
        key=lambda p: (counts[p.source_document_id], p.rank, p.id),
    )
    take(underrepresented, per_stratum)

    take(ordered, size - len(selected))
    return tuple(sorted(selected.values(), key=lambda p: (p.rank, p.id)))
