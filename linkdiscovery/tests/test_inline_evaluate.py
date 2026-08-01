"""Hand-computed tests for the inline evaluation suite (SPEC §7, §8, §12)."""

from __future__ import annotations

import pytest

from linkdiscovery.contracts.base import ArtifactHeader
from linkdiscovery.contracts.units import Span
from linkdiscovery.errors import ContractError
from linkdiscovery.inline import (
    AuditItem,
    Benchmark,
    BenchmarkCase,
    BenchmarkKind,
    InlineProposal,
    InlineProposalSet,
    LinkRegionKind,
    SpanCandidate,
    SplitAssignment,
    bpref,
    judged_only_precision,
    kill_criterion,
    operating_point,
    retrieval_metrics,
    score_benchmark,
    span_detection_f1,
    three_way_split,
)
from linkdiscovery.inline.records import PRODUCER_VERSION, SCHEMA_VERSION


def make_header() -> ArtifactHeader:
    """A valid inline-subsystem artifact header."""
    return ArtifactHeader(
        schema_version=SCHEMA_VERSION,
        run_id="run-1",
        corpus_id="corpus-1",
        created_at="2026-07-31T00:00:00+00:00",
        config_fingerprint="sha256:test",
        producer_version=PRODUCER_VERSION,
    )


def make_candidate(
    candidate_id: str, document_id: str, start: int, end: int, text: str = "anchor"
) -> SpanCandidate:
    """A minimal span candidate at a fixed location."""
    return SpanCandidate(
        id=candidate_id,
        document_id=document_id,
        unit_id=None,
        span=Span(start, end),
        text=text,
        region_kind=LinkRegionKind.PROSE,
        word_count=1,
    )


def make_audit_item(
    item_id: str, document_id: str, span: Span | None, anchor: str = "anchor"
) -> AuditItem:
    """A minimal prose audit item with an optional source span."""
    return AuditItem(
        id=item_id,
        source_document_id=document_id,
        target_document_id="target",
        anchor_text=anchor,
        source_span=span,
        region_kind=LinkRegionKind.PROSE,
        context="... anchor ...",
        anchor_word_count=1,
        topic_family="general",
        strata_key="prose|short|general|note",
    )


def make_proposal(
    proposal_id: str, *, abstained: bool = False, target: str = "target"
) -> InlineProposal:
    """A minimal proposal whose identity is all the pooling metrics need."""
    return InlineProposal(
        id=proposal_id,
        source_document_id="src",
        span=Span(0, 6),
        anchor_text="anchor",
        target_document_id=target,
        target_section=None,
        naturalness=0.5,
        target_correctness=0.5,
        placement_validity=0.5,
        combined_score=0.5,
        abstained=abstained,
    )


def make_case(
    case_id: str,
    kind: BenchmarkKind,
    *,
    expected: bool = True,
    hard_case: bool = False,
) -> BenchmarkCase:
    """A minimal benchmark case of the given judgment kind."""
    return BenchmarkCase(
        id=case_id,
        kind=kind,
        source_document_id="src",
        span=Span(0, 6),
        anchor_text="anchor",
        target_document_id="target",
        expected=expected,
        hard_case=hard_case,
    )


