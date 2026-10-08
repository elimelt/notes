"""Unit tests for the frozen-benchmark runner's per-kind outcome semantics.

Every test drives :func:`~linkdiscovery.inline.benchmark.run_benchmark` over
hand-built drafts and selections, flipping exactly the ingredient each
benchmark kind depends on (an overlapping draft's head score, an accepted
versus abstained post-selection proposal, the located span). Nothing here
touches the real frozen artifact.
"""

from __future__ import annotations

from linkdiscovery.contracts import SourceDocument, Span
from linkdiscovery.inline.benchmark import (
    NATURAL_SPAN_NATURALNESS,
    locate_case_span,
    run_benchmark,
)
from linkdiscovery.inline.records import (
    Benchmark,
    BenchmarkCase,
    BenchmarkKind,
    InlineProposal,
    InlineProposalSet,
)
from linkdiscovery.inline.select import Q25_TARGET_CORRECTNESS
from tests.conftest import make_header

CONTENT = "Dynamo trades consistency for availability. Vector clocks order writes.\n"
ANCHOR = "consistency"
ANCHOR_START = CONTENT.index(ANCHOR)
ANCHOR_SPAN = Span(start=ANCHOR_START, end=ANCHOR_START + len(ANCHOR))

DOCUMENTS = {
    "doc": SourceDocument(id="doc", revision="r1", media_type="text/markdown", content=CONTENT)
}


def make_case(
    kind: BenchmarkKind,
    *,
    case_id: str = "case-1",
    source: str = "doc",
    anchor: str = ANCHOR,
    span: Span | None = None,
    target: str | None = "target",
    expected: bool = True,
) -> BenchmarkCase:
    return BenchmarkCase(
        id=case_id,
        kind=kind,
        source_document_id=source,
        span=span,
        anchor_text=anchor,
        target_document_id=target,
        expected=expected,
    )


def make_proposal(
    proposal_id: str,
    *,
    source: str = "doc",
    span: Span = ANCHOR_SPAN,
    target: str = "target",
    naturalness: float = 0.9,
    target_correctness: float = 0.9,
    combined: float = 0.8,
    abstained: bool = False,
) -> InlineProposal:
    return InlineProposal(
        id=proposal_id,
        source_document_id=source,
        span=span,
        anchor_text=CONTENT[span.start : span.end],
        target_document_id=target,
        target_section=None,
        naturalness=naturalness,
        target_correctness=target_correctness,
        placement_validity=0.9,
        combined_score=combined,
        abstained=abstained,
    )


def run_one(
    case: BenchmarkCase,
    *,
    drafts: list[InlineProposal] = [],  # noqa: B006 -- never mutated
    selected: list[InlineProposal] = [],  # noqa: B006 -- never mutated
) -> dict[str, bool]:
    benchmark = Benchmark(header=make_header(), cases=(case,))
    proposal_set = InlineProposalSet(header=make_header(), proposals=tuple(selected))
    return run_benchmark(benchmark, drafts=drafts, selected=proposal_set, documents=DOCUMENTS)


class TestLocateCaseSpan:
    def test_explicit_span_wins_over_anchor_text(self) -> None:
        explicit = Span(start=0, end=6)
        case = make_case(BenchmarkKind.NATURAL_SPAN, span=explicit)
        assert locate_case_span(case, DOCUMENTS["doc"]) == explicit

    def test_anchor_text_locates_the_first_verbatim_occurrence(self) -> None:
        case = make_case(BenchmarkKind.NATURAL_SPAN)
        assert locate_case_span(case, DOCUMENTS["doc"]) == ANCHOR_SPAN

    def test_missing_anchor_text_is_unlocatable(self) -> None:
        case = make_case(BenchmarkKind.NATURAL_SPAN, anchor="quorum intersection")
        assert locate_case_span(case, DOCUMENTS["doc"]) is None

    def test_empty_anchor_text_is_unlocatable(self) -> None:
        case = make_case(BenchmarkKind.NATURAL_SPAN, anchor="")
        assert locate_case_span(case, DOCUMENTS["doc"]) is None


class TestOmission:
    def test_missing_source_document_is_omitted(self) -> None:
        case = make_case(BenchmarkKind.NATURAL_SPAN, source="ghost")
        assert run_one(case) == {}

    def test_unlocatable_span_is_omitted(self) -> None:
        case = make_case(BenchmarkKind.NATURAL_SPAN, anchor="quorum intersection")
        assert run_one(case) == {}

    def test_outcomes_follow_benchmark_case_order(self) -> None:
        benchmark = Benchmark(
            header=make_header(),
            cases=(
                make_case(BenchmarkKind.NO_LINK, case_id="c-b", target=None),
                make_case(BenchmarkKind.NATURAL_SPAN, case_id="c-a", target=None),
            ),
        )
        outcomes = run_benchmark(
            benchmark,
            drafts=[],
            selected=InlineProposalSet(header=make_header()),
            documents=DOCUMENTS,
        )
        assert list(outcomes) == ["c-b", "c-a"]


