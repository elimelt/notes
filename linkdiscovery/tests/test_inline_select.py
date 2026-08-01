"""Global selection: score combination, budgets, MMR, hard constraints, sweeps."""

from __future__ import annotations

from typing import ClassVar

import numpy as np
import pytest

from linkdiscovery.contracts.documents import SourceDocument
from linkdiscovery.contracts.units import Span
from linkdiscovery.errors import ConfigError
from linkdiscovery.inline import (
    InlineProposal,
    InlineProposalSet,
    SelectionConfig,
    combine_scores,
    precision_recall_sweep,
    select_proposals,
)


def make_doc(doc_id: str, words: int) -> SourceDocument:
    """A source document with exactly ``words`` whitespace-separated words."""
    return SourceDocument(
        id=doc_id,
        revision="r1",
        media_type="text/markdown",
        content=" ".join(f"w{i}" for i in range(words)),
    )


def make_draft(
    draft_id: str,
    *,
    source: str = "note",
    target: str = "target",
    span: tuple[int, int] = (0, 5),
    anchor: str = "anchor phrase",
    naturalness: float = 0.8,
    target_correctness: float = 0.8,
    placement_validity: float = 0.8,
    combined: float = 0.8,
    calibrated: float | None = 0.8,
    abstained: bool = False,
    features: dict[str, float] | None = None,
) -> InlineProposal:
    """A draft proposal with every selection-relevant knob controllable.

    The default anchor is two words so drafts face the ordinary naturalness
    floor; single-word tests pass ``anchor`` explicitly.
    """
    return InlineProposal(
        id=draft_id,
        source_document_id=source,
        span=Span(*span),
        anchor_text=anchor,
        target_document_id=target,
        target_section=None,
        naturalness=naturalness,
        target_correctness=target_correctness,
        placement_validity=placement_validity,
        combined_score=combined,
        calibrated_probability=calibrated,
        abstained=abstained,
        features=features or {},
    )


def accepted_of(result: InlineProposalSet) -> list[InlineProposal]:
    """The selected (non-abstained) proposals, in emitted order."""
    return [p for p in result.proposals if not p.abstained]


def rejected_of(result: InlineProposalSet) -> list[InlineProposal]:
    """The audit-preserving abstained records, in emitted order."""
    return [p for p in result.proposals if p.abstained]


class TestSelectionConfig:
    def test_defaults_match_spec_operating_points(self) -> None:
        config = SelectionConfig()
        assert config.resolved_dict() == {
            "accept_threshold": 0.5,
            "words_per_link": 175,
            "max_links_per_note": 10,
            "mmr_lambda": 0.6,
            "target_redundancy_penalty": 0.3,
            "naturalness_floor": 0.2,
            "existing_target_window_chars": 600,
            "single_word_naturalness_floor": 0.5,
            "max_per_target_per_note": 1,
            "combine_weights": {"naturalness": 0.35, "target": 0.45, "placement": 0.20},
        }

    def test_fingerprint_is_deterministic_and_config_sensitive(self) -> None:
        assert SelectionConfig().fingerprint() == SelectionConfig().fingerprint()
        assert SelectionConfig(mmr_lambda=0.5).fingerprint() != SelectionConfig().fingerprint()

    def test_unknown_weight_key_rejected(self) -> None:
        with pytest.raises(ConfigError, match="unknown combine_weights"):
            SelectionConfig(combine_weights={"naturalness": 1.0, "novelty": 1.0})

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("accept_threshold", 1.5),
            ("words_per_link", 0),
            ("max_links_per_note", 0),
            ("mmr_lambda", -0.1),
            ("target_redundancy_penalty", -1.0),
            ("naturalness_floor", 2.0),
            ("existing_target_window_chars", -1),
            ("single_word_naturalness_floor", 2.0),
            ("max_per_target_per_note", 0),
        ],
    )
    def test_out_of_domain_fields_rejected(self, field_name: str, value: float) -> None:
        with pytest.raises(ConfigError, match=field_name):
            SelectionConfig(**{field_name: value})  # type: ignore[arg-type]

    def test_zero_total_weight_rejected(self) -> None:
        with pytest.raises(ConfigError, match="positive total weight"):
            SelectionConfig(combine_weights={"naturalness": 0.0, "target": 0.0})


