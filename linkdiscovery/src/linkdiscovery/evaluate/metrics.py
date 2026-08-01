"""Recovery and reviewer-quality metrics over contract types.

Implements the SPEC "Evaluation and calibration" metrics: held-out link
recovery (recall at ``k``, mean reciprocal rank, degree breakdowns) and the
primary human-review quality metrics (reviewer precision at ``k``, acceptance
rate, corpus coverage, recommendation concentration).

Every function is pure and deterministic, and empty inputs yield well-defined
zeros — never a ``ZeroDivisionError``.

Matching is direction-agnostic: a held-out ``(source, target)`` counts as
recovered by any proposal over the same unordered document pair. Retrieval
starts from unordered pairs and direction is a presentation decision, so
penalizing a proposal for proposing the reverse direction of a known link
would measure the direction heuristic, not recovery.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from linkdiscovery.contracts.reviews import DecisionKind
from linkdiscovery.evaluate.holdout import DEGREE_BUCKETS, degree_bucket

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from linkdiscovery.contracts.documents import RelationshipSet
    from linkdiscovery.contracts.proposals import LinkProposal, ProposalSet
    from linkdiscovery.contracts.reviews import ReviewHistory

__all__ = ["recovery_by_degree", "recovery_metrics", "reviewer_precision_at_k"]


def _unordered(a: str, b: str) -> tuple[str, str]:
    """Canonical unordered document-pair key."""
    return (a, b) if a <= b else (b, a)


def _ordered_proposals(proposals: ProposalSet) -> list[LinkProposal]:
    """Proposals in global rank order with deterministic id tie-breaking."""
    return sorted(proposals.proposals, key=lambda p: (p.rank, p.id))


def _proposals_by_document(ordered: Sequence[LinkProposal]) -> dict[str, list[LinkProposal]]:
    """Rank-ordered proposals touching each document (as source or target)."""
    by_document: dict[str, list[LinkProposal]] = {}
    for proposal in ordered:
        by_document.setdefault(proposal.source_document_id, []).append(proposal)
        if proposal.target_document_id != proposal.source_document_id:
            by_document.setdefault(proposal.target_document_id, []).append(proposal)
    return by_document


def _holdout_items(held_out: RelationshipSet) -> list[tuple[str, tuple[str, str]]]:
    """Distinct held-out links as ``(source_document, unordered_pair)``.

    Deduplicated so a link serialized twice is not double-counted; the
    source document is kept because recall is computed per source document.
    Self-relationships (a document linking to itself, for example via a
    pure-anchor link) are skipped: proposals never contain self-pairs, so a
    self link is not a recoverable target and would only deflate recall.
    """
    items: list[tuple[str, tuple[str, str]]] = []
    seen: set[tuple[str, tuple[str, str]]] = set()
    for relationship in held_out.relationships:
        if relationship.source_id == relationship.target_id:
            continue
        key = (relationship.source_id, _unordered(relationship.source_id, relationship.target_id))
        if key not in seen:
            seen.add(key)
            items.append(key)
    return items


def _per_document_rank(
    by_document: dict[str, list[LinkProposal]], document_id: str, pair: tuple[str, str]
) -> int:
    """1-based rank of ``pair`` among proposals touching ``document_id``; 0 if absent."""
    for position, proposal in enumerate(by_document.get(document_id, ()), start=1):
        if _unordered(proposal.source_document_id, proposal.target_document_id) == pair:
            return position
    return 0


def recovery_metrics(
    proposals: ProposalSet,
    held_out: RelationshipSet,
    *,
    k_values: Sequence[int] = (1, 5, 10, 25),
) -> dict[str, float]:
    """Held-out link recovery: per-document recall at ``k``, MRR, and counts.

    Recall at ``k`` is computed per source document, not over the global
    ranking: with many documents almost every document's links fall outside
    a global top-``k``, making global recall@k nearly useless. For each
    held-out link from document ``d``, the link is recovered at ``k`` when
    its unordered pair appears within the top-``k`` proposals whose source
    or target is ``d`` (ordered by rank, ties broken by id). ``mrr`` is the
    mean reciprocal per-document rank, contributing 0 when the pair is
    absent. ``recovered_count`` counts held-out links found at any rank and
    ``holdout_count`` the distinct held-out links. Empty inputs yield zeros.
    """
    items = _holdout_items(held_out)
    result = {f"recall_at_{k}": 0.0 for k in k_values}
    result["mrr"] = 0.0
    result["recovered_count"] = 0.0
    result["holdout_count"] = float(len(items))
    if not items:
        return result

    by_document = _proposals_by_document(_ordered_proposals(proposals))
    ranks = [_per_document_rank(by_document, document, pair) for document, pair in items]
    total = len(items)
    for k in k_values:
        found = sum(1 for rank in ranks if 0 < rank <= k)
        result[f"recall_at_{k}"] = found / total
    result["mrr"] = sum(1.0 / rank for rank in ranks if rank > 0) / total
    result["recovered_count"] = float(sum(1 for rank in ranks if rank > 0))
    return result


def recovery_by_degree(
    proposals: ProposalSet,
    held_out: RelationshipSet,
    visible: RelationshipSet,
    k: int = 10,
) -> dict[str, dict[str, float]]:
    """Per-document recall at ``k`` bucketed by visible source out-degree.

    The SPEC asks for recovery breakdowns by graph degree: hiding links from
    hub documents is easier to recover from than hiding a sparse document's
    only link. Each held-out link is bucketed by its source document's
    out-degree over the *visible* relationships (:func:`~linkdiscovery.
    evaluate.holdout.degree_bucket`), and per-bucket ``recall_at_k``,
    ``holdout_count``, and ``recovered_count`` (within ``k``) are reported.
    All buckets are always present; empty buckets carry zeros.
    """
    visible_degree: dict[str, int] = {}
    for relationship in visible.relationships:
        visible_degree[relationship.source_id] = visible_degree.get(relationship.source_id, 0) + 1

    by_document = _proposals_by_document(_ordered_proposals(proposals))
    buckets = {
        name: {"recall_at_k": 0.0, "holdout_count": 0.0, "recovered_count": 0.0}
        for name in DEGREE_BUCKETS
    }
    for document, pair in _holdout_items(held_out):
        bucket = buckets[degree_bucket(visible_degree.get(document, 0))]
        bucket["holdout_count"] += 1.0
        rank = _per_document_rank(by_document, document, pair)
        if 0 < rank <= k:
            bucket["recovered_count"] += 1.0
    for bucket in buckets.values():
        if bucket["holdout_count"] > 0:
            bucket["recall_at_k"] = bucket["recovered_count"] / bucket["holdout_count"]
    return buckets


def _latest_decision_kinds(history: ReviewHistory) -> dict[str, DecisionKind]:
    """The authoritative (latest, by append order) decision kind per proposal id.

    Local to this module so evaluation depends only on contract types, not
    on the reporting package.
    """
    latest: dict[str, DecisionKind] = {}
    for decision in history.decisions:
        latest[decision.proposal_id] = decision.decision
    return latest


def _gini(values: Iterable[float]) -> float:
    """Gini coefficient of non-negative values; 0.0 for empty or all-zero input.

    Formula (sorted ascending, 1-based index ``i``):
    ``G = 2 * sum(i * x_i) / (n * sum(x)) - (n + 1) / n``. 0 means proposals
    are spread evenly across documents; values near 1 mean they concentrate
    on a few documents.
    """
    ordered = sorted(values)
    n = len(ordered)
    total = sum(ordered)
    if n == 0 or total == 0:
        return 0.0
    weighted = sum(index * value for index, value in enumerate(ordered, start=1))
    return (2.0 * weighted) / (n * total) - (n + 1.0) / n


def reviewer_precision_at_k(
    proposals: ProposalSet,
    history: ReviewHistory,
    *,
    k_values: Sequence[int] = (5, 10, 25),
) -> dict[str, float]:
    """Reviewer quality metrics: precision at ``k``, acceptance, coverage, Gini.

    ``precision_at_{k}`` is computed over decided proposals only: among
    proposals with global rank <= ``k`` that carry a review decision (latest
    per proposal wins), the fraction whose decision is ``accept``. Undecided
    proposals are excluded rather than counted as failures — an unreviewed
    proposal is missing data, not a rejection — so precision stays
    meaningful on partially reviewed sets. ``acceptance_rate`` is accepted /
    decided over the whole set.

    ``coverage`` approximates corpus coverage as the fraction of distinct
    document ids appearing anywhere in the proposal set that also appear in
    at least one top-``k`` proposal, using the largest ``k`` in ``k_values``
    (the review horizon). ``concentration`` is the Gini coefficient over
    per-document proposal counts (each proposal counts once for its source
    and once for its target document); see :func:`_gini` for the formula.
    Empty inputs yield zeros.
    """
    ordered = _ordered_proposals(proposals)
    latest = _latest_decision_kinds(history)
    decided = [(p, latest[p.id]) for p in ordered if p.id in latest]

    result: dict[str, float] = {}
    for k in k_values:
        top = [(p, kind) for p, kind in decided if p.rank <= k]
        accepted = sum(1 for _, kind in top if kind is DecisionKind.ACCEPT)
        result[f"precision_at_{k}"] = accepted / len(top) if top else 0.0

    accepted_total = sum(1 for _, kind in decided if kind is DecisionKind.ACCEPT)
    result["acceptance_rate"] = accepted_total / len(decided) if decided else 0.0

    all_documents = {p.source_document_id for p in ordered} | {
        p.target_document_id for p in ordered
    }
    k_max = max(k_values, default=0)
    covered = {p.source_document_id for p in ordered if p.rank <= k_max} | {
        p.target_document_id for p in ordered if p.rank <= k_max
    }
    result["coverage"] = len(covered) / len(all_documents) if all_documents else 0.0

    counts: dict[str, float] = dict.fromkeys(all_documents, 0.0)
    for proposal in ordered:
        counts[proposal.source_document_id] += 1.0
        counts[proposal.target_document_id] += 1.0
    result["concentration"] = _gini(counts.values())
    return result
