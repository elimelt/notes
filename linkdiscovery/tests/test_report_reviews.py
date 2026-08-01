"""Tests for durable review decisions: persistence, merge, apply, queue."""

from __future__ import annotations

from pathlib import Path

import pytest

from linkdiscovery.contracts import (
    Confidence,
    DecisionKind,
    LinkProposal,
    ProposalSet,
    ReasonCode,
    ReviewDecision,
    ReviewHistory,
)
from linkdiscovery.errors import ReportError
from linkdiscovery.report import (
    apply_reviews,
    build_review_queue,
    load_review_history,
    merge_decisions,
    save_review_history,
)
from tests.conftest import make_header


def make_proposal(
    pid: str, rank: int, *, source: str = "doc-a", score: float = 0.9
) -> LinkProposal:
    return LinkProposal(
        id=pid,
        source_document_id=source,
        target_document_id=f"target-of-{pid}",
        direction="source-to-target",
        rank=rank,
        score=score,
        confidence=Confidence.MEDIUM,
        features={"document_similarity": score},
    )


def decision(
    pid: str, kind: DecisionKind, *, reason: ReasonCode | None = None, decided_at: str = ""
) -> ReviewDecision:
    return ReviewDecision(proposal_id=pid, decision=kind, reason=reason, decided_at=decided_at)


def history(*decisions: ReviewDecision) -> ReviewHistory:
    return ReviewHistory(header=make_header(), decisions=decisions)


class TestPersistence:
    def test_save_load_round_trip(self, tmp_path: Path) -> None:
        original = history(
            decision("p1", DecisionKind.ACCEPT, decided_at="2026-07-31T13:00:00+00:00"),
            decision("p2", DecisionKind.REJECT, reason=ReasonCode.TOO_GENERIC),
        )
        path = tmp_path / "reviews" / "history.json"
        save_review_history(original, path)
        assert load_review_history(path) == original

    def test_load_missing_file_raises_actionable_error(self, tmp_path: Path) -> None:
        with pytest.raises(ReportError, match="cannot read review history"):
            load_review_history(tmp_path / "missing.json")

    def test_load_invalid_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "corrupt.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(ReportError, match="not valid JSON"):
            load_review_history(path)

    def test_load_non_object_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "list.json"
        path.write_text("[]", encoding="utf-8")
        with pytest.raises(ReportError, match="must contain a JSON object"):
            load_review_history(path)

    def test_load_contract_violation_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text('{"header": {}, "decisions": []}', encoding="utf-8")
        with pytest.raises(ReportError, match="violates the contract"):
            load_review_history(path)


class TestMergeDecisions:
    def test_new_decision_overrides_history(self) -> None:
        base = history(decision("p1", DecisionKind.ACCEPT))
        merged = merge_decisions(base, [decision("p1", DecisionKind.REJECT)])
        assert len(merged.decisions) == 1
        assert merged.decisions[0].decision is DecisionKind.REJECT

    def test_later_entry_in_new_wins(self) -> None:
        merged = merge_decisions(
            history(),
            [decision("p1", DecisionKind.REJECT), decision("p1", DecisionKind.DEFER)],
        )
        assert len(merged.decisions) == 1
        assert merged.decisions[0].decision is DecisionKind.DEFER

    def test_untouched_decisions_survive_in_chronological_order(self) -> None:
        base = history(decision("p1", DecisionKind.ACCEPT), decision("p2", DecisionKind.DEFER))
        merged = merge_decisions(base, [decision("p2", DecisionKind.ACCEPT)])
        assert [d.proposal_id for d in merged.decisions] == ["p1", "p2"]
        assert merged.decisions[1].decision is DecisionKind.ACCEPT
        assert merged.header == base.header

    def test_merge_with_empty_sequence_is_identity(self) -> None:
        base = history(decision("p1", DecisionKind.ACCEPT))
        assert merge_decisions(base, []) == base