class TestCombineScores:
    def test_equal_weights_give_plain_geometric_mean(self) -> None:
        weights = {"naturalness": 1.0, "target": 1.0, "placement": 1.0}
        # (0.5 * 0.5 * 0.5) ** (1/3) = 0.5.
        assert combine_scores(0.5, 0.5, 0.5, weights) == pytest.approx(0.5)
        # (0.9 * 0.4 * 0.6) ** (1/3), hand-computed.
        assert combine_scores(0.9, 0.4, 0.6, weights) == pytest.approx(
            (0.9 * 0.4 * 0.6) ** (1.0 / 3.0)
        )

    def test_weighted_case_hand_computed(self) -> None:
        weights = {"naturalness": 0.35, "target": 0.45, "placement": 0.20}
        expected = (0.8**0.35 * 0.9**0.45 * 0.5**0.20) ** (1.0 / 1.0)
        assert combine_scores(0.8, 0.9, 0.5, weights) == pytest.approx(expected)

    def test_zero_head_vetoes(self) -> None:
        weights = {"naturalness": 0.35, "target": 0.45, "placement": 0.20}
        assert combine_scores(0.0, 1.0, 1.0, weights) == 0.0

    def test_zero_weighted_head_is_ignored(self) -> None:
        weights = {"naturalness": 1.0, "target": 1.0, "placement": 0.0}
        assert combine_scores(0.5, 0.5, 0.0, weights) == pytest.approx(0.5)

    def test_unknown_weight_key_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="unknown combine_weights"):
            combine_scores(0.5, 0.5, 0.5, {"bogus": 1.0})

    def test_out_of_range_score_raises(self) -> None:
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            combine_scores(1.5, 0.5, 0.5, {"naturalness": 1.0})


class TestBudget:
    def test_599_word_note_gets_three_links_at_175_words_per_link(self) -> None:
        docs = {"note": make_doc("note", 599)}
        drafts = [
            make_draft(
                f"d{i}", target=f"t{i}", span=(i * 10, i * 10 + 5), calibrated=0.9 - i * 0.01
            )
            for i in range(5)
        ]
        result = select_proposals(drafts, docs, config=SelectionConfig())
        accepted = accepted_of(result)
        assert len(accepted) == 3  # 599 // 175 = 3
        assert all(p.features["note_budget"] == 3.0 for p in accepted)
        over_budget = rejected_of(result)
        assert len(over_budget) == 2
        assert all(p.features["rejected_over_budget"] == 1.0 for p in over_budget)

    def test_tiny_note_still_allows_one_link(self) -> None:
        docs = {"note": make_doc("note", 20)}
        result = select_proposals([make_draft("d0")], docs, config=SelectionConfig())
        assert len(accepted_of(result)) == 1
        assert accepted_of(result)[0].features["note_budget"] == 1.0

    def test_hard_cap_applies(self) -> None:
        docs = {"note": make_doc("note", 10_000)}
        drafts = [
            make_draft(
                f"d{i}", target=f"t{i}", span=(i * 10, i * 10 + 5), calibrated=0.99 - i * 0.01
            )
            for i in range(12)
        ]
        result = select_proposals(drafts, docs, config=SelectionConfig(max_links_per_note=10))
        assert len(accepted_of(result)) == 10


