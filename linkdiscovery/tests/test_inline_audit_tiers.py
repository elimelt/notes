"""Tier derivation rules and the audit go/no-go report."""

from __future__ import annotations

import pytest

from linkdiscovery.inline import (
    AuditItem,
    AuditLabel,
    AuditSample,
    LinkRegionKind,
    Tier,
    build_audit_report,
    derive_tier,
)
from tests.conftest import make_header


def make_item(item_id: str, region_kind: LinkRegionKind = LinkRegionKind.PROSE) -> AuditItem:
    """A minimal audit item in the given region."""
    return AuditItem(
        id=item_id,
        source_document_id="systems/a",
        target_document_id="systems/b",
        anchor_text="anchor",
        source_span=None,
        region_kind=region_kind,
        context="",
        anchor_word_count=1,
        topic_family="systems",
        strata_key=f"{region_kind.value}|1|systems|note",
    )


def make_label(
    item_id: str,
    annotator: str,
    *,
    target_correct: bool = True,
    anchor_natural: bool = True,
    placement_valid: bool = True,
    tier: Tier = Tier.A,
) -> AuditLabel:
    """A label with controllable judgments."""
    return AuditLabel(
        item_id=item_id,
        annotator=annotator,
        target_correct=target_correct,
        anchor_natural=anchor_natural,
        placement_valid=placement_valid,
        tier=tier,
        labeled_at="2026-07-31T12:00:00+00:00",
    )


class TestDeriveTier:
    @pytest.mark.parametrize(
        ("target_correct", "anchor_natural", "placement_valid", "region_kind", "expected"),
        [
            # Prose, all judgments positive -> strong positive for all heads.
            (True, True, True, LinkRegionKind.PROSE, Tier.A),
            # Prose, target correct but anchor or placement flawed -> weak positive.
            (True, False, True, LinkRegionKind.PROSE, Tier.B),
            (True, True, False, LinkRegionKind.PROSE, Tier.B),
            (True, False, False, LinkRegionKind.PROSE, Tier.B),
            # Graph-only regions cap at Tier C even when everything is positive.
            (True, True, True, LinkRegionKind.RELATED_NOTES, Tier.C),
            (True, True, True, LinkRegionKind.HEADING, Tier.C),
            (True, True, True, LinkRegionKind.TABLE, Tier.C),
            (True, True, True, LinkRegionKind.CODE, Tier.C),
            # Wrong target -> exclude/negative, regardless of everything else.
            (False, True, True, LinkRegionKind.PROSE, Tier.D),
            (False, True, True, LinkRegionKind.RELATED_NOTES, Tier.D),
            (False, False, False, LinkRegionKind.CODE, Tier.D),
            # Non-graph-only, non-prose regions follow the prose A/B rules.
            (True, True, True, LinkRegionKind.LIST, Tier.A),
            (True, True, True, LinkRegionKind.CITATION, Tier.A),
            (True, False, True, LinkRegionKind.OTHER, Tier.B),
        ],
    )
    def test_rules(
        self,
        target_correct: bool,
        anchor_natural: bool,
        placement_valid: bool,
        region_kind: LinkRegionKind,
        expected: Tier,
    ) -> None:
        assert derive_tier(target_correct, anchor_natural, placement_valid, region_kind) == expected


class TestBuildAuditReport:
    def test_go_when_agreement_and_positives_meet_thresholds(self) -> None:
        sample = AuditSample(
            header=make_header(), items=(make_item("i1"), make_item("i2"), make_item("i3"))
        )
        tiers = {"i1": Tier.A, "i2": Tier.A, "i3": Tier.B}
        labels = [
            make_label(item_id, annotator, tier=tier)
            for item_id, tier in tiers.items()
            for annotator in ("alice", "bob")
        ]
        report = build_audit_report(sample, labels, min_kappa=0.6, min_clean_positives=3)
        assert report.go is True
        assert report.n_items == 3
        assert report.n_labeled == 3
        assert report.tier_counts == {"a": 2, "b": 1, "c": 0, "d": 0}
        assert report.agreement["kappa_tier"] == pytest.approx(1.0)
        assert report.notes == ()

    def test_single_annotator_never_goes(self) -> None:
        sample = AuditSample(header=make_header(), items=(make_item("i1"),))
        labels = [make_label("i1", "alice")]
        report = build_audit_report(sample, labels, min_clean_positives=1)
        assert report.go is False
        assert report.agreement == {}
        assert any("single annotator" in note for note in report.notes)

    def test_consensus_tie_resolves_to_worse_tier(self) -> None:
        sample = AuditSample(header=make_header(), items=(make_item("i1"),))
        labels = [
            make_label("i1", "alice", tier=Tier.A),
            make_label("i1", "bob", tier=Tier.B),
        ]
        report = build_audit_report(sample, labels, min_clean_positives=1)
        assert report.tier_counts["b"] == 1
        assert report.tier_counts["a"] == 0

    def test_low_kappa_blocks_go_with_note(self) -> None:
        sample = AuditSample(
            header=make_header(), items=tuple(make_item(f"i{i}") for i in range(4))
        )
        naturals_a = (True, True, False, False)
        naturals_b = (True, False, True, False)
        labels = [make_label(f"i{i}", "alice", anchor_natural=naturals_a[i]) for i in range(4)] + [
            make_label(f"i{i}", "bob", anchor_natural=naturals_b[i]) for i in range(4)
        ]
        report = build_audit_report(sample, labels, min_kappa=0.6, min_clean_positives=1)
        assert report.go is False
        assert any("below threshold 0.6" in note for note in report.notes)

    def test_too_few_clean_positives_blocks_go_with_note(self) -> None:
        sample = AuditSample(header=make_header(), items=(make_item("i1"), make_item("i2")))
        labels = [
            make_label(item_id, annotator, tier=Tier.A)
            for item_id in ("i1", "i2")
            for annotator in ("alice", "bob")
        ]
        report = build_audit_report(sample, labels)  # default floor of 150
        assert report.go is False
        expected = "clean Tier A+B positives 2 below threshold 150"
        assert any(expected in note for note in report.notes)

    def test_unlabeled_items_and_foreign_labels_are_noted(self) -> None:
        sample = AuditSample(header=make_header(), items=(make_item("i1"), make_item("i2")))
        labels = [
            make_label("i1", "alice"),
            make_label("i1", "bob"),
            make_label("ghost", "alice"),  # not in the sample
        ]
        report = build_audit_report(sample, labels, min_clean_positives=1)
        assert report.n_labeled == 1
        assert any("1 of 2 items unlabeled" in note for note in report.notes)
        assert any("ignored 1 label(s)" in note for note in report.notes)

    def test_header_carries_run_and_corpus_identity(self) -> None:
        sample = AuditSample(header=make_header(), items=(make_item("i1"),))
        report = build_audit_report(sample, [], run_id="audit-7")
        assert report.header.run_id == "audit-7"
        assert report.header.corpus_id == sample.header.corpus_id
        assert report.header.schema_version == 1
