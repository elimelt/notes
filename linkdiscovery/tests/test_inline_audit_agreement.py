"""Hand-computed agreement statistics: Cohen's kappa, Krippendorff's alpha."""

from __future__ import annotations

import pytest

from linkdiscovery.inline import (
    AuditLabel,
    Tier,
    agreement_report,
    cohen_kappa,
    krippendorff_alpha,
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
    """A label with judgment fields controllable per test."""
    return AuditLabel(
        item_id=item_id,
        annotator=annotator,
        target_correct=target_correct,
        anchor_natural=anchor_natural,
        placement_valid=placement_valid,
        tier=tier,
        labeled_at="2026-07-31T12:00:00+00:00",
    )


class TestCohenKappa:
    def test_classic_two_by_two_example(self) -> None:
        # The textbook example: 20 yes/yes, 5 yes/no, 10 no/yes, 15 no/no.
        # p_o = 35/50 = 0.7; p_e = 0.5*0.6 + 0.5*0.4 = 0.5; kappa = 0.2/0.5 = 0.4.
        labels_a = ["y"] * 20 + ["y"] * 5 + ["n"] * 10 + ["n"] * 15
        labels_b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
        assert cohen_kappa(labels_a, labels_b) == pytest.approx(0.4)

    def test_perfect_agreement_on_two_categories(self) -> None:
        labels = ["a", "b", "a", "b", "b"]
        assert cohen_kappa(labels, labels) == pytest.approx(1.0)

    def test_perfect_agreement_on_constant_category_is_one(self) -> None:
        # p_e = 1.0 would make the ratio 0/0; the guard returns 1.0.
        assert cohen_kappa(["x", "x", "x"], ["x", "x", "x"]) == 1.0

    def test_constant_but_disjoint_raters_score_zero(self) -> None:
        # p_o = 0 and p_e = 0: kappa = (0 - 0) / (1 - 0) = 0.
        assert cohen_kappa(["x", "x"], ["y", "y"]) == pytest.approx(0.0)

    def test_empty_input_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one paired label"):
            cohen_kappa([], [])

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="equal-length"):
            cohen_kappa(["a"], ["a", "b"])


class TestKrippendorffAlpha:
    def test_hand_computed_example_with_missing_label(self) -> None:
        # Units u1..u3 pairable; u4 has a single label and is dropped.
        # Coincidences: o[y,y]=2, o[n,n]=2, o[y,n]=o[n,y]=1; n_y=n_n=3, n=6.
        # D_o = 2; D_e = (36 - 18) / 5 = 3.6; alpha = 1 - 2/3.6 = 4/9.
        labels = {
            "alice": {"u1": "yes", "u2": "no", "u3": "yes", "u4": "no"},
            "bob": {"u1": "yes", "u2": "no", "u3": "no"},
        }
        assert krippendorff_alpha(labels) == pytest.approx(4.0 / 9.0)

    def test_single_observed_category_is_one(self) -> None:
        labels = {"alice": {"u1": "x", "u2": "x"}, "bob": {"u1": "x", "u2": "x"}}
        assert krippendorff_alpha(labels) == 1.0

    def test_three_annotators_perfect_agreement(self) -> None:
        unit_labels = {"u1": "a", "u2": "b", "u3": "a"}
        labels = {"alice": unit_labels, "bob": unit_labels, "carol": unit_labels}
        assert krippendorff_alpha(labels) == pytest.approx(1.0)

    def test_no_pairable_units_raises(self) -> None:
        with pytest.raises(ValueError, match="two or more annotators"):
            krippendorff_alpha({"alice": {"u1": "x"}, "bob": {"u2": "y"}})


class TestAgreementReport:
    def test_reports_kappa_and_alpha_per_field(self) -> None:
        # Four shared items. Tiers agree everywhere (kappa 1.0); anchor_natural
        # disagrees on half in a symmetric pattern (p_o = p_e = 0.5, kappa 0.0;
        # alpha = 1 - 4 / (32/7) = 0.125 by the coincidence matrix).
        naturals_a = (True, True, False, False)
        naturals_b = (True, False, True, False)
        tiers = (Tier.A, Tier.A, Tier.B, Tier.B)
        labels = [
            make_label(f"u{i}", "alice", anchor_natural=naturals_a[i], tier=tiers[i])
            for i in range(4)
        ] + [
            make_label(f"u{i}", "bob", anchor_natural=naturals_b[i], tier=tiers[i])
            for i in range(4)
        ]
        report = agreement_report(labels)
        assert report["kappa_tier"] == pytest.approx(1.0)
        assert report["alpha_tier"] == pytest.approx(1.0)
        assert report["kappa_anchor_natural"] == pytest.approx(0.0)
        assert report["alpha_anchor_natural"] == pytest.approx(0.125)
        assert report["kappa_target_correct"] == pytest.approx(1.0)
        assert report["kappa_placement_valid"] == pytest.approx(1.0)
        assert set(report) == {
            f"{stat}_{field}"
            for stat in ("kappa", "alpha")
            for field in ("target_correct", "anchor_natural", "placement_valid", "tier")
        }

    def test_single_annotator_returns_empty(self) -> None:
        labels = [make_label("u1", "alice"), make_label("u2", "alice")]
        assert agreement_report(labels) == {}

    def test_disjoint_annotators_return_empty(self) -> None:
        labels = [make_label("u1", "alice"), make_label("u2", "bob")]
        assert agreement_report(labels) == {}

    def test_empty_labels_return_empty(self) -> None:
        assert agreement_report([]) == {}

    def test_later_label_replaces_earlier_from_same_annotator(self) -> None:
        labels = [
            make_label("u1", "alice", tier=Tier.D),
            make_label("u1", "alice", tier=Tier.A),  # replaces the D judgment
            make_label("u2", "alice", tier=Tier.B),
            make_label("u1", "bob", tier=Tier.A),
            make_label("u2", "bob", tier=Tier.B),
        ]
        report = agreement_report(labels)
        assert report["kappa_tier"] == pytest.approx(1.0)