class TestThresholdsAndQ25:
    def test_below_accept_threshold_is_rejected(self) -> None:
        docs = {"note": make_doc("note", 200)}
        drafts = [make_draft("lo", calibrated=0.4), make_draft("hi", span=(10, 15))]
        result = select_proposals(drafts, docs, config=SelectionConfig())
        assert [p.id for p in accepted_of(result)] == ["hi"]
        (rejected,) = rejected_of(result)
        assert rejected.id == "lo"
        assert rejected.features["rejected_below_accept_threshold"] == 1.0
        assert rejected.features["selection_rejected"] == 1.0

    def test_none_calibrated_probability_falls_back_to_combined(self) -> None:
        docs = {"note": make_doc("note", 200)}
        keep = make_draft("keep", calibrated=None, combined=0.6)
        drop = make_draft("drop", span=(10, 15), calibrated=None, combined=0.4)
        result = select_proposals([keep, drop], docs, config=SelectionConfig())
        assert [p.id for p in accepted_of(result)] == ["keep"]

    def test_upstream_abstained_draft_stays_abstained(self) -> None:
        docs = {"note": make_doc("note", 200)}
        result = select_proposals(
            [make_draft("ab", abstained=True)], docs, config=SelectionConfig()
        )
        assert not accepted_of(result)
        (rejected,) = rejected_of(result)
        assert rejected.features["rejected_abstained_upstream"] == 1.0

    def test_low_naturalness_low_target_is_rejected(self) -> None:
        docs = {"note": make_doc("note", 200)}
        draft = make_draft("weak", naturalness=0.1, target_correctness=0.5)
        result = select_proposals([draft], docs, config=SelectionConfig())
        (rejected,) = rejected_of(result)
        assert rejected.features["rejected_below_naturalness_floor"] == 1.0

    def test_q25_high_target_low_naturalness_kept_and_marked(self) -> None:
        docs = {"note": make_doc("note", 200)}
        draft = make_draft("q25", naturalness=0.1, target_correctness=0.9)
        result = select_proposals([draft], docs, config=SelectionConfig())
        (accepted,) = accepted_of(result)
        assert accepted.id == "q25"
        assert accepted.features["suggest_better_anchor"] == 1.0
        assert accepted.abstained is False
        assert accepted.review.status == "unreviewed"

    def test_q25_draft_counts_against_the_budget(self) -> None:
        # Budget of one: the higher-probability Q25 draft takes the slot.
        docs = {"note": make_doc("note", 100)}
        q25 = make_draft("q25", naturalness=0.1, target_correctness=0.9, calibrated=0.9)
        plain = make_draft("plain", target="other", span=(10, 15), calibrated=0.7)
        result = select_proposals([q25, plain], docs, config=SelectionConfig())
        assert [p.id for p in accepted_of(result)] == ["q25"]
        (rejected,) = rejected_of(result)
        assert rejected.features["rejected_over_budget"] == 1.0

    def test_q25_does_not_rescue_below_accept_threshold(self) -> None:
        docs = {"note": make_doc("note", 200)}
        draft = make_draft("q25", naturalness=0.1, target_correctness=0.9, calibrated=0.3)
        result = select_proposals([draft], docs, config=SelectionConfig())
        (rejected,) = rejected_of(result)
        assert rejected.features["rejected_below_accept_threshold"] == 1.0


