"""Hand-computed tests for cross-run ranking agreement (SPEC criterion 11)."""

from __future__ import annotations

import pytest

from linkdiscovery.contracts import Confidence, LinkProposal, ProposalSet
from linkdiscovery.evaluate import rank_agreement
from tests.conftest import make_header


def make_proposal(pid: str, source: str, target: str, rank: int, score: float) -> LinkProposal:
    return LinkProposal(
        id=pid,
        source_document_id=source,
        target_document_id=target,
        direction="source-to-target",
        rank=rank,
        score=score,
        confidence=Confidence.MEDIUM,
        features={"document_similarity": score},
    )


def proposal_set(*proposals: LinkProposal) -> ProposalSet:
    return ProposalSet(header=make_header(), proposals=proposals)


def three_pairs(ranks: tuple[int, int, int], scores: tuple[float, float, float]) -> ProposalSet:
    """Pairs (d1,d2), (d1,d3), (d2,d3) at the given ranks and scores."""
    return proposal_set(
        make_proposal("p12", "d1", "d2", ranks[0], scores[0]),
        make_proposal("p13", "d1", "d3", ranks[1], scores[1]),
        make_proposal("p23", "d2", "d3", ranks[2], scores[2]),
    )


class TestRankAgreement:
    def test_identical_rankings_agree_perfectly(self) -> None:
        a = three_pairs((1, 2, 3), (0.9, 0.8, 0.7))
        b = three_pairs((1, 2, 3), (0.9, 0.8, 0.7))
        assert rank_agreement(a, b, k=10) == {
            "jaccard": 1.0,
            "spearman": 1.0,
            "score_divergence": 0.0,
            "shared_pairs": 3.0,
        }

    def test_reversed_ranking_has_spearman_minus_one(self) -> None:
        a = three_pairs((1, 2, 3), (0.9, 0.8, 0.7))
        b = three_pairs((3, 2, 1), (0.6, 0.65, 0.7))
        result = rank_agreement(a, b, k=10)
        assert result["jaccard"] == 1.0
        # Dense ranks (1,2,3) vs (3,2,1): rho = 1 - 6*(4+0+4)/(3*8) = -1.
        assert result["spearman"] == pytest.approx(-1.0)
        # Divergence: max(|0.9-0.6|, |0.8-0.65|, |0.7-0.7|) = 0.3.
        assert result["score_divergence"] == pytest.approx(0.3)
        assert result["shared_pairs"] == 3.0

    def test_partial_overlap_jaccard(self) -> None:
        a = proposal_set(
            make_proposal("p1", "d1", "d2", 1, 0.9),
            make_proposal("p2", "d1", "d3", 2, 0.8),
        )
        b = proposal_set(
            make_proposal("q1", "d1", "d3", 1, 0.7),
            make_proposal("q2", "d4", "d5", 2, 0.6),
        )
        result = rank_agreement(a, b, k=2)
        # Top sets {12,13} and {13,45}: intersection 1, union 3.
        assert result["jaccard"] == pytest.approx(1 / 3)
        assert result["shared_pairs"] == 1.0
        assert result["spearman"] == 1.0  # single shared pair
        assert result["score_divergence"] == pytest.approx(0.1)  # |0.8 - 0.7|

    def test_k_truncates_both_rankings(self) -> None:
        a = three_pairs((1, 2, 3), (0.9, 0.8, 0.7))
        b = three_pairs((1, 3, 2), (0.9, 0.7, 0.8))
        result = rank_agreement(a, b, k=1)
        assert result == {
            "jaccard": 1.0,  # both top-1 sets are {(d1,d2)}
            "spearman": 1.0,
            "score_divergence": 0.0,
            "shared_pairs": 1.0,
        }

    def test_reciprocal_directions_collapse_to_one_pair(self) -> None:
        a = proposal_set(
            make_proposal("fwd", "d1", "d2", 1, 0.9),
            make_proposal("rev", "d2", "d1", 2, 0.85),
            make_proposal("other", "d3", "d4", 3, 0.5),
        )
        b = proposal_set(
            make_proposal("fwd", "d1", "d2", 1, 0.9),
            make_proposal("other", "d3", "d4", 2, 0.5),
        )
        result = rank_agreement(a, b, k=2)
        assert result["jaccard"] == 1.0
        assert result["shared_pairs"] == 2.0
        assert result["score_divergence"] == 0.0  # first occurrence's score is used

    def test_disjoint_rankings(self) -> None:
        a = proposal_set(make_proposal("p1", "d1", "d2", 1, 0.9))
        b = proposal_set(make_proposal("q1", "d3", "d4", 1, 0.9))
        result = rank_agreement(a, b, k=5)
        assert result == {
            "jaccard": 0.0,
            "spearman": 0.0,
            "score_divergence": 0.0,
            "shared_pairs": 0.0,
        }

    def test_empty_rankings_agree(self) -> None:
        empty = proposal_set()
        result = rank_agreement(empty, empty, k=5)
        assert result["jaccard"] == 1.0  # two empty rankings agree perfectly
        assert result["spearman"] == 0.0
        assert result["score_divergence"] == 0.0
        assert result["shared_pairs"] == 0.0