class TestApplyReviews:
    def test_statuses_and_reasons_applied(self) -> None:
        proposals = ProposalSet(
            header=make_header(),
            proposals=(make_proposal("p1", 1), make_proposal("p2", 2), make_proposal("p3", 3)),
        )
        reviewed = apply_reviews(
            proposals,
            history(
                decision("p1", DecisionKind.ACCEPT),
                decision("p2", DecisionKind.REJECT, reason=ReasonCode.WEAK_EVIDENCE),
                decision("p3", DecisionKind.DEFER),
            ),
        )
        statuses = [p.review.status for p in reviewed.proposals]
        assert statuses == ["accepted", "rejected", "deferred"]
        assert reviewed.proposals[1].review.reason == "weak_evidence"
        assert reviewed.proposals[0].review.reason is None

    def test_latest_decision_wins(self) -> None:
        proposals = ProposalSet(header=make_header(), proposals=(make_proposal("p1", 1),))
        reviewed = apply_reviews(
            proposals,
            history(decision("p1", DecisionKind.REJECT), decision("p1", DecisionKind.ACCEPT)),
        )
        assert reviewed.proposals[0].review.status == "accepted"

    def test_unmatched_decisions_ignored_and_inputs_unchanged(self) -> None:
        proposals = ProposalSet(header=make_header(), proposals=(make_proposal("p1", 1),))
        reviewed = apply_reviews(
            proposals, history(decision("older-ranking-version-id", DecisionKind.ACCEPT))
        )
        assert reviewed.proposals[0].review.status == "unreviewed"
        assert proposals.proposals[0].review.status == "unreviewed"
        assert reviewed.header == proposals.header

    def test_undecided_proposals_keep_state(self) -> None:
        proposals = ProposalSet(
            header=make_header(), proposals=(make_proposal("p1", 1), make_proposal("p2", 2))
        )
        reviewed = apply_reviews(proposals, history(decision("p1", DecisionKind.ACCEPT)))
        assert reviewed.proposals[1].review.status == "unreviewed"


def stratified_set() -> ProposalSet:
    """40 proposals: a hub document, a mid band-scored document, two rare docs.

    - ranks 1-30: source "hub", scores 0.99 down to 0.70 (outside the band)
    - ranks 31-38: source "mid", score 0.5 (inside the default band)
    - ranks 39-40: sources "rare1"/"rare2", score 0.2 (one proposal each)
    """
    proposals: list[LinkProposal] = []
    for rank in range(1, 31):
        proposals.append(
            make_proposal(f"hub-{rank:02d}", rank, source="hub", score=0.99 - 0.01 * (rank - 1))
        )
    for rank in range(31, 39):
        proposals.append(make_proposal(f"mid-{rank:02d}", rank, source="mid", score=0.5))
    proposals.append(make_proposal("rare-1", 39, source="rare1", score=0.2))
    proposals.append(make_proposal("rare-2", 40, source="rare2", score=0.2))
    return ProposalSet(header=make_header(), proposals=tuple(proposals))


class TestBuildReviewQueue:
    def test_stratification_proportions(self) -> None:
        queue = build_review_queue(stratified_set(), size=10, seed=7)
        ids = [p.id for p in queue]

        assert len(queue) == 10
        assert len(set(ids)) == 10  # no duplicates
        # ~40% top-ranked: the 4 best global ranks are always present.
        assert {"hub-01", "hub-02", "hub-03", "hub-04"} <= set(ids)
        # ~20% near-threshold: at least 2 proposals inside [0.4, 0.6].
        assert sum(1 for p in queue if 0.4 <= p.score <= 0.6) >= 2
        # ~20% underrepresented sources: the single-proposal documents appear.
        assert {"rare-1", "rare-2"} <= set(ids)

    def test_deterministic_for_a_seed(self) -> None:
        first = build_review_queue(stratified_set(), size=10, seed=42)
        second = build_review_queue(stratified_set(), size=10, seed=42)
        assert first == second

    def test_returned_in_rank_order(self) -> None:
        queue = build_review_queue(stratified_set(), size=10, seed=3)
        assert [p.rank for p in queue] == sorted(p.rank for p in queue)

    def test_backfills_from_top_when_band_is_empty(self) -> None:
        proposals = ProposalSet(
            header=make_header(),
            proposals=tuple(
                make_proposal(f"p-{rank:02d}", rank, source=f"doc-{rank}", score=0.9)
                for rank in range(1, 21)
            ),
        )
        queue = build_review_queue(proposals, size=10, seed=1)
        assert len(queue) == 10

    def test_size_covering_everything_returns_all(self) -> None:
        proposals = stratified_set()
        queue = build_review_queue(proposals, size=100, seed=1)
        assert len(queue) == len(proposals.proposals)

    def test_non_positive_size_returns_empty(self) -> None:
        assert build_review_queue(stratified_set(), size=0, seed=1) == ()

    def test_custom_band(self) -> None:
        queue = build_review_queue(
            stratified_set(), size=10, seed=7, near_threshold_band=(0.15, 0.25)
        )
        assert {"rare-1", "rare-2"} <= {p.id for p in queue}