class TestMMR:
    def test_diversity_reorders_same_target_drafts(self) -> None:
        # Budget 2 (350 words). Round 1 picks d1 (highest relevance). Round 2:
        # d2 shares d1's target (sim 1.0): 0.6*0.85 - 0.4 - 0.3 = -0.19;
        # d3 has a fresh target: 0.6*0.7 = 0.42 -> d3 wins despite lower prob.
        # max_per_target_per_note=2 keeps the same-target cap out of the way
        # so the test pins pure MMR ordering.
        docs = {"note": make_doc("note", 350)}
        config = SelectionConfig(max_per_target_per_note=2)
        d1 = make_draft("d1", target="t1", span=(0, 5), calibrated=0.9)
        d2 = make_draft("d2", target="t1", span=(10, 15), calibrated=0.85)
        d3 = make_draft("d3", target="t2", span=(20, 25), calibrated=0.7)
        result = select_proposals([d1, d2, d3], docs, config=config)
        assert sorted(p.id for p in accepted_of(result)) == ["d1", "d3"]
        (rejected,) = rejected_of(result)
        assert rejected.id == "d2"
        assert rejected.features["rejected_over_budget"] == 1.0

    def test_mmr_adjusted_scores_are_recorded(self) -> None:
        docs = {"note": make_doc("note", 350)}
        d1 = make_draft("d1", target="t1", span=(0, 5), calibrated=0.9)
        d3 = make_draft("d3", target="t2", span=(20, 25), calibrated=0.7)
        result = select_proposals([d1, d3], docs, config=SelectionConfig())
        by_id = {p.id: p for p in accepted_of(result)}
        assert by_id["d1"].features["mmr_adjusted_score"] == pytest.approx(0.6 * 0.9)
        assert by_id["d3"].features["mmr_adjusted_score"] == pytest.approx(0.6 * 0.7)

    def test_same_target_penalty_alone_reorders(self) -> None:
        # lambda = 1.0 removes the similarity term; only the same-target
        # penalty acts: d2 scores 0.85 - 0.3 = 0.55 < d3's 0.7.
        docs = {"note": make_doc("note", 350)}
        config = SelectionConfig(
            mmr_lambda=1.0, target_redundancy_penalty=0.3, max_per_target_per_note=2
        )
        d1 = make_draft("d1", target="t1", span=(0, 5), calibrated=0.9)
        d2 = make_draft("d2", target="t1", span=(10, 15), calibrated=0.85)
        d3 = make_draft("d3", target="t2", span=(20, 25), calibrated=0.7)
        result = select_proposals([d1, d2, d3], docs, config=config)
        assert sorted(p.id for p in accepted_of(result)) == ["d1", "d3"]

    def test_target_similarity_mapping_is_used_symmetrically(self) -> None:
        # t2 is near-duplicate of t1 (sim 0.9): 0.6*0.85 - 0.4*0.9 = 0.15 <
        # 0.6*0.7 = 0.42 for unrelated t3 -> t3 selected second.
        docs = {"note": make_doc("note", 350)}
        d1 = make_draft("d1", target="t1", span=(0, 5), calibrated=0.9)
        d2 = make_draft("d2", target="t2", span=(10, 15), calibrated=0.85)
        d3 = make_draft("d3", target="t3", span=(20, 25), calibrated=0.7)
        result = select_proposals(
            [d1, d2, d3],
            docs,
            config=SelectionConfig(),
            # Keyed (t1, t2) while MMR looks up (t2, t1): reversed pairs count.
            target_similarity={("t1", "t2"): 0.9},
        )
        assert sorted(p.id for p in accepted_of(result)) == ["d1", "d3"]


class TestHardConstraints:
    def test_overlapping_spans_keep_the_higher_score(self) -> None:
        docs = {"note": make_doc("note", 2000)}
        low = make_draft("low", span=(5, 15), calibrated=0.8)
        high = make_draft("high", span=(0, 10), calibrated=0.9)
        result = select_proposals([low, high], docs, config=SelectionConfig())
        assert [p.id for p in accepted_of(result)] == ["high"]
        (rejected,) = rejected_of(result)
        assert rejected.id == "low"
        assert rejected.features["rejected_overlaps_selected_span"] == 1.0

    def test_overlap_tie_breaks_by_span_start_then_id(self) -> None:
        docs = {"note": make_doc("note", 2000)}
        later = make_draft("a-later", span=(5, 15), calibrated=0.8)
        earlier = make_draft("z-earlier", span=(0, 10), calibrated=0.8)
        result = select_proposals([later, earlier], docs, config=SelectionConfig())
        assert [p.id for p in accepted_of(result)] == ["z-earlier"]

    def test_touching_spans_do_not_overlap(self) -> None:
        docs = {"note": make_doc("note", 2000)}
        a = make_draft("a", target="t1", span=(0, 10), calibrated=0.9)
        b = make_draft("b", target="t2", span=(10, 20), calibrated=0.8)
        result = select_proposals([a, b], docs, config=SelectionConfig())
        assert len(accepted_of(result)) == 2

    def test_existing_link_overlap_feature_raises(self) -> None:
        docs = {"note": make_doc("note", 200)}
        draft = make_draft("bad", features={"overlaps_existing_link": 1.0})
        with pytest.raises(ValueError, match="excluded upstream"):
            select_proposals([draft], docs, config=SelectionConfig())

    def test_missing_source_document_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown source document"):
            select_proposals([make_draft("d0")], {}, config=SelectionConfig())


