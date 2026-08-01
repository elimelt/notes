"""Ranking stability across runs, devices, and index parameters.

SPEC acceptance criterion 11 requires equivalent candidate rankings on MPS
and CPU "within documented tolerance", and the reproducibility section asks
for measured top-k stability when approximate indexes cannot be built
deterministically. :func:`rank_agreement` quantifies both: set overlap of
the top-``k`` pairs, rank correlation over the shared pairs, and the maximum
score divergence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from linkdiscovery.contracts.proposals import ProposalSet

__all__ = ["rank_agreement"]


def _top_pairs(proposals: ProposalSet, k: int) -> dict[tuple[str, str], tuple[int, float]]:
    """The top-``k`` distinct unordered pairs mapped to ``(position, score)``.

    Proposals are walked in global rank order (ties broken by id); each
    pair's first occurrence defines its 1-based position and score, so
    reciprocal directed proposals collapse onto one pair.
    """
    result: dict[tuple[str, str], tuple[int, float]] = {}
    ordered = sorted(proposals.proposals, key=lambda p: (p.rank, p.id))
    for proposal in ordered:
        if len(result) >= k:
            break
        a, b = proposal.source_document_id, proposal.target_document_id
        pair = (a, b) if a <= b else (b, a)
        if pair not in result:
            result[pair] = (len(result) + 1, proposal.score)
    return result


def _dense_ranks(positions: Sequence[int]) -> NDArray[np.float64]:
    """Re-rank distinct positions to 1..n, preserving their relative order."""
    array = np.asarray(positions, dtype=np.int64)
    order = np.argsort(array, kind="stable")
    ranks = np.empty(len(positions), dtype=np.float64)
    ranks[order] = np.arange(1, len(positions) + 1, dtype=np.float64)
    return ranks


def _spearman(positions_a: Sequence[int], positions_b: Sequence[int]) -> float:
    """Spearman rank correlation over paired, distinct positions.

    Positions are dense-ranked to 1..n per side and the classic formula
    ``rho = 1 - 6 * sum(d^2) / (n * (n^2 - 1))`` is applied (valid because
    positions within one top-k list are distinct, so there are no ties).
    Defined edges: no shared pairs yields 0.0 (no evidence of agreement);
    exactly one shared pair yields 1.0 (it occupies the same relative rank
    in both lists).
    """
    n = len(positions_a)
    if n == 0:
        return 0.0
    if n == 1:
        return 1.0
    ranks_a = _dense_ranks(positions_a)
    ranks_b = _dense_ranks(positions_b)
    squared = float(np.sum((ranks_a - ranks_b) ** 2))
    return 1.0 - 6.0 * squared / (n * (n * n - 1))


def rank_agreement(a: ProposalSet, b: ProposalSet, *, k: int = 50) -> dict[str, float]:
    """Compare two rankings of the same corpus: overlap, correlation, divergence.

    Returns:

    - ``jaccard``: Jaccard overlap of the two top-``k`` unordered pair sets
      (1.0 when both are empty — two empty rankings agree perfectly).
    - ``spearman``: Spearman rank correlation over the shared pairs, using
      each pair's position within its own top-``k`` list (see
      :func:`_spearman` for the edge-case definitions).
    - ``score_divergence``: max ``|score_a - score_b|`` over shared pairs
      (0.0 when there are none); this is the number to check against a
      documented MPS-vs-CPU tolerance.
    - ``shared_pairs``: the number of shared pairs the correlation and
      divergence were computed over.

    Deterministic, pure, and safe on empty inputs.
    """
    top_a = _top_pairs(a, k)
    top_b = _top_pairs(b, k)
    union = set(top_a) | set(top_b)
    shared = sorted(set(top_a) & set(top_b))
    jaccard = len(shared) / len(union) if union else 1.0

    positions_a = [top_a[pair][0] for pair in shared]
    positions_b = [top_b[pair][0] for pair in shared]
    divergence = max(
        (abs(top_a[pair][1] - top_b[pair][1]) for pair in shared),
        default=0.0,
    )
    return {
        "jaccard": jaccard,
        "spearman": _spearman(positions_a, positions_b),
        "score_divergence": divergence,
        "shared_pairs": float(len(shared)),
    }