class TestThreeWaySplit:
    def test_chained_identifiers_land_in_one_split_with_honest_fractions(self) -> None:
        # Adversarial chain: one anchor string links d1/d2, d2's target links
        # d3, and d3/d4 share another anchor -- indices 0-3 form ONE group.
        items = [
            ("d1", "Gradient Descent", "t1"),
            ("d2", "gradient   descent", "t2"),
            ("d3", "SGD", "t2"),
            ("d4", "sgd", "t9"),
            ("d5", "paxos", "t5"),
            ("d6", "raft", "t6"),
        ]
        result = three_way_split(items, seed=7, test_fraction=1 / 3, val_fraction=1 / 3)
        assert result.group_count == 3
        chain_splits = {result.assignments[index] for index in (0, 1, 2, 3)}
        assert len(chain_splits) == 1
        # The size-4 group fills its split alone: fractions deviate from the
        # requested 1/3 each and the deviation is reported, not hidden.
        counts = {split: len(result.indices_for(split)) for split in ("train", "val", "test")}
        assert sorted(counts.values()) == [1, 1, 4]
        assert result.achieved_fractions == {
            split: counts[split] / 6 for split in ("train", "val", "test")
        }

    def test_no_identifier_straddles_splits(self) -> None:
        items = [
            ("d1", "alpha", "t1"),
            ("d1", "beta", "t2"),
            ("d2", "alpha", "t3"),
            ("d3", "gamma", "t3"),
            ("d4", "delta", "t4"),
            ("d5", "epsilon", "t5"),
            ("d6", "zeta", "t6"),
        ]
        result = three_way_split(items, seed=13, test_fraction=0.3, val_fraction=0.2)
        splits_by_id: dict[str, set[str]] = {}
        for index, (document_id, anchor, target_id) in enumerate(items):
            split = result.assignments[index]
            normalized = " ".join(anchor.split()).casefold()
            for key in (f"doc:{document_id}", f"anchor:{normalized}", f"target:{target_id}"):
                splits_by_id.setdefault(key, set()).add(split)
        for key, splits in splits_by_id.items():
            assert len(splits) == 1, f"identifier {key} straddles splits {splits}"

    def test_independent_items_hit_requested_fractions_exactly(self) -> None:
        items = [(f"d{i}", f"anchor{i}", f"t{i}") for i in range(10)]
        result = three_way_split(items, seed=0, test_fraction=0.2, val_fraction=0.2)
        assert result.group_count == 10
        assert result.achieved_fractions == {"train": 0.6, "val": 0.2, "test": 0.2}

    def test_same_seed_is_deterministic(self) -> None:
        items = [(f"d{i}", f"anchor{i % 4}", f"t{i % 3}") for i in range(12)]
        first = three_way_split(items, seed=42, test_fraction=0.25, val_fraction=0.25)
        second = three_way_split(items, seed=42, test_fraction=0.25, val_fraction=0.25)
        assert first == second

    def test_empty_items_yield_empty_assignment(self) -> None:
        result = three_way_split([], seed=1, test_fraction=0.2, val_fraction=0.1)
        assert result.assignments == ()
        assert result.group_count == 0
        assert result.achieved_fractions == {"train": 0.0, "val": 0.0, "test": 0.0}

    @pytest.mark.parametrize(
        ("test_fraction", "val_fraction"),
        [(-0.1, 0.2), (0.2, 1.0), (0.6, 0.5), (0.5, 0.5)],
    )
    def test_invalid_fractions_raise(self, test_fraction: float, val_fraction: float) -> None:
        with pytest.raises(ValueError, match="fraction"):
            three_way_split(
                [("d1", "a", "t1")],
                seed=0,
                test_fraction=test_fraction,
                val_fraction=val_fraction,
            )


class TestSplitAssignment:
    def test_round_trip(self) -> None:
        assignment = SplitAssignment(
            ("train", "test", "val"),
            {"train": 1 / 3, "val": 1 / 3, "test": 1 / 3},
            3,
        )
        assert SplitAssignment.from_dict(assignment.to_dict()) == assignment

    def test_split_of_and_indices_for(self) -> None:
        assignment = SplitAssignment(("train", "test", "train"), {}, 3)
        assert assignment.split_of(1) == "test"
        assert assignment.indices_for("train") == (0, 2)
        assert assignment.indices_for("val") == ()

    def test_unknown_split_name_raises(self) -> None:
        with pytest.raises(ContractError, match="expected one of"):
            SplitAssignment(("train", "dev"), {}, 2)

    def test_negative_group_count_raises(self) -> None:
        with pytest.raises(ContractError, match="group_count"):
            SplitAssignment((), {}, -1)