class TestExistingTargetProximity:
    """Rule A: suppression near links the author already wrote (report mode 3)."""

    DOCS: ClassVar[dict[str, SourceDocument]] = {"note": make_doc("note", 200)}

    def test_same_target_within_window_is_rejected_with_gap_feature(self) -> None:
        existing = {"note": [(Span(50, 60), "target")]}
        result = select_proposals(
            [make_draft("d0", span=(0, 5))],
            self.DOCS,
            config=SelectionConfig(),
            existing_links=existing,
        )
        assert not accepted_of(result)
        (rejected,) = rejected_of(result)
        assert rejected.abstained is True
        assert rejected.features["rejected_near_existing_same_target"] == 1.0
        assert rejected.features["selection_rejected"] == 1.0
        assert rejected.features["existing_same_target_gap"] == 45.0  # 50 - 5

    def test_overlapping_existing_link_has_gap_zero(self) -> None:
        existing = {"note": [(Span(3, 10), "target")]}
        result = select_proposals(
            [make_draft("d0", span=(0, 5))],
            self.DOCS,
            config=SelectionConfig(),
            existing_links=existing,
        )
        (rejected,) = rejected_of(result)
        assert rejected.features["existing_same_target_gap"] == 0.0

    def test_gap_is_to_the_nearest_same_target_link(self) -> None:
        existing = {"note": [(Span(310, 320), "target"), (Span(50, 60), "target")]}
        result = select_proposals(
            [make_draft("d0", span=(0, 5))],
            self.DOCS,
            config=SelectionConfig(),
            existing_links=existing,
        )
        (rejected,) = rejected_of(result)
        assert rejected.features["existing_same_target_gap"] == 45.0

    def test_same_target_outside_window_is_kept(self) -> None:
        existing = {"note": [(Span(700, 710), "target")]}  # gap 695 > 600
        result = select_proposals(
            [make_draft("d0", span=(0, 5))],
            self.DOCS,
            config=SelectionConfig(),
            existing_links=existing,
        )
        assert [p.id for p in accepted_of(result)] == ["d0"]

    def test_different_target_nearby_is_kept(self) -> None:
        existing = {"note": [(Span(10, 20), "other")]}
        result = select_proposals(
            [make_draft("d0", span=(0, 5))],
            self.DOCS,
            config=SelectionConfig(),
            existing_links=existing,
        )
        assert [p.id for p in accepted_of(result)] == ["d0"]

    def test_window_zero_disables_the_rule(self) -> None:
        existing = {"note": [(Span(10, 20), "target")]}
        result = select_proposals(
            [make_draft("d0", span=(0, 5))],
            self.DOCS,
            config=SelectionConfig(existing_target_window_chars=0),
            existing_links=existing,
        )
        assert [p.id for p in accepted_of(result)] == ["d0"]

    def test_links_in_other_documents_never_trigger(self) -> None:
        existing = {"other-note": [(Span(0, 10), "target")]}
        result = select_proposals(
            [make_draft("d0", span=(0, 5))],
            self.DOCS,
            config=SelectionConfig(),
            existing_links=existing,
        )
        assert [p.id for p in accepted_of(result)] == ["d0"]


