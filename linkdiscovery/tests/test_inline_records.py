"""Round-trip and validation tests for the inline-link subsystem records."""

from __future__ import annotations

from typing import Any

import pytest

from linkdiscovery.contracts import ReviewState, Span
from linkdiscovery.errors import ContractError
from linkdiscovery.inline import (
    AuditItem,
    AuditLabel,
    AuditReport,
    AuditSample,
    Benchmark,
    BenchmarkCase,
    BenchmarkKind,
    InlineProposal,
    InlineProposalSet,
    LinkRegionKind,
    SpanCandidate,
    Tier,
)
from linkdiscovery.inline.records import (
    REVIEW_ENGINES,
    REVIEW_REASONS,
    REVIEW_VERDICTS,
    InlineReviewDecision,
)
from tests.conftest import make_header


def make_audit_item(item_id: str = "item-1") -> AuditItem:
    """A fully populated audit item."""
    return AuditItem(
        id=item_id,
        source_document_id="systems/scheduling",
        target_document_id="systems/fair-queueing",
        anchor_text="fair queueing",
        source_span=Span(start=120, end=133),
        region_kind=LinkRegionKind.PROSE,
        context="...schedulers often rely on fair queueing to bound latency...",
        anchor_word_count=2,
        topic_family="systems",
        strata_key="prose|2-3|systems|note",
    )


def make_audit_label(
    item_id: str = "item-1",
    annotator: str = "alice",
    *,
    target_correct: bool = True,
    anchor_natural: bool = True,
    placement_valid: bool = True,
    tier: Tier = Tier.A,
) -> AuditLabel:
    """A fully populated audit label."""
    return AuditLabel(
        item_id=item_id,
        annotator=annotator,
        target_correct=target_correct,
        anchor_natural=anchor_natural,
        placement_valid=placement_valid,
        tier=tier,
        note="clean anchor",
        labeled_at="2026-07-31T12:00:00+00:00",
    )


def make_audit_sample() -> AuditSample:
    """An audit sample with two items and strata counts."""
    return AuditSample(
        header=make_header(),
        items=(make_audit_item("item-1"), make_audit_item("item-2")),
        strata_counts={"prose|2-3|systems|note": 2},
    )


def make_audit_report() -> AuditReport:
    """An audit report with agreement values and notes."""
    return AuditReport(
        header=make_header(),
        n_items=150,
        n_labeled=148,
        tier_counts={"a": 90, "b": 30, "c": 20, "d": 8},
        agreement={"kappa_anchor_natural": 0.72, "alpha_tier": 0.68},
        go=False,
        notes=("2 of 150 items unlabeled",),
    )


def make_span_candidate() -> SpanCandidate:
    """A fully populated span candidate."""
    return SpanCandidate(
        id="cand-1",
        document_id="systems/scheduling",
        unit_id="systems/scheduling:section-1:chunk-0",
        span=Span(start=40, end=49),
        text="MapReduce",
        region_kind=LinkRegionKind.PROSE,
        word_count=1,
        features={"keyphraseness": 0.12, "title_case": 1.0},
    )


def make_inline_proposal(proposal_id: str = "prop-1") -> InlineProposal:
    """A fully populated inline proposal."""
    return InlineProposal(
        id=proposal_id,
        source_document_id="systems/scheduling",
        span=Span(start=40, end=49),
        anchor_text="MapReduce",
        target_document_id="distributed/mapreduce",
        target_section="Execution model",
        naturalness=0.91,
        target_correctness=0.88,
        placement_validity=0.95,
        combined_score=0.9,
        calibrated_probability=0.83,
        abstained=False,
        features={"keyphraseness": 0.12, "retrieval_rank": 1.0},
        model_version="inline-v1",
        review=ReviewState(status="unreviewed", reason=None),
    )


def make_review_decision() -> InlineReviewDecision:
    """A fully populated review decision."""
    return InlineReviewDecision(
        engine="learned",
        source_document_id="systems/scheduling",
        span=Span(start=40, end=49),
        anchor_text="MapReduce",
        target_document_id="distributed/mapreduce",
        verdict="accept",
        target_ok=True,
        anchor_ok=True,
        placement_ok=True,
        reason="good",
        note="clean pairing",
        combined_score=0.71,
    )


def review_wire_dict() -> dict[str, Any]:
    """One ``decisions.jsonl`` line: the wire format including ignored keys."""
    return {
        "engine": "learned",
        "id": "sha256:4ab1a9dd1c95f",  # informational, ignored
        "source": "systems/scheduling",
        "target": "distributed/mapreduce",
        "anchor": "MapReduce",
        "start": 40,
        "end": 49,
        "score": 0.71,
        "flag": False,  # informational, ignored
        "rank": 12,  # informational, ignored
        "verdict": "accept",
        "target_ok": True,
        "anchor_ok": True,
        "placement_ok": True,
        "reason": "good",
        "note": "clean pairing",
    }