class TestSpanDetectionF1:
    def test_exact_and_overlap_matching_on_crafted_spans(self) -> None:
        predicted = [
            make_candidate("c1", "a", 0, 10),
            make_candidate("c2", "a", 20, 30),
            make_candidate("c3", "b", 0, 5),
        ]
        gold = [
            make_audit_item("g1", "a", Span(0, 10)),  # exact match with c1
            make_audit_item("g2", "a", Span(21, 30)),  # Jaccard 9/10 with c2
            make_audit_item("g3", "b", Span(40, 50)),  # unmatched
        ]
        result = span_detection_f1(predicted, gold, overlap_threshold=0.8)
        assert result["precision_exact"] == pytest.approx(1 / 3)
        assert result["recall_exact"] == pytest.approx(1 / 3)
        assert result["f1_exact"] == pytest.approx(1 / 3)
        assert result["precision_overlap"] == pytest.approx(2 / 3)
        assert result["recall_overlap"] == pytest.approx(2 / 3)
        assert result["f1_overlap"] == pytest.approx(2 / 3)
        assert result["predicted_count"] == 3.0
        assert result["gold_count"] == 3.0

    def test_overlap_below_threshold_does_not_match(self) -> None:
        predicted = [make_candidate("c1", "a", 0, 10)]
        gold = [make_audit_item("g1", "a", Span(5, 15))]  # Jaccard 5/15 = 1/3
        result = span_detection_f1(predicted, gold, overlap_threshold=0.5)
        assert result["f1_overlap"] == 0.0

    def test_matching_is_one_to_one(self) -> None:
        # Two predictions overlap the single gold span; only one may match.
        predicted = [
            make_candidate("c1", "a", 0, 10),
            make_candidate("c2", "a", 1, 10),
        ]
        gold = [make_audit_item("g1", "a", Span(0, 10))]
        result = span_detection_f1(predicted, gold)
        assert result["precision_overlap"] == pytest.approx(0.5)
        assert result["recall_overlap"] == pytest.approx(1.0)

    def test_different_documents_never_match(self) -> None:
        predicted = [make_candidate("c1", "a", 0, 10)]
        gold = [make_audit_item("g1", "b", Span(0, 10))]
        result = span_detection_f1(predicted, gold)
        assert result["f1_exact"] == 0.0
        assert result["f1_overlap"] == 0.0

    def test_gold_without_span_is_excluded(self) -> None:
        predicted = [make_candidate("c1", "a", 0, 10)]
        gold = [
            make_audit_item("g1", "a", Span(0, 10)),
            make_audit_item("g2", "a", None),
        ]
        result = span_detection_f1(predicted, gold)
        assert result["gold_count"] == 1.0
        assert result["recall_exact"] == pytest.approx(1.0)

    def test_empty_inputs_yield_zeros(self) -> None:
        result = span_detection_f1([], [])
        assert result["f1_exact"] == 0.0
        assert result["f1_overlap"] == 0.0
        assert result["predicted_count"] == 0.0

    def test_invalid_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="overlap_threshold"):
            span_detection_f1([], [], overlap_threshold=0.0)


class TestRetrievalMetrics:
    def test_exact_hand_computed_values(self) -> None:
        ranked = [
            ["t1", "t2", "t3"],  # gold at rank 1
            ["x", "gold2", "y"],  # gold at rank 2
            ["a", "b"],  # gold absent
        ]
        gold = ["t1", "gold2", "missing"]
        result = retrieval_metrics(ranked, gold, k_values=(1, 3))
        assert result["recall_at_1"] == pytest.approx(1 / 3)
        assert result["recall_at_3"] == pytest.approx(2 / 3)
        assert result["mrr"] == pytest.approx((1.0 + 0.5 + 0.0) / 3)
        assert result["query_count"] == 3.0

    def test_empty_inputs_yield_zeros(self) -> None:
        result = retrieval_metrics([], [])
        assert result["mrr"] == 0.0
        assert result["recall_at_1"] == 0.0
        assert result["query_count"] == 0.0

    def test_misaligned_inputs_raise(self) -> None:
        with pytest.raises(ValueError, match="align"):
            retrieval_metrics([["t1"]], ["t1", "t2"])


