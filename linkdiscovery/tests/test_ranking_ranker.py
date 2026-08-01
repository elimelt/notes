"""WeightedRanker tests: filters, scoring, direction, evidence, MMR, calibration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from linkdiscovery.candidates import DefaultCandidateGenerator
from linkdiscovery.config import CandidateConfig, RankingConfig
from linkdiscovery.contracts.candidates import CandidatePair, CandidateSet, UnitMatch
from linkdiscovery.contracts.documents import RelationshipSet
from linkdiscovery.contracts.proposals import Confidence, LinkProposal, ProposalSet
from linkdiscovery.contracts.reviews import DecisionKind, ReviewDecision, ReviewHistory
from linkdiscovery.contracts.units import (
    ProcessedCorpus,
    ProcessedDocument,
    RegionKind,
    SemanticUnit,
    Span,
)
from linkdiscovery.fingerprint import canonical_json
from linkdiscovery.ranking import WeightedRanker
from linkdiscovery.ranking.features import (
    clamp01,
    cross_neighborhood_value,
    graph_redundancy,
    hubness_penalty,
    normalize_features,
)
from tests.test_candidates_generator import HubFixture, UnitSpec, build_inputs, fixture_header

if TYPE_CHECKING:
    from linkdiscovery.artifacts import ArtifactStore

SPEC_EXAMPLE_KEYS = frozenset(
    {
        "document_similarity",
        "best_chunk_similarity",
        "support_breadth",
        "lexical_similarity",
        "hubness_penalty",
        "graph_redundancy_penalty",
    }
)


def make_corpus(docs: dict[str, list[tuple[str, str]]]) -> ProcessedCorpus:
    """Corpus with one document per key and one unit per (view, text) entry."""
    documents = []
    for doc_id in sorted(docs):
        counters: dict[str, int] = {}
        units = []
        for view, text in docs[doc_id]:
            position = counters.get(view, 0)
            counters[view] = position + 1
            unit_id = f"{doc_id}:{view}:{position}"
            units.append(
                SemanticUnit(
                    id=unit_id,
                    document_id=doc_id,
                    view=view,
                    section_path=("Body",),
                    region_kinds=(RegionKind.PROSE,),
                    source_spans=(Span(start=position * 100, end=position * 100 + 50),),
                    text=text,
                    token_count=max(1, len(text.split())),
                    content_hash=f"sha256:{unit_id}",
                )
            )
        documents.append(
            ProcessedDocument(document_id=doc_id, revision="rev-1", units=tuple(units))
        )
    return ProcessedCorpus(
        header=fixture_header(),
        preprocessing_fingerprint="sha256:pre",
        documents=tuple(documents),
    )


def base_features(**overrides: float) -> dict[str, float]:
    features = {
        "document_similarity": 0.8,
        "title_similarity": 0.5,
        "best_chunk_similarity": 0.85,
        "top_r_mean_similarity": 0.8,
        "support_breadth": 0.5,
        "source_chunk_count": 3.0,
        "target_chunk_count": 3.0,
        "source_token_count": 300.0,
        "target_token_count": 280.0,
        "lexical_similarity": 0.15,
        "graph_distance": 6.0,
        "common_neighbor_count": 0.0,
        "hubness_source": 0.3,
        "hubness_target": 0.3,
        "csls_similarity": 0.8,
        "csls_best_chunk_similarity": 0.9,
        "near_duplicate_probability": 0.0,
        "directional_similarity_source_to_target": 0.5,
        "directional_similarity_target_to_source": 0.5,
    }
    features.update(overrides)
    return features


def make_pair(
    source: str,
    target: str,
    *,
    features: dict[str, float] | None = None,
    matches: tuple[UnitMatch, ...] | None = None,
) -> CandidatePair:
    if matches is None:
        matches = (
            UnitMatch(
                source_unit_id=f"{source}:section:0",
                target_unit_id=f"{target}:section:0",
                view="section",
                similarity=0.85,
            ),
        )
    return CandidatePair(
        source_document_id=source,
        target_document_id=target,
        matches=matches,
        features=features if features is not None else base_features(),
    )


def make_candidates(*pairs: CandidatePair) -> CandidateSet:
    return CandidateSet(header=fixture_header(), pairs=pairs)


def default_corpus() -> ProcessedCorpus:
    return make_corpus(
        {
            "doc-a": [("document", "alpha overview"), ("section", "alpha body text")],
            "doc-b": [("document", "beta overview"), ("section", "beta body text")],
        }
    )


def by_pair(proposals: ProposalSet, source: str, target: str) -> LinkProposal:
    for proposal in proposals.proposals:
        if (proposal.source_document_id, proposal.target_document_id) == (source, target):
            return proposal
    raise AssertionError(f"proposal ({source!r}, {target!r}) not found")


def test_filters_pair_referencing_absent_document() -> None:
    ranker = WeightedRanker(default_corpus())
    proposals = ranker.rank(make_candidates(make_pair("doc-a", "doc-zz")), RankingConfig())
    assert proposals.proposals == ()


def test_filters_pair_with_empty_document() -> None:
    corpus = make_corpus(
        {
            "doc-a": [("section", "alpha body text")],
            "doc-e": [("section", "   ")],
        }
    )
    ranker = WeightedRanker(corpus)
    proposals = ranker.rank(make_candidates(make_pair("doc-a", "doc-e")), RankingConfig())
    assert proposals.proposals == ()


def test_filters_near_duplicates_above_threshold_only() -> None:
    ranker = WeightedRanker(default_corpus())
    dropped = make_pair("doc-a", "doc-b", features=base_features(near_duplicate_probability=0.99))
    proposals = ranker.rank(make_candidates(dropped), RankingConfig())
    assert proposals.proposals == ()  # dedup is a different action than linking
    kept = make_pair("doc-a", "doc-b", features=base_features(near_duplicate_probability=0.98))
    proposals = ranker.rank(make_candidates(kept), RankingConfig())
    assert len(proposals.proposals) == 1


def test_minimum_relatedness_filter() -> None:
    ranker = WeightedRanker(default_corpus())
    candidates = make_candidates(make_pair("doc-a", "doc-b"))
    assert ranker.rank(candidates, RankingConfig(minimum_relatedness=0.99)).proposals == ()
    assert ranker.rank(candidates, RankingConfig(minimum_relatedness=0.1)).proposals


def test_score_matches_spec_formula() -> None:
    raw = base_features()
    config = RankingConfig()
    ranker = WeightedRanker(default_corpus())
    proposal = ranker.rank(
        make_candidates(make_pair("doc-a", "doc-b", features=dict(raw))), config
    ).proposals[0]
    norms = normalize_features(raw)
    weights = config.weights
    bridge = cross_neighborhood_value(norms["csls_similarity_norm"], raw["graph_distance"])
    expected = clamp01(
        weights["w_document"] * norms["csls_similarity_norm"]
        + weights["w_local"] * norms["best_chunk_similarity_norm"]
        + weights["w_breadth"] * norms["support_breadth_norm"]
        + weights["w_lexical"] * norms["lexical_similarity_norm"]
        + weights["w_bridge"] * bridge
        - weights["w_hub"] * hubness_penalty(raw["hubness_source"], raw["hubness_target"])
        - weights["w_duplicate"] * norms["near_duplicate_probability_norm"]
        - weights["w_redundancy"] * graph_redundancy(raw["graph_distance"])
    )
    assert proposal.score == pytest.approx(expected)
    assert 0.0 <= proposal.score <= 1.0


def test_proposal_carries_spec_keys_raw_norms_and_estimates() -> None:
    ranker = WeightedRanker(default_corpus())
    proposal = ranker.rank(make_candidates(make_pair("doc-a", "doc-b")), RankingConfig()).proposals[
        0
    ]
    assert set(proposal.features) >= SPEC_EXAMPLE_KEYS
    assert "document_similarity_norm" in proposal.features
    assert "csls_similarity_norm" in proposal.features
    for estimate in ("relatedness", "usefulness", "missingness"):
        assert 0.0 <= proposal.features[estimate] <= 1.0
    # The document term is CSLS-corrected but the raw similarity is preserved.
    assert proposal.features["document_similarity"] == base_features()["document_similarity"]
    assert proposal.existing_relationship is False
    assert proposal.review.status == "unreviewed"
    assert proposal.ranking_version


def test_missingness_declines_with_graph_proximity() -> None:
    ranker = WeightedRanker(default_corpus())

    def missingness(distance: float) -> float:
        pair = make_pair("doc-a", "doc-b", features=base_features(graph_distance=distance))
        return (
            ranker.rank(make_candidates(pair), RankingConfig()).proposals[0].features["missingness"]
        )

    assert missingness(6.0) == pytest.approx(1.0)
    assert missingness(4.0) == pytest.approx(0.65)
    assert missingness(2.0) == pytest.approx(0.3)


def test_direction_from_section_placement_evidence() -> None:
    ranker = WeightedRanker(default_corpus())

    def direction(forward: float, backward: float) -> str:
        pair = make_pair(
            "doc-a",
            "doc-b",
            features=base_features(
                directional_similarity_source_to_target=forward,
                directional_similarity_target_to_source=backward,
            ),
        )
        return ranker.rank(make_candidates(pair), RankingConfig()).proposals[0].direction

    assert direction(0.9, 0.5) == "source-to-target"
    assert direction(0.5, 0.9) == "target-to-source"
    assert direction(0.7, 0.69) == "undirected"  # within epsilon


def test_direction_undirected_without_section_evidence() -> None:
    ranker = WeightedRanker(default_corpus())
    pair = make_pair(
        "doc-a",
        "doc-b",
        features=base_features(
            directional_similarity_source_to_target=0.9,
            directional_similarity_target_to_source=0.1,
        ),
        matches=(
            UnitMatch(
                source_unit_id="doc-a:document:0",
                target_unit_id="doc-b:document:0",
                view="document",
                similarity=0.9,
            ),
        ),
    )
    proposal = ranker.rank(make_candidates(pair), RankingConfig()).proposals[0]
    assert proposal.direction == "undirected"


def test_evidence_spans_round_trip_and_cap() -> None:
    corpus = default_corpus()
    ranker = WeightedRanker(corpus)
    matches = tuple(
        UnitMatch(
            source_unit_id="doc-a:section:0",
            target_unit_id="doc-b:section:0",
            view="section",
            similarity=similarity,
        )
        for similarity in (0.9,)
    ) + tuple(
        UnitMatch(
            source_unit_id="doc-a:document:0",
            target_unit_id="doc-b:document:0",
            view="document",
            similarity=similarity,
        )
        for similarity in (0.8, 0.7, 0.6)
    )
    pair = make_pair("doc-a", "doc-b", matches=matches)
    proposal = ranker.rank(make_candidates(pair), RankingConfig()).proposals[0]
    assert len(proposal.evidence) == 3  # capped, strongest first
    assert [item.similarity for item in proposal.evidence] == [0.9, 0.8, 0.7]
    section_unit = next(
        unit
        for document in corpus.documents
        for unit in document.units
        if unit.id == "doc-a:section:0"
    )
    assert proposal.evidence[0].source_spans == section_unit.source_spans


def test_evidence_missing_unit_yields_empty_spans() -> None:
    ranker = WeightedRanker(default_corpus())
    pair = make_pair(
        "doc-a",
        "doc-b",
        matches=(
            UnitMatch(
                source_unit_id="ghost:section:0",
                target_unit_id="doc-b:section:0",
                view="section",
                similarity=0.95,
            ),
        ),
    )
    proposal = ranker.rank(make_candidates(pair), RankingConfig()).proposals[0]
    assert proposal.evidence[0].source_spans == ()
    assert proposal.evidence[0].target_spans != ()


def _diversity_fixture() -> tuple[WeightedRanker, CandidateSet]:
    corpus = make_corpus(
        {
            "doc-s": [("section", "source note body")],
            "doc-t1": [("section", "shared identical wording example tokens")],
            "doc-t2": [("section", "shared identical wording example tokens")],
            "doc-t3": [("section", "totally different vocabulary elsewhere")],
        }
    )
    candidates = make_candidates(
        make_pair("doc-s", "doc-t1", features=base_features(csls_similarity=0.8)),
        make_pair("doc-s", "doc-t2", features=base_features(csls_similarity=0.6)),
        make_pair("doc-s", "doc-t3", features=base_features(csls_similarity=0.4)),
    )
    return WeightedRanker(corpus), candidates


def test_mmr_reorders_presentation_but_not_membership() -> None:
    ranker, candidates = _diversity_fixture()
    plain = ranker.rank(candidates, RankingConfig(diversity=0.0))
    diverse = ranker.rank(candidates, RankingConfig(diversity=0.8))
    order = lambda proposals: [p.target_document_id for p in proposals.proposals]  # noqa: E731
    assert order(plain) == ["doc-t1", "doc-t2", "doc-t3"]
    assert order(diverse) == ["doc-t1", "doc-t3", "doc-t2"]  # near-duplicate target demoted
    members = lambda proposals: {  # noqa: E731
        (p.source_document_id, p.target_document_id) for p in proposals.proposals
    }
    assert members(plain) == members(diverse)


def test_results_per_document_is_a_presentation_cap() -> None:
    ranker, candidates = _diversity_fixture()
    proposals = ranker.rank(candidates, RankingConfig(diversity=0.8, results_per_document=2))
    assert len(proposals.proposals) == 2
    assert [p.target_document_id for p in proposals.proposals] == ["doc-t1", "doc-t3"]


def test_ranks_are_contiguous_and_one_based() -> None:
    ranker, candidates = _diversity_fixture()
    proposals = ranker.rank(candidates, RankingConfig())
    assert [p.rank for p in proposals.proposals] == list(range(1, len(proposals.proposals) + 1))


def _calibration_fixture() -> tuple[WeightedRanker, CandidateSet]:
    docs: dict[str, list[tuple[str, str]]] = {}
    pairs = []
    for index in range(24):
        source, target = f"doc-a{index:02d}", f"doc-b{index:02d}"
        docs[source] = [("section", f"source text {index} alpha")]
        docs[target] = [("section", f"target text {index} beta")]
        pairs.append(
            make_pair(
                source,
                target,
                features=base_features(
                    document_similarity=0.9 - 0.02 * index,
                    best_chunk_similarity=0.9 - 0.02 * index,
                    top_r_mean_similarity=0.85 - 0.02 * index,
                    csls_similarity=0.6 - 0.02 * index,
                ),
            )
        )
    return WeightedRanker(make_corpus(docs)), make_candidates(*pairs)


def test_confidence_calibrates_to_observed_acceptance() -> None:
    ranker, candidates = _calibration_fixture()
    config = RankingConfig()
    baseline = ranker.rank(candidates, config)
    ordered = sorted(
        baseline.proposals,
        key=lambda p: -(p.features["relatedness"] * p.features["usefulness"]),
    )
    decisions = tuple(
        ReviewDecision(
            proposal_id=proposal.id,
            decision=DecisionKind.ACCEPT if position < 12 else DecisionKind.REJECT,
        )
        for position, proposal in enumerate(ordered)
    )
    feedback = ReviewHistory(header=fixture_header(), decisions=decisions)
    calibrated = ranker.rank(candidates, config, feedback)
    confidence = {p.id: p.confidence for p in calibrated.proposals}
    for position, proposal in enumerate(ordered):
        if position < 12:
            assert confidence[proposal.id] is Confidence.HIGH
        else:
            assert confidence[proposal.id] is Confidence.LOW
    assert [p.confidence for p in baseline.proposals] != [
        p.confidence for p in calibrated.proposals
    ]


def test_confidence_falls_back_to_fixed_bands_below_min_decisions() -> None:
    ranker, candidates = _calibration_fixture()
    config = RankingConfig()
    baseline = ranker.rank(candidates, config)
    decisions = tuple(
        ReviewDecision(proposal_id=proposal.id, decision=DecisionKind.ACCEPT)
        for proposal in baseline.proposals[:5]
    )
    feedback = ReviewHistory(header=fixture_header(), decisions=decisions)
    sparse = ranker.rank(candidates, config, feedback)
    assert [p.confidence for p in sparse.proposals] == [p.confidence for p in baseline.proposals]


def test_ranking_is_deterministic_and_byte_identical(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "linkdiscovery.ranking.ranker.utc_now_iso", lambda: "2026-07-31T12:00:00+00:00"
    )
    ranker, candidates = _diversity_fixture()
    config = RankingConfig(diversity=0.5)
    first = ranker.rank(candidates, config)
    second = WeightedRanker(
        make_corpus(
            {
                "doc-s": [("section", "source note body")],
                "doc-t1": [("section", "shared identical wording example tokens")],
                "doc-t2": [("section", "shared identical wording example tokens")],
                "doc-t3": [("section", "totally different vocabulary elsewhere")],
            }
        )
    ).rank(candidates, config)
    assert canonical_json(first.to_dict()) == canonical_json(second.to_dict())
    assert first.proposals  # the comparison is not vacuous


def test_proposal_ids_stable_for_identical_runs() -> None:
    ranker, candidates = _diversity_fixture()
    config = RankingConfig()
    first = ranker.rank(candidates, config)
    second = ranker.rank(candidates, config)
    assert [p.id for p in first.proposals] == [p.id for p in second.proposals]
    other_config = RankingConfig(diversity=0.9)
    changed = ranker.rank(candidates, other_config)
    assert {p.id for p in changed.proposals} != {p.id for p in first.proposals}


def test_end_to_end_hub_demotion(store: ArtifactStore) -> None:
    """Acceptance criterion 7 end to end: the planted hub's raw similarity wins
    but the ranked score and rank prefer the specific match."""
    corpus, index = build_inputs(store, list(HubFixture().specs))
    candidates = DefaultCandidateGenerator(store).generate(
        corpus, index, RelationshipSet(), CandidateConfig()
    )
    proposals = WeightedRanker(corpus).rank(candidates, RankingConfig(diversity=0.0))
    hub_proposal = by_pair(proposals, "hub", "src")
    specific_proposal = by_pair(proposals, "src", "tgt")
    assert (
        hub_proposal.features["document_similarity"]
        > specific_proposal.features["document_similarity"]
    )
    assert specific_proposal.score > hub_proposal.score
    assert specific_proposal.rank < hub_proposal.rank
    assert specific_proposal.features["hubness_penalty"] < hub_proposal.features["hubness_penalty"]


def test_end_to_end_direction_from_generator_features(store: ArtifactStore) -> None:
    specs = [
        UnitSpec("doc-alpha", "document", (1.0, 0.0, 0.0, 0.0), "alpha overview"),
        UnitSpec("doc-alpha", "section", (0.0, 1.0, 0.0, 0.0), "alpha section about beta topic"),
        UnitSpec("doc-beta", "document", (0.0, 0.98, 0.2, 0.0), "beta topic overview"),
        UnitSpec("doc-beta", "section", (0.0, 0.0, 0.0, 1.0), "beta appendix"),
    ]
    corpus, index = build_inputs(store, specs)
    candidates = DefaultCandidateGenerator(store).generate(
        corpus, index, RelationshipSet(), CandidateConfig()
    )
    proposals = WeightedRanker(corpus).rank(candidates, RankingConfig())
    proposal = by_pair(proposals, "doc-alpha", "doc-beta")
    # doc-alpha's section is the placement evidence pointing at doc-beta.
    assert proposal.direction == "source-to-target"