def make_benchmark_case(case_id: str = "case-1") -> BenchmarkCase:
    """A fully populated benchmark case."""
    return BenchmarkCase(
        id=case_id,
        kind=BenchmarkKind.NO_LINK,
        source_document_id="systems/scheduling",
        span=Span(start=10, end=16),
        anchor_text="system",
        target_document_id=None,
        expected=True,
        hard_case=True,
        note="generic anchor must not link",
    )


class TestEnums:
    def test_tier_values(self) -> None:
        assert [tier.value for tier in Tier] == ["a", "b", "c", "d"]
        assert Tier("c") is Tier.C

    def test_link_region_kind_values(self) -> None:
        assert LinkRegionKind.RELATED_NOTES == "related_notes"
        assert LinkRegionKind("prose") is LinkRegionKind.PROSE

    def test_benchmark_kind_covers_seven_judgments(self) -> None:
        assert len(BenchmarkKind) == 7
        assert BenchmarkKind("reverse_direction") is BenchmarkKind.REVERSE_DIRECTION


class TestRoundTrips:
    @pytest.mark.parametrize(
        "record",
        [
            make_audit_item(),
            make_audit_label(),
            make_audit_sample(),
            make_audit_report(),
            make_span_candidate(),
            make_inline_proposal(),
            InlineProposalSet(
                header=make_header(),
                proposals=(make_inline_proposal("p1"), make_inline_proposal("p2")),
            ),
            make_benchmark_case(),
            Benchmark(
                header=make_header(),
                cases=(make_benchmark_case("c1"), make_benchmark_case("c2")),
            ),
            make_review_decision(),
        ],
        ids=lambda record: type(record).__name__,
    )
    def test_to_dict_from_dict_round_trip(self, record: Any) -> None:
        assert type(record).from_dict(record.to_dict()) == record

    def test_nullable_fields_round_trip_as_none(self) -> None:
        item = AuditItem(
            id="i",
            source_document_id="a",
            target_document_id="b",
            anchor_text="x",
            source_span=None,
            region_kind=LinkRegionKind.OTHER,
            context="",
            anchor_word_count=1,
            topic_family="a",
            strata_key="other|1|a|note",
        )
        data = item.to_dict()
        assert data["source_span"] is None
        assert AuditItem.from_dict(data) == item

    def test_label_defaults_apply_when_fields_absent(self) -> None:
        data = make_audit_label().to_dict()
        del data["note"]
        del data["labeled_at"]
        label = AuditLabel.from_dict(data)
        assert label.note == ""
        assert label.labeled_at == ""

    def test_proposal_calibrated_probability_none_round_trips(self) -> None:
        data = make_inline_proposal().to_dict()
        data["calibrated_probability"] = None
        assert InlineProposal.from_dict(data).calibrated_probability is None


class TestValidation:
    def test_missing_required_field_raises(self) -> None:
        data = make_audit_item().to_dict()
        del data["strata_key"]
        with pytest.raises(ContractError, match="missing required field 'strata_key'"):
            AuditItem.from_dict(data)

    def test_wrong_type_raises_with_field_name(self) -> None:
        data = make_audit_label().to_dict()
        data["target_correct"] = "yes"
        with pytest.raises(ContractError, match="'target_correct' must be a boolean"):
            AuditLabel.from_dict(data)

    def test_unknown_tier_rejected(self) -> None:
        data = make_audit_label().to_dict()
        data["tier"] = "e"
        with pytest.raises(ContractError, match="unknown tier 'e'"):
            AuditLabel.from_dict(data)

    def test_unknown_region_kind_rejected(self) -> None:
        data = make_span_candidate().to_dict()
        data["region_kind"] = "sidebar"
        with pytest.raises(ContractError, match="unknown region_kind 'sidebar'"):
            SpanCandidate.from_dict(data)

    def test_unknown_benchmark_kind_rejected(self) -> None:
        data = make_benchmark_case().to_dict()
        data["kind"] = "vibes"
        with pytest.raises(ContractError, match="unknown kind 'vibes'"):
            BenchmarkCase.from_dict(data)

    def test_negative_anchor_word_count_rejected(self) -> None:
        with pytest.raises(ContractError, match="anchor_word_count must be >= 0"):
            AuditItem(
                id="i",
                source_document_id="a",
                target_document_id="b",
                anchor_text="x",
                source_span=None,
                region_kind=LinkRegionKind.PROSE,
                context="",
                anchor_word_count=-1,
                topic_family="a",
                strata_key="k",
            )

    def test_negative_word_count_rejected(self) -> None:
        with pytest.raises(ContractError, match="word_count must be >= 0"):
            SpanCandidate(
                id="c",
                document_id="d",
                unit_id=None,
                span=Span(start=0, end=1),
                text="x",
                region_kind=LinkRegionKind.PROSE,
                word_count=-2,
            )

    def test_negative_report_counts_rejected(self) -> None:
        with pytest.raises(ContractError, match="must be >= 0"):
            AuditReport(header=make_header(), n_items=-1, n_labeled=0)

    def test_duplicate_audit_item_ids_rejected(self) -> None:
        with pytest.raises(ContractError, match="duplicate item id 'item-1'"):
            AuditSample(
                header=make_header(),
                items=(make_audit_item("item-1"), make_audit_item("item-1")),
            )

    def test_duplicate_proposal_ids_rejected(self) -> None:
        with pytest.raises(ContractError, match="duplicate proposal id 'p1'"):
            InlineProposalSet(
                header=make_header(),
                proposals=(make_inline_proposal("p1"), make_inline_proposal("p1")),
            )

    def test_duplicate_benchmark_case_ids_rejected(self) -> None:
        with pytest.raises(ContractError, match="duplicate case id 'c1'"):
            Benchmark(
                header=make_header(),
                cases=(make_benchmark_case("c1"), make_benchmark_case("c1")),
            )

    @pytest.mark.parametrize(
        "artifact",
        [
            make_audit_sample(),
            make_audit_report(),
            InlineProposalSet(header=make_header(), proposals=(make_inline_proposal(),)),
            Benchmark(header=make_header(), cases=(make_benchmark_case(),)),
        ],
        ids=lambda artifact: type(artifact).__name__,
    )
    def test_unknown_schema_version_rejected(self, artifact: Any) -> None:
        data = artifact.to_dict()
        data["header"]["schema_version"] = 99
        with pytest.raises(ContractError, match="unknown schema_version 99"):
            type(artifact).from_dict(data)