class TestJudgedOnlyPrecision:
    def test_unjudged_proposals_are_never_scored_wrong(self) -> None:
        proposals = InlineProposalSet(
            header=make_header(),
            proposals=tuple(make_proposal(f"p{i}") for i in range(1, 6)),
        )
        judgments = {"p1": True, "p3": False, "p5": True}
        result = judged_only_precision(proposals, judgments, k_values=(1, 2, 5))
        # k=1: [p1] judged relevant.
        assert result["precision_at_1"] == pytest.approx(1.0)
        assert result["judged_fraction_at_1"] == pytest.approx(1.0)
        # k=2: p2 unjudged -- excluded from precision, visible in the residual.
        assert result["precision_at_2"] == pytest.approx(1.0)
        assert result["judged_fraction_at_2"] == pytest.approx(0.5)
        # k=5: judged pool is [True, False, True].
        assert result["precision_at_5"] == pytest.approx(2 / 3)
        assert result["judged_fraction_at_5"] == pytest.approx(3 / 5)

    def test_abstained_proposals_are_excluded_from_the_ranking(self) -> None:
        proposals = InlineProposalSet(
            header=make_header(),
            proposals=(
                make_proposal("p1"),
                make_proposal("p2", abstained=True),
                make_proposal("p3"),
            ),
        )
        result = judged_only_precision(proposals, {"p1": True, "p3": False}, k_values=(2,))
        assert result["precision_at_2"] == pytest.approx(0.5)
        assert result["judged_fraction_at_2"] == pytest.approx(1.0)

    def test_empty_proposals_yield_zeros(self) -> None:
        proposals = InlineProposalSet(header=make_header())
        result = judged_only_precision(proposals, {}, k_values=(1,))
        assert result["precision_at_1"] == 0.0
        assert result["judged_fraction_at_1"] == 0.0


class TestBpref:
    def make_set(self, pattern: list[str]) -> tuple[InlineProposalSet, dict[str, bool]]:
        """Build a ranked set from 'R'/'N'/'U' (relevant/nonrelevant/unjudged)."""
        proposals = tuple(make_proposal(f"p{i}") for i in range(len(pattern)))
        judgments = {f"p{i}": mark == "R" for i, mark in enumerate(pattern) if mark in ("R", "N")}
        return InlineProposalSet(header=make_header(), proposals=proposals), judgments

    def test_canonical_small_example(self) -> None:
        # Ranking R N R N R: R=3, N=2, min(R,N)=2.
        # Terms: 1 - 0/2, 1 - 1/2, 1 - 2/2 -> (1 + 0.5 + 0) / 3 = 0.5.
        proposals, judgments = self.make_set(["R", "N", "R", "N", "R"])
        assert bpref(proposals, judgments) == pytest.approx(0.5)

    def test_unjudged_proposals_are_skipped(self) -> None:
        proposals, judgments = self.make_set(["R", "U", "N", "U", "R", "N", "R"])
        assert bpref(proposals, judgments) == pytest.approx(0.5)

    def test_perfect_ranking_scores_one(self) -> None:
        proposals, judgments = self.make_set(["R", "R", "N", "N"])
        assert bpref(proposals, judgments) == pytest.approx(1.0)

    def test_no_judged_nonrelevant_scores_one(self) -> None:
        proposals, judgments = self.make_set(["R", "U", "R"])
        assert bpref(proposals, judgments) == pytest.approx(1.0)

    def test_no_judged_relevant_scores_zero(self) -> None:
        proposals, judgments = self.make_set(["N", "U", "N"])
        assert bpref(proposals, judgments) == 0.0

    def test_all_relevant_below_the_nonrelevant_scores_zero(self) -> None:
        # N R R: R=2, N=1, min(R,N)=1; both terms 1 - min(1,2)/1 = 0.
        proposals, judgments = self.make_set(["N", "R", "R"])
        assert bpref(proposals, judgments) == pytest.approx(0.0)