class TestSingleWordFloor:
    """Rule C: raised naturalness floor for generic single words (report mode 4)."""

    DOCS: ClassVar[dict[str, SourceDocument]] = {"note": make_doc("note", 200)}

    def test_lowercase_single_word_below_floor_is_rejected(self) -> None:
        # Above the ordinary floor (0.2) but below the single-word one (0.5).
        draft = make_draft("res", anchor="resistance", naturalness=0.3, target_correctness=0.5)
        result = select_proposals([draft], self.DOCS, config=SelectionConfig())
        assert not accepted_of(result)
        (rejected,) = rejected_of(result)
        assert rejected.features["rejected_below_single_word_floor"] == 1.0

    @pytest.mark.parametrize("anchor", ["Paxos", "TCP"])
    def test_title_shaped_single_word_keeps_the_ordinary_floor(self, anchor: str) -> None:
        draft = make_draft("d0", anchor=anchor, naturalness=0.3, target_correctness=0.5)
        result = select_proposals([draft], self.DOCS, config=SelectionConfig())
        assert [p.id for p in accepted_of(result)] == ["d0"]

    def test_two_word_anchor_keeps_the_ordinary_floor(self) -> None:
        draft = make_draft(
            "d0", anchor="memory management", naturalness=0.3, target_correctness=0.5
        )
        result = select_proposals([draft], self.DOCS, config=SelectionConfig())
        assert [p.id for p in accepted_of(result)] == ["d0"]

    def test_q25_rescue_still_fires_for_single_words(self) -> None:
        draft = make_draft("q25", anchor="resistance", naturalness=0.3, target_correctness=0.9)
        result = select_proposals([draft], self.DOCS, config=SelectionConfig())
        (accepted,) = accepted_of(result)
        assert accepted.id == "q25"
        assert accepted.features["suggest_better_anchor"] == 1.0

    def test_effective_floor_is_the_max_of_the_two_floors(self) -> None:
        # A single-word floor BELOW the ordinary floor never lowers it.
        config = SelectionConfig(naturalness_floor=0.4, single_word_naturalness_floor=0.0)
        draft = make_draft("res", anchor="resistance", naturalness=0.3, target_correctness=0.5)
        result = select_proposals([draft], self.DOCS, config=config)
        (rejected,) = rejected_of(result)
        assert rejected.features["rejected_below_single_word_floor"] == 1.0


class TestSameTargetNoteCap:
    """Rule D: hard per-note cap on accepted proposals sharing one target.

    The MMR redundancy penalty only reorders picks; acceptance is
    thresholded on the raw effective score, so without the cap one note can
    accept the same target many times.
    """

    DOCS: ClassVar[dict[str, SourceDocument]] = {"note": make_doc("note", 599)}  # budget 3

    def drafts(self) -> list[InlineProposal]:
        return [
            make_draft("d1", span=(0, 5), calibrated=0.9),
            make_draft("d2", span=(10, 15), calibrated=0.85),
            make_draft("d3", span=(20, 25), calibrated=0.8),
        ]  # all share the default target

    def test_default_cap_accepts_only_the_best_same_target_draft(self) -> None:
        result = select_proposals(self.drafts(), self.DOCS, config=SelectionConfig())
        assert [p.id for p in accepted_of(result)] == ["d1"]
        rejected = rejected_of(result)
        assert {p.id for p in rejected} == {"d2", "d3"}
        assert all(p.features["rejected_same_target_note_cap"] == 1.0 for p in rejected)
        assert all(p.abstained for p in rejected)

    def test_cap_of_two_accepts_the_two_best(self) -> None:
        config = SelectionConfig(max_per_target_per_note=2)
        result = select_proposals(self.drafts(), self.DOCS, config=config)
        assert sorted(p.id for p in accepted_of(result)) == ["d1", "d2"]
        (rejected,) = rejected_of(result)
        assert rejected.id == "d3"
        assert rejected.features["rejected_same_target_note_cap"] == 1.0

    def test_different_targets_are_unaffected(self) -> None:
        drafts = [
            make_draft("d1", target="t1", span=(0, 5), calibrated=0.9),
            make_draft("d2", target="t2", span=(10, 15), calibrated=0.85),
            make_draft("d3", target="t3", span=(20, 25), calibrated=0.8),
        ]
        result = select_proposals(drafts, self.DOCS, config=SelectionConfig())
        assert sorted(p.id for p in accepted_of(result)) == ["d1", "d2", "d3"]