class TestReviewDecision:
    """The decisions.jsonl wire format and its closed domains."""

    def test_domains_cover_the_review_taxonomy(self) -> None:
        assert {"baseline", "learned"} == REVIEW_ENGINES
        assert {"accept", "reject"} == REVIEW_VERDICTS
        assert len(REVIEW_REASONS) == 8
        assert "broken_span" in REVIEW_REASONS

    def test_from_dict_maps_the_wire_format(self) -> None:
        decision = InlineReviewDecision.from_dict(review_wire_dict())
        assert decision.engine == "learned"
        assert decision.source_document_id == "systems/scheduling"
        assert decision.target_document_id == "distributed/mapreduce"
        assert decision.anchor_text == "MapReduce"
        assert decision.span == Span(start=40, end=49)
        assert decision.combined_score == pytest.approx(0.71)
        assert decision.verdict == "accept"
        assert decision.target_ok and decision.anchor_ok and decision.placement_ok
        assert decision.reason == "good"
        assert decision.note == "clean pairing"

    def test_informational_wire_keys_are_ignored_and_not_reemitted(self) -> None:
        decision = InlineReviewDecision.from_dict(review_wire_dict())
        emitted = decision.to_dict()
        assert set(emitted).isdisjoint({"id", "flag", "rank"})
        assert InlineReviewDecision.from_dict(emitted) == decision

    def test_note_defaults_to_empty_when_absent(self) -> None:
        data = review_wire_dict()
        del data["note"]
        assert InlineReviewDecision.from_dict(data).note == ""

    def test_missing_required_wire_field_raises(self) -> None:
        data = review_wire_dict()
        del data["source"]
        with pytest.raises(ContractError, match="missing required field 'source'"):
            InlineReviewDecision.from_dict(data)

    def test_wrong_type_raises_with_field_name(self) -> None:
        data = review_wire_dict()
        data["target_ok"] = "yes"
        with pytest.raises(ContractError, match="'target_ok' must be a boolean"):
            InlineReviewDecision.from_dict(data)

    @pytest.mark.parametrize(
        ("field", "value"),
        [("engine", "quantum"), ("verdict", "maybe"), ("reason", "vibes")],
    )
    def test_out_of_domain_values_rejected(self, field: str, value: str) -> None:
        data = review_wire_dict()
        data[field] = value
        with pytest.raises(ContractError, match=f"unknown {field} {value!r}"):
            InlineReviewDecision.from_dict(data)

    def test_direct_construction_is_validated_too(self) -> None:
        with pytest.raises(ContractError, match="unknown reason 'vibes'"):
            InlineReviewDecision(
                engine="baseline",
                source_document_id="a",
                span=Span(start=0, end=1),
                anchor_text="x",
                target_document_id="b",
                verdict="reject",
                target_ok=False,
                anchor_ok=False,
                placement_ok=False,
                reason="vibes",
                note="",
                combined_score=0.5,
            )

    def test_invalid_span_range_rejected(self) -> None:
        data = review_wire_dict()
        data["start"], data["end"] = 49, 40
        with pytest.raises(ContractError, match="invalid range"):
            InlineReviewDecision.from_dict(data)