class TestScoreBenchmark:
    def test_per_kind_overall_and_hard_case_with_missing_outcomes(self) -> None:
        benchmark = Benchmark(
            header=make_header(),
            cases=(
                make_case("c1", BenchmarkKind.NATURAL_SPAN, expected=True),
                make_case("c2", BenchmarkKind.NATURAL_SPAN, expected=True),
                make_case("c3", BenchmarkKind.NO_LINK, expected=True, hard_case=True),
            ),
        )
        outcomes = {"c1": True, "c3": False}  # c2 unevaluated; c3 incorrect
        result = score_benchmark(benchmark, outcomes)
        assert result["natural_span"] == {
            "accuracy": 1.0,
            "evaluated": 1.0,
            "unevaluated": 1.0,
            "total": 2.0,
        }
        assert result["no_link"]["accuracy"] == 0.0
        assert result["overall"] == {
            "accuracy": 0.5,
            "evaluated": 2.0,
            "unevaluated": 1.0,
            "total": 3.0,
        }
        assert result["hard_case"] == {
            "accuracy": 0.0,
            "evaluated": 1.0,
            "unevaluated": 0.0,
            "total": 1.0,
        }

    def test_all_seven_kinds_are_always_reported(self) -> None:
        result = score_benchmark(Benchmark(header=make_header()), {})
        expected_keys = {kind.value for kind in BenchmarkKind} | {"overall", "hard_case"}
        assert set(result) == expected_keys
        assert result["correct_target"] == {
            "accuracy": 0.0,
            "evaluated": 0.0,
            "unevaluated": 0.0,
            "total": 0.0,
        }

    def test_expected_false_case_is_correct_when_outcome_false(self) -> None:
        benchmark = Benchmark(
            header=make_header(),
            cases=(make_case("c1", BenchmarkKind.INCORRECT_TARGET, expected=False),),
        )
        assert score_benchmark(benchmark, {"c1": False})["overall"]["accuracy"] == 1.0


class TestOperatingPoint:
    SWEEP = (
        {"precision": 0.90, "recall": 0.20, "threshold": 0.8},
        {"precision": 0.76, "recall": 0.45, "threshold": 0.5},
        {"precision": 0.70, "recall": 0.60, "threshold": 0.3},
    )

    def test_picks_highest_recall_row_meeting_the_bar(self) -> None:
        result = operating_point(self.SWEEP, min_precision=0.75)
        assert result == {"precision": 0.76, "recall": 0.45, "threshold": 0.5}

    def test_lower_bar_admits_the_higher_recall_row(self) -> None:
        result = operating_point(self.SWEEP, min_precision=0.70)
        assert result is not None
        assert result["recall"] == 0.60

    def test_recall_ties_break_by_precision(self) -> None:
        sweep = (
            {"precision": 0.80, "recall": 0.40},
            {"precision": 0.85, "recall": 0.40},
        )
        result = operating_point(sweep, min_precision=0.75)
        assert result is not None
        assert result["precision"] == 0.85

    def test_unreachable_bar_returns_none(self) -> None:
        assert operating_point(self.SWEEP, min_precision=0.95) is None
        assert operating_point((), min_precision=0.5) is None

    def test_missing_keys_raise(self) -> None:
        with pytest.raises(ValueError, match="precision"):
            operating_point(({"recall": 0.4},))


class TestKillCriterion:
    def test_meeting_both_floors_survives(self) -> None:
        assert kill_criterion(0.75, 0.40) is False
        assert kill_criterion(0.70, 0.20) is False  # floors are inclusive

    def test_precision_below_070_kills(self) -> None:
        assert kill_criterion(0.69, 0.40) is True

    def test_recall_below_020_kills(self) -> None:
        assert kill_criterion(0.90, 0.19) is True