class TestGlobalOrderingAndArtifact:
    def test_accepted_ranked_by_probability_desc_across_notes(self) -> None:
        docs = {"n1": make_doc("n1", 400), "n2": make_doc("n2", 400)}
        drafts = [
            make_draft("a", source="n1", target="t1", calibrated=0.7),
            make_draft("b", source="n2", target="t2", calibrated=0.9),
            make_draft("c", source="n1", target="t3", span=(20, 25), calibrated=0.8),
        ]
        result = select_proposals(drafts, docs, config=SelectionConfig())
        accepted = accepted_of(result)
        assert [p.id for p in accepted] == ["b", "c", "a"]
        assert [p.features["selection_rank"] for p in accepted] == [1.0, 2.0, 3.0]

    def test_rank_ties_break_deterministically(self) -> None:
        docs = {"note": make_doc("note", 400)}
        drafts = [
            make_draft("zz", target="t1", span=(0, 5), calibrated=0.8),
            make_draft("aa", target="t2", span=(10, 15), calibrated=0.8),
        ]
        result = select_proposals(drafts, docs, config=SelectionConfig())
        # Equal probability: earlier span start wins the tie.
        assert [p.id for p in accepted_of(result)] == ["zz", "aa"]

    def test_header_carries_config_fingerprint_and_producer(self) -> None:
        docs = {"note": make_doc("note", 200)}
        config = SelectionConfig()
        result = select_proposals(
            [make_draft("d0")], docs, config=config, run_id="run-1", corpus_id="corpus-1"
        )
        assert result.header.run_id == "run-1"
        assert result.header.corpus_id == "corpus-1"
        assert result.header.config_fingerprint == config.fingerprint()
        assert result.header.producer_version == "linkdiscovery-inline/0.1.0"

    def test_round_trips_through_the_contract(self) -> None:
        docs = {"note": make_doc("note", 400)}
        drafts = [make_draft("d0"), make_draft("d1", span=(10, 15), calibrated=0.4)]
        result = select_proposals(drafts, docs, config=SelectionConfig())
        restored = InlineProposalSet.from_dict(result.to_dict())
        assert restored == result

    def test_determinism_same_input_same_output(self) -> None:
        docs = {"n1": make_doc("n1", 599), "n2": make_doc("n2", 350)}
        drafts = [
            make_draft("a", source="n1", target="t1", span=(0, 5), calibrated=0.9),
            make_draft("b", source="n1", target="t1", span=(10, 15), calibrated=0.85),
            make_draft("c", source="n1", target="t2", span=(20, 25), calibrated=0.7),
            make_draft("d", source="n2", target="t3", span=(0, 8), calibrated=0.6),
            make_draft("e", source="n2", target="t3", span=(4, 12), calibrated=0.65),
            make_draft("f", source="n2", naturalness=0.1, span=(30, 35), calibrated=0.55),
        ]
        first = select_proposals(drafts, docs, config=SelectionConfig())
        second = select_proposals(list(reversed(drafts)), docs, config=SelectionConfig())
        # Header timestamps may differ; the proposal payloads must not.
        assert [p.to_dict() for p in first.proposals] == [p.to_dict() for p in second.proposals]


class TestPrecisionRecallSweep:
    def test_hand_computed_table(self) -> None:
        probs = np.array([0.9, 0.8, 0.7, 0.6])
        labels = np.array([True, True, False, True])
        rows = precision_recall_sweep(probs, labels, [0.5, 0.75, 0.95])
        assert rows == [
            {
                "threshold": 0.5,
                "precision": pytest.approx(0.75),
                "recall": pytest.approx(1.0),
                "accepted_count": 4.0,
            },
            {
                "threshold": 0.75,
                "precision": pytest.approx(1.0),
                "recall": pytest.approx(2.0 / 3.0),
                "accepted_count": 2.0,
            },
            {
                "threshold": 0.95,
                "precision": 0.0,
                "recall": 0.0,
                "accepted_count": 0.0,
            },
        ]

    def test_threshold_is_inclusive(self) -> None:
        rows = precision_recall_sweep(np.array([0.5]), np.array([True]), [0.5])
        assert rows[0]["accepted_count"] == 1.0

    def test_no_positive_labels_raises(self) -> None:
        with pytest.raises(ValueError, match="no positive example"):
            precision_recall_sweep(np.array([0.5]), np.array([False]), [0.5])

    def test_empty_inputs_raise(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            precision_recall_sweep(np.array([]), np.array([], dtype=bool), [0.5])
        with pytest.raises(ValueError, match="thresholds"):
            precision_recall_sweep(np.array([0.5]), np.array([True]), [])
