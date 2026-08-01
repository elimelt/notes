"""Hand-computed correctness tests for recovery and reviewer metrics."""

from __future__ import annotations

import pytest

from linkdiscovery.contracts import (
    Confidence,
    DecisionKind,
    LinkProposal,
    ProposalSet,
    Relationship,
    RelationshipSet,
    ReviewDecision,
    ReviewHistory,
)
from linkdiscovery.evaluate import (
    recovery_by_degree,
    recovery_metrics,
    reviewer_precision_at_k,
)
from tests.conftest import make_header


def make_proposal(pid: str, source: str, target: str, rank: int) -> LinkProposal:
    return LinkProposal(
        id=pid,
        source_document_id=source,
        target_document_id=target,
        direction="source-to-target",
        rank=rank,
        score=1.0 - 0.01 * rank,
        confidence=Confidence.MEDIUM,
        features={"document_similarity": 0.5},
    )


def proposal_set(*proposals: LinkProposal) -> ProposalSet:
    return ProposalSet(header=make_header(), proposals=proposals)


def rel(source: str, target: str, kind: str = "explicit-link") -> Relationship:
    return Relationship(source_id=source, target_id=target, kind=kind)


def rels(*relationships: Relationship) -> RelationshipSet:
    return RelationshipSet(relationships=relationships)


def decision(pid: str, kind: DecisionKind) -> ReviewDecision:
    return ReviewDecision(proposal_id=pid, decision=kind)


def history(*decisions: ReviewDecision) -> ReviewHistory:
    return ReviewHistory(header=make_header(), decisions=decisions)


class TestRecoveryMetrics:
    def proposals(self) -> ProposalSet:
        return proposal_set(
            make_proposal("p1", "a", "b", 1),
            make_proposal("p2", "a", "c", 2),
            make_proposal("p3", "b", "d", 3),
        )

    def test_hand_computed_values(self) -> None:
        # Held out: a->c (per-document rank 2 among a's proposals p1, p2)
        # and b->e (never proposed).
        metrics = recovery_metrics(
            self.proposals(), rels(rel("a", "c"), rel("b", "e")), k_values=(1, 2, 5)
        )
        assert metrics == {
            "recall_at_1": 0.0,
            "recall_at_2": 0.5,
            "recall_at_5": 0.5,
            "mrr": 0.25,  # (1/2 + 0) / 2
            "recovered_count": 1.0,
            "holdout_count": 2.0,
        }

    def test_direction_agnostic_matching(self) -> None:
        # Held-out c->a matches proposal a->c on the unordered pair; among
        # c's proposals p2 is the only one, so its per-document rank is 1.
        metrics = recovery_metrics(self.proposals(), rels(rel("c", "a")), k_values=(1,))
        assert metrics["recall_at_1"] == 1.0
        assert metrics["mrr"] == 1.0

    def test_duplicate_held_out_links_counted_once(self) -> None:
        metrics = recovery_metrics(
            self.proposals(), rels(rel("a", "c"), rel("a", "c")), k_values=(5,)
        )
        assert metrics["holdout_count"] == 1.0

    def test_empty_holdout_yields_zeros(self) -> None:
        metrics = recovery_metrics(self.proposals(), rels(), k_values=(1, 5))
        assert metrics == {
            "recall_at_1": 0.0,
            "recall_at_5": 0.0,
            "mrr": 0.0,
            "recovered_count": 0.0,
            "holdout_count": 0.0,
        }

    def test_empty_proposals_yield_zero_recall(self) -> None:
        metrics = recovery_metrics(proposal_set(), rels(rel("a", "b")), k_values=(5,))
        assert metrics["recall_at_5"] == 0.0
        assert metrics["holdout_count"] == 1.0
        assert metrics["mrr"] == 0.0