class TestNaturalSpan:
    def test_overlapping_draft_at_the_floor_passes(self) -> None:
        case = make_case(BenchmarkKind.NATURAL_SPAN, target=None)
        drafts = [make_proposal("d1", naturalness=NATURAL_SPAN_NATURALNESS)]
        assert run_one(case, drafts=drafts) == {"case-1": True}

    def test_low_naturalness_or_no_overlap_fails(self) -> None:
        case = make_case(BenchmarkKind.NATURAL_SPAN, target=None)
        low = [make_proposal("d1", naturalness=0.4)]
        elsewhere = [make_proposal("d1", span=Span(start=0, end=6), naturalness=0.9)]
        assert run_one(case, drafts=low) == {"case-1": False}
        assert run_one(case, drafts=elsewhere) == {"case-1": False}

    def test_selection_cannot_hide_a_draft_level_judgment(self) -> None:
        # natural_span consults DRAFTS: an empty accepted set changes nothing.
        case = make_case(BenchmarkKind.NATURAL_SPAN, target=None)
        drafts = [make_proposal("d1", naturalness=0.9)]
        assert run_one(case, drafts=drafts, selected=[]) == {"case-1": True}

    def test_touching_spans_do_not_overlap(self) -> None:
        case = make_case(BenchmarkKind.NATURAL_SPAN, target=None)
        touching = [make_proposal("d1", span=Span(start=ANCHOR_SPAN.end, end=ANCHOR_SPAN.end + 3))]
        assert run_one(case, drafts=touching) == {"case-1": False}


class TestAcceptableSpan:
    def test_right_target_at_q25_level_passes(self) -> None:
        case = make_case(BenchmarkKind.ACCEPTABLE_SPAN)
        drafts = [make_proposal("d1", target_correctness=Q25_TARGET_CORRECTNESS)]
        assert run_one(case, drafts=drafts) == {"case-1": True}

    def test_below_q25_or_wrong_target_fails(self) -> None:
        case = make_case(BenchmarkKind.ACCEPTABLE_SPAN)
        weak = [make_proposal("d1", target_correctness=Q25_TARGET_CORRECTNESS - 0.01)]
        wrong = [make_proposal("d1", target="other", target_correctness=0.99)]
        assert run_one(case, drafts=weak) == {"case-1": False}
        assert run_one(case, drafts=wrong) == {"case-1": False}


class TestCorrectTarget:
    def test_best_overlapping_draft_decides(self) -> None:
        case = make_case(BenchmarkKind.CORRECT_TARGET)
        winning = [
            make_proposal("d1", target="target", combined=0.9),
            make_proposal("d2", target="other", combined=0.5),
        ]
        losing = [
            make_proposal("d1", target="target", combined=0.5),
            make_proposal("d2", target="other", combined=0.9),
        ]
        assert run_one(case, drafts=winning) == {"case-1": True}
        assert run_one(case, drafts=losing) == {"case-1": False}

    def test_no_overlapping_draft_fails(self) -> None:
        case = make_case(BenchmarkKind.CORRECT_TARGET)
        assert run_one(case, drafts=[]) == {"case-1": False}

    def test_combined_score_tie_breaks_by_proposal_id(self) -> None:
        case = make_case(BenchmarkKind.CORRECT_TARGET)
        drafts = [
            make_proposal("d2", target="other", combined=0.9),
            make_proposal("d1", target="target", combined=0.9),
        ]
        assert run_one(case, drafts=drafts) == {"case-1": True}


class TestIncorrectTarget:
    def test_confidently_linking_the_wrong_pairing_fails(self) -> None:
        # The case's target is the known-WRONG pairing; accepting it means
        # the system failed to judge it wrong.
        case = make_case(BenchmarkKind.INCORRECT_TARGET)
        accepted = [make_proposal("p1", target="target")]
        assert run_one(case, selected=accepted) == {"case-1": False}

    def test_abstaining_or_linking_elsewhere_passes(self) -> None:
        case = make_case(BenchmarkKind.INCORRECT_TARGET)
        abstained = [make_proposal("p1", target="target", abstained=True)]
        elsewhere = [make_proposal("p1", target="other")]
        assert run_one(case, selected=abstained) == {"case-1": True}
        assert run_one(case, selected=elsewhere) == {"case-1": True}


class TestNoLink:
    def test_any_accepted_overlap_fails(self) -> None:
        case = make_case(BenchmarkKind.NO_LINK, target=None)
        assert run_one(case, selected=[make_proposal("p1")]) == {"case-1": False}

    def test_abstentions_and_empty_selection_pass(self) -> None:
        case = make_case(BenchmarkKind.NO_LINK, target=None)
        abstained = [make_proposal("p1", abstained=True)]
        assert run_one(case, selected=abstained) == {"case-1": True}
        assert run_one(case, selected=[]) == {"case-1": True}


class TestValidPlacement:
    def test_accepted_overlap_matching_the_target_passes(self) -> None:
        case = make_case(BenchmarkKind.VALID_PLACEMENT)
        assert run_one(case, selected=[make_proposal("p1")]) == {"case-1": True}

    def test_target_mismatch_fails_when_the_case_records_one(self) -> None:
        case = make_case(BenchmarkKind.VALID_PLACEMENT)
        wrong = [make_proposal("p1", target="other")]
        assert run_one(case, selected=wrong) == {"case-1": False}

    def test_any_accepted_overlap_passes_without_a_recorded_target(self) -> None:
        case = make_case(BenchmarkKind.VALID_PLACEMENT, target=None)
        any_target = [make_proposal("p1", target="other")]
        assert run_one(case, selected=any_target) == {"case-1": True}
        assert run_one(case, selected=[]) == {"case-1": False}


class TestReverseDirection:
    def test_accepted_overlap_with_the_target_passes(self) -> None:
        case = make_case(BenchmarkKind.REVERSE_DIRECTION)
        assert run_one(case, selected=[make_proposal("p1")]) == {"case-1": True}

    def test_wrong_target_or_abstention_fails(self) -> None:
        case = make_case(BenchmarkKind.REVERSE_DIRECTION)
        wrong = [make_proposal("p1", target="other")]
        abstained = [make_proposal("p1", abstained=True)]
        assert run_one(case, selected=wrong) == {"case-1": False}
        assert run_one(case, selected=abstained) == {"case-1": False}
