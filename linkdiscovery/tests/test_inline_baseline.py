"""Hand-computed tests for the deterministic baseline engine (SPEC §12)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import ClassVar

import numpy as np
import pytest

from linkdiscovery.contracts.units import Span
from linkdiscovery.errors import ConfigError
from linkdiscovery.inline import (
    BaselineConfig,
    InlineProposal,
    LinkRegionKind,
    SpanCandidate,
    levenshtein_ratio,
    propose_baseline,
    score_baseline,
)


def make_candidate(
    candidate_id: str = "c1",
    document_id: str = "src",
    text: str = "mapreduce",
    *,
    region_kind: LinkRegionKind = LinkRegionKind.PROSE,
    word_count: int = 1,
    features: dict[str, float] | None = None,
    start: int = 0,
) -> SpanCandidate:
    """A span candidate with controllable features and region."""
    return SpanCandidate(
        id=candidate_id,
        document_id=document_id,
        unit_id=None,
        span=Span(start, start + len(text)),
        text=text,
        region_kind=region_kind,
        word_count=word_count,
        features=dict(features or {}),
    )


class TestLevenshteinRatio:
    def test_kitten_sitting_pinned_value(self) -> None:
        # distance("kitten", "sitting") = 3, max length 7.
        assert levenshtein_ratio("kitten", "sitting") == pytest.approx(1 - 3 / 7)

    def test_identical_strings(self) -> None:
        assert levenshtein_ratio("mapreduce", "mapreduce") == 1.0

    def test_both_empty(self) -> None:
        assert levenshtein_ratio("", "") == 1.0

    def test_one_empty(self) -> None:
        assert levenshtein_ratio("", "abc") == 0.0
        assert levenshtein_ratio("abc", "") == 0.0

    def test_single_substitution(self) -> None:
        assert levenshtein_ratio("abc", "abd") == pytest.approx(1 - 1 / 3)

    def test_flaw_lawn_pinned_value(self) -> None:
        # distance("flaw", "lawn") = 2, max length 4.
        assert levenshtein_ratio("flaw", "lawn") == pytest.approx(0.5)

    def test_symmetric(self) -> None:
        assert levenshtein_ratio("kitten", "sitting") == levenshtein_ratio("sitting", "kitten")


class TestBaselineConfig:
    def test_fingerprint_is_stable_and_weight_sensitive(self) -> None:
        assert BaselineConfig().fingerprint() == BaselineConfig().fingerprint()
        changed = BaselineConfig(commonness_weight=0.5)
        assert changed.fingerprint() != BaselineConfig().fingerprint()
        assert BaselineConfig().fingerprint().startswith("sha256:")

    def test_resolved_dict_round_trips_through_constructor(self) -> None:
        config = BaselineConfig(top_k_targets=3, position_penalty=0.5)
        assert BaselineConfig(**config.resolved_dict()) == config

    def test_invalid_top_k_raises(self) -> None:
        with pytest.raises(ConfigError, match="top_k_targets"):
            BaselineConfig(top_k_targets=0)

    def test_negative_weight_raises(self) -> None:
        with pytest.raises(ConfigError, match="commonness_weight"):
            BaselineConfig(commonness_weight=-0.1)

    def test_out_of_range_factor_raises(self) -> None:
        with pytest.raises(ConfigError, match="single_word_factor"):
            BaselineConfig(single_word_factor=1.5)

    def test_zero_saturation_raises(self) -> None:
        with pytest.raises(ConfigError, match="keyphraseness_saturation"):
            BaselineConfig(keyphraseness_saturation=0.0)

    def test_zero_weight_group_raises(self) -> None:
        with pytest.raises(ConfigError, match="keyphraseness_weight"):
            BaselineConfig(keyphraseness_weight=0.0, match_weight=0.0)

    @pytest.mark.parametrize("value", [-0.1, 1.5])
    def test_out_of_range_cross_family_penalty_raises(self, value: float) -> None:
        with pytest.raises(ConfigError, match="cross_family_penalty"):
            BaselineConfig(cross_family_penalty=value)

    def test_cross_family_penalty_enters_the_fingerprint(self) -> None:
        # Intended: the new field changes the config fingerprint and thus
        # every draft's model_version.
        assert "cross_family_penalty" in BaselineConfig().resolved_dict()
        changed = BaselineConfig(cross_family_penalty=0.5)
        assert changed.fingerprint() != BaselineConfig().fingerprint()


class TestScoreBaseline:
    CONFIG = BaselineConfig()

    def score(
        self,
        candidate: SpanCandidate,
        *,
        commonness: float = 0.5,
        target_vector_sim: float = 0.5,
        ambiguity: int = 1,
        levenshtein_title: float = 0.5,
        same_family: float | None = None,
    ) -> tuple[float, float, float]:
        return score_baseline(
            candidate,
            "target",
            commonness=commonness,
            target_vector_sim=target_vector_sim,
            ambiguity=ambiguity,
            levenshtein_title=levenshtein_title,
            same_family=same_family,
            config=self.CONFIG,
        )

    def test_all_scores_stay_in_unit_interval(self) -> None:
        candidate = make_candidate(
            features={"keyphraseness": 5.0, "is_title_match": 1.0, "sentence_position": 1.0},
            word_count=8,
        )
        scores = self.score(
            candidate, commonness=2.0, target_vector_sim=-1.0, ambiguity=50, levenshtein_title=1.0
        )
        for value in scores:
            assert 0.0 <= value <= 1.0

    def test_higher_keyphraseness_raises_naturalness(self) -> None:
        low = make_candidate(features={"keyphraseness": 0.05}, word_count=2)
        high = make_candidate(features={"keyphraseness": 0.15}, word_count=2)
        assert self.score(high)[0] > self.score(low)[0]

    def test_title_match_raises_naturalness(self) -> None:
        plain = make_candidate(features={"keyphraseness": 0.1}, word_count=2)
        matched = make_candidate(
            features={"keyphraseness": 0.1, "is_title_match": 1.0}, word_count=2
        )
        assert self.score(matched)[0] > self.score(plain)[0]

    def test_word_count_sweet_spot_beats_one_and_many_words(self) -> None:
        features = {"keyphraseness": 0.2}
        sweet = make_candidate(features=features, word_count=2)
        single = make_candidate(features=features, word_count=1)
        long = make_candidate(features=features, word_count=7)
        assert self.score(sweet)[0] > self.score(single)[0]
        assert self.score(sweet)[0] > self.score(long)[0]

    def test_more_ambiguity_lowers_target_correctness(self) -> None:
        candidate = make_candidate()
        assert self.score(candidate, ambiguity=5)[1] < self.score(candidate, ambiguity=1)[1]

    def test_higher_commonness_raises_target_correctness(self) -> None:
        candidate = make_candidate()
        assert self.score(candidate, commonness=0.8)[1] > self.score(candidate, commonness=0.2)[1]

    def test_higher_embedding_similarity_raises_target_correctness(self) -> None:
        candidate = make_candidate()
        low = self.score(candidate, target_vector_sim=0.1)[1]
        high = self.score(candidate, target_vector_sim=0.9)[1]
        assert high > low

    def test_negative_cosine_clamps_to_zero(self) -> None:
        candidate = make_candidate()
        assert (
            self.score(candidate, target_vector_sim=-1.0)[1]
            == self.score(candidate, target_vector_sim=0.0)[1]
        )

    def test_prose_placement_and_position_penalty(self) -> None:
        at_start = make_candidate(features={"sentence_position": 0.0})
        at_end = make_candidate(features={"sentence_position": 1.0})
        assert self.score(at_start)[2] == pytest.approx(1.0)
        assert self.score(at_end)[2] == pytest.approx(1.0 - self.CONFIG.position_penalty)

    def test_non_prose_placement_floors_at_config_value(self) -> None:
        code = make_candidate(region_kind=LinkRegionKind.CODE)
        assert self.score(code)[2] == pytest.approx(self.CONFIG.non_prose_placement)

    def test_region_prose_feature_backs_up_the_region_kind(self) -> None:
        listed = make_candidate(region_kind=LinkRegionKind.LIST, features={"region_prose": 1.0})
        assert self.score(listed)[2] == pytest.approx(1.0)

    def test_cross_family_penalty_scales_target_correctness_exactly(self) -> None:
        candidate = make_candidate()
        baseline = self.score(candidate)[1]
        penalized = self.score(candidate, same_family=0.0)[1]
        assert penalized == pytest.approx(baseline * (1.0 - self.CONFIG.cross_family_penalty))

    def test_same_family_one_and_none_are_no_ops(self) -> None:
        candidate = make_candidate()
        baseline = self.score(candidate)
        assert self.score(candidate, same_family=1.0) == pytest.approx(baseline)
        assert self.score(candidate, same_family=None) == pytest.approx(baseline)

    def test_target_correctness_is_monotone_in_same_family(self) -> None:
        candidate = make_candidate()
        low = self.score(candidate, same_family=0.0)[1]
        mid = self.score(candidate, same_family=0.5)[1]
        high = self.score(candidate, same_family=1.0)[1]
        assert low < mid < high

    def test_same_family_is_clamped_to_the_unit_interval(self) -> None:
        candidate = make_candidate()
        assert self.score(candidate, same_family=-2.0) == self.score(candidate, same_family=0.0)
        assert self.score(candidate, same_family=3.0) == self.score(candidate, same_family=1.0)

    def test_penalty_only_touches_the_target_head(self) -> None:
        candidate = make_candidate(features={"keyphraseness": 0.1, "sentence_position": 0.5})
        plain = self.score(candidate)
        penalized = self.score(candidate, same_family=0.0)
        assert penalized[0] == plain[0]
        assert penalized[2] == plain[2]


def lookup_mapreduce(mention: str) -> Mapping[str, int]:
    """Anchor-dictionary stub: 'mapreduce' resolves to t1 (8) and t2 (2)."""
    if " ".join(mention.split()).casefold() == "mapreduce":
        return {"t1": 8, "t2": 2}
    return {}


class TestProposeBaseline:
    TITLES: ClassVar[dict[str, str]] = {
        "t1": "MapReduce",
        "t2": "MapReduce Survey",
        "src": "Source Note",
    }
    DOC_VECTORS: ClassVar[dict[str, np.ndarray]] = {
        "t1": np.asarray([1.0, 0.0], dtype=np.float32),
        "t2": np.asarray([0.0, 1.0], dtype=np.float32),
    }

    @staticmethod
    def span_vector(_: SpanCandidate) -> np.ndarray:
        return np.asarray([1.0, 0.0], dtype=np.float32)

    def test_emits_one_draft_with_the_best_target(self) -> None:
        candidate = make_candidate(
            text="MapReduce", features={"keyphraseness": 0.2, "is_title_match": 1.0}
        )
        config = BaselineConfig()
        proposals = propose_baseline(
            {"src": [candidate]},
            lookup_mapreduce,
            self.DOC_VECTORS,
            self.span_vector,
            self.TITLES,
            config=config,
        )
        assert len(proposals) == 1
        proposal = proposals[0]
        # t1 dominates: commonness 0.8 vs 0.2, cosine 1.0 vs 0.0, exact title.
        assert proposal.target_document_id == "t1"
        assert proposal.source_document_id == "src"
        assert proposal.anchor_text == "MapReduce"
        assert proposal.model_version == "baseline-" + config.fingerprint()
        assert proposal.abstained is False
        assert proposal.calibrated_probability is None
        assert proposal.target_section is None
        assert proposal.review.status == "unreviewed"
        assert proposal.combined_score == pytest.approx(
            (proposal.naturalness * proposal.target_correctness * proposal.placement_validity)
            ** (1 / 3)
        )
        assert proposal.features["commonness"] == pytest.approx(0.8)
        assert proposal.features["ambiguity"] == 2.0
        assert proposal.features["embedding_similarity"] == pytest.approx(1.0)
        assert proposal.features["levenshtein_title"] == pytest.approx(1.0)

    def test_draft_emission_is_deterministic(self) -> None:
        candidates = [
            make_candidate("c1", "src", "MapReduce", features={"keyphraseness": 0.1}),
            make_candidate("c2", "src", "MapReduce", start=50, features={"keyphraseness": 0.3}),
        ]
        args = (lookup_mapreduce, self.DOC_VECTORS, self.span_vector, self.TITLES)
        config = BaselineConfig()
        first = propose_baseline({"src": candidates, "other": []}, *args, config=config)
        second = propose_baseline({"other": [], "src": candidates}, *args, config=config)
        assert first == second
        assert [p.span.start for p in first] == [0, 50]
        assert len({p.id for p in first}) == 2

    def test_never_proposes_a_self_link(self) -> None:
        candidate = make_candidate("c1", "t1", "MapReduce")
        proposals = propose_baseline(
            {"t1": [candidate]},
            lookup_mapreduce,
            self.DOC_VECTORS,
            self.span_vector,
            self.TITLES,
            config=BaselineConfig(),
        )
        assert len(proposals) == 1
        assert proposals[0].target_document_id == "t2"

    def test_no_targets_means_no_draft(self) -> None:
        candidate = make_candidate("c1", "src", "unknown phrase")
        proposals = propose_baseline(
            {"src": [candidate]},
            lookup_mapreduce,
            self.DOC_VECTORS,
            self.span_vector,
            {},
            config=BaselineConfig(),
        )
        assert proposals == ()

    def test_title_match_supplies_targets_outside_the_dictionary(self) -> None:
        candidate = make_candidate("c1", "src", "MapReduce   Survey", word_count=2)
        proposals = propose_baseline(
            {"src": [candidate]},
            lambda _: {},
            self.DOC_VECTORS,
            None,
            self.TITLES,
            config=BaselineConfig(),
        )
        assert len(proposals) == 1
        assert proposals[0].target_document_id == "t2"
        assert proposals[0].features["commonness"] == 0.0

    def test_none_span_vectors_zero_the_embedding_signal(self) -> None:
        candidate = make_candidate("c1", "src", "MapReduce")
        proposals = propose_baseline(
            {"src": [candidate]},
            lookup_mapreduce,
            self.DOC_VECTORS,
            None,
            self.TITLES,
            config=BaselineConfig(),
        )
        assert len(proposals) == 1
        assert proposals[0].features["embedding_similarity"] == 0.0

    def propose_with_families(
        self, candidate: SpanCandidate, families: dict[str, str] | None
    ) -> tuple[InlineProposal, ...]:
        return propose_baseline(
            {candidate.document_id: [candidate]},
            lookup_mapreduce,
            self.DOC_VECTORS,
            None,
            self.TITLES,
            config=BaselineConfig(),
            families=families,
        )

    def test_cross_family_target_is_penalized_and_feature_recorded(self) -> None:
        # Lowercase, non-acronym anchor: the family prior applies.
        candidate = make_candidate(text="mapreduce", features={"keyphraseness": 0.2})
        (plain,) = self.propose_with_families(candidate, None)
        (penalized,) = self.propose_with_families(candidate, {"src": "os", "t1": "ml", "t2": "ml"})
        assert penalized.target_document_id == plain.target_document_id
        assert penalized.features["same_family"] == 0.0
        assert penalized.target_correctness == pytest.approx(
            plain.target_correctness * (1.0 - BaselineConfig().cross_family_penalty)
        )
        assert "same_family" not in plain.features

    def test_same_family_target_is_not_penalized(self) -> None:
        candidate = make_candidate(text="mapreduce", features={"keyphraseness": 0.2})
        (plain,) = self.propose_with_families(candidate, None)
        (same,) = self.propose_with_families(candidate, {"src": "os", "t1": "os", "t2": "os"})
        assert same.features["same_family"] == 1.0
        assert same.target_correctness == pytest.approx(plain.target_correctness)

    @pytest.mark.parametrize("shape_feature", ["is_titlecase", "is_acronym"])
    def test_proper_name_shaped_anchors_are_exempt(self, shape_feature: str) -> None:
        candidate = make_candidate(
            text="MapReduce", features={"keyphraseness": 0.2, shape_feature: 1.0}
        )
        (plain,) = self.propose_with_families(candidate, None)
        (exempt,) = self.propose_with_families(candidate, {"src": "os", "t1": "ml", "t2": "ml"})
        assert "same_family" not in exempt.features
        assert exempt.target_correctness == pytest.approx(plain.target_correctness)

    @pytest.mark.parametrize(
        "families",
        [
            {"src": "os"},  # target families unknown
            {"t1": "ml", "t2": "ml"},  # source family unknown
        ],
    )
    def test_unknown_families_are_never_penalized(self, families: dict[str, str]) -> None:
        candidate = make_candidate(text="mapreduce", features={"keyphraseness": 0.2})
        (plain,) = self.propose_with_families(candidate, None)
        (unknown,) = self.propose_with_families(candidate, families)
        assert "same_family" not in unknown.features
        assert unknown.target_correctness == pytest.approx(plain.target_correctness)

    def test_top_k_caps_the_scored_targets(self) -> None:
        def lookup(mention: str) -> Mapping[str, int]:
            del mention
            return {"t1": 1, "t2": 9}

        candidate = make_candidate("c1", "src", "MapReduce")
        proposals = propose_baseline(
            {"src": [candidate]},
            lookup,
            self.DOC_VECTORS,
            None,
            {},
            config=BaselineConfig(top_k_targets=1),
        )
        # Only the highest-count target (t2) survives the shortlist.
        assert len(proposals) == 1
        assert proposals[0].target_document_id == "t2"