class TestRecoveryByDegree:
    def test_bucketed_by_visible_out_degree(self) -> None:
        proposals = proposal_set(
            make_proposal("p1", "a", "b", 1),
            make_proposal("p2", "a", "c", 2),
        )
        held_out = rels(rel("a", "c"), rel("b", "e"))
        visible = rels(
            rel("a", "x"),  # a has visible out-degree 1 -> bucket "1"
            *(rel("b", f"x{i}") for i in range(5)),  # b has 5 -> bucket "5+"
        )
        breakdown = recovery_by_degree(proposals, held_out, visible, k=10)
        assert breakdown == {
            "1": {"recall_at_k": 1.0, "holdout_count": 1.0, "recovered_count": 1.0},
            "2-4": {"recall_at_k": 0.0, "holdout_count": 0.0, "recovered_count": 0.0},
            "5+": {"recall_at_k": 0.0, "holdout_count": 1.0, "recovered_count": 0.0},
        }

    def test_zero_visible_degree_falls_into_sparse_bucket(self) -> None:
        breakdown = recovery_by_degree(proposal_set(), rels(rel("a", "b")), rels(), k=5)
        assert breakdown["1"]["holdout_count"] == 1.0
        assert breakdown["1"]["recall_at_k"] == 0.0

    def test_k_limits_recovery(self) -> None:
        proposals = proposal_set(
            make_proposal("p1", "a", "b", 1),
            make_proposal("p2", "a", "c", 2),
        )
        breakdown = recovery_by_degree(proposals, rels(rel("a", "c")), rels(), k=1)
        assert breakdown["1"]["recovered_count"] == 0.0  # pair sits at rank 2


class TestReviewerPrecisionAtK:
    def proposals(self) -> ProposalSet:
        return proposal_set(
            make_proposal("p1", "a", "b", 1),
            make_proposal("p2", "a", "c", 2),
            make_proposal("p3", "b", "c", 3),
            make_proposal("p4", "c", "d", 4),
        )

    def reviewed(self) -> ReviewHistory:
        # p4 is first rejected then accepted (latest wins); p3 is undecided.
        return history(
            decision("p4", DecisionKind.REJECT),
            decision("p1", DecisionKind.ACCEPT),
            decision("p2", DecisionKind.REJECT),
            decision("p4", DecisionKind.ACCEPT),
        )

    def test_hand_computed_values(self) -> None:
        metrics = reviewer_precision_at_k(self.proposals(), self.reviewed(), k_values=(2, 3))
        # Decided within rank<=2: p1 accept, p2 reject -> 1/2. Within
        # rank<=3: same (p3 undecided is excluded, not a failure).
        assert metrics["precision_at_2"] == 0.5
        assert metrics["precision_at_3"] == 0.5
        # 3 decided overall (p1, p2, p4 latest=accept) -> 2 accepted.
        assert metrics["acceptance_rate"] == pytest.approx(2 / 3)
        # Documents {a,b,c,d}; top-3 proposals cover {a,b,c} -> 3/4.
        assert metrics["coverage"] == 0.75
        # Per-document counts a:2 b:2 c:3 d:1 -> sorted [1,2,2,3]:
        # G = 2*(1*1+2*2+3*2+4*3)/(4*8) - 5/4 = 46/32 - 1.25 = 0.1875.
        assert metrics["concentration"] == pytest.approx(0.1875)

    def test_empty_history_yields_zero_precision(self) -> None:
        metrics = reviewer_precision_at_k(self.proposals(), history(), k_values=(5,))
        assert metrics["precision_at_5"] == 0.0
        assert metrics["acceptance_rate"] == 0.0
        assert metrics["coverage"] == 1.0  # all documents appear within rank<=5

    def test_empty_proposals_yield_zeros(self) -> None:
        metrics = reviewer_precision_at_k(
            proposal_set(), history(decision("p1", DecisionKind.ACCEPT)), k_values=(5,)
        )
        assert metrics == {
            "precision_at_5": 0.0,
            "acceptance_rate": 0.0,
            "coverage": 0.0,
            "concentration": 0.0,
        }

    def test_uniform_spread_has_zero_concentration(self) -> None:
        proposals = proposal_set(
            make_proposal("p1", "a", "b", 1),
            make_proposal("p2", "c", "d", 2),
        )
        metrics = reviewer_precision_at_k(proposals, history(), k_values=(5,))
        assert metrics["concentration"] == 0.0
