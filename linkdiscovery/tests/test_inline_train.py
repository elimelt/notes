"""Tests for training-data assembly, PU discipline, mining, and the loops."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("torch")

from linkdiscovery.contracts.base import ArtifactHeader
from linkdiscovery.contracts.units import Span
from linkdiscovery.errors import ConfigError, ContractError
from linkdiscovery.inline.encode import span_representation_dim
from linkdiscovery.inline.heads import TrainedHeads, build_pair_features
from linkdiscovery.inline.records import (
    SCHEMA_VERSION,
    AuditItem,
    AuditLabel,
    AuditSample,
    InlineReviewDecision,
    LinkRegionKind,
    SpanCandidate,
    Tier,
)
from linkdiscovery.inline.train import (
    SpanRepTable,
    TargetCatalog,
    TrainConfig,
    TrainingData,
    build_training_data,
    confirmed_negative_mask,
    default_pair_hand_features,
    mine_hard_negatives,
    naturalness_training_arrays,
    reranker_positive_examples,
    retrieval_training_arrays,
    review_span_key,
    review_training_examples,
    train_heads,
)

HIDDEN = 8
FEATURE_NAMES = ("keyphraseness",)
SPAN_DIM = span_representation_dim(HIDDEN, len(FEATURE_NAMES))
N_TARGETS = 6
ENCODER_FP = "sha256:test-encoder"


def make_catalog() -> TargetCatalog:
    matrix = np.eye(N_TARGETS, HIDDEN, dtype=np.float32)
    return TargetCatalog(tuple(f"t{i}" for i in range(N_TARGETS)), matrix)


def planted_rep(target_row: int, rng: np.random.Generator) -> np.ndarray:
    """A span rep whose interior block points at the target vector."""
    start = rng.normal(0.0, 0.1, HIDDEN)
    end = rng.normal(0.0, 0.1, HIDDEN)
    interior = np.eye(N_TARGETS, HIDDEN)[target_row] + rng.normal(0.0, 0.05, HIDDEN)
    width = np.zeros(5)
    width[1] = 1.0
    return np.concatenate([start, end, interior, width, [0.5]]).astype(np.float32)


def make_item(
    item_id: str, source_doc: str, target_doc: str, span: Span | None = None
) -> AuditItem:
    return AuditItem(
        id=item_id,
        source_document_id=source_doc,
        target_document_id=target_doc,
        anchor_text="anchor",
        source_span=span,
        region_kind=LinkRegionKind.PROSE,
        context="context",
        anchor_word_count=1,
        topic_family="family",
        strata_key="stratum",
    )


def make_label(item_id: str, tier: Tier, annotator: str = "a") -> AuditLabel:
    return AuditLabel(
        item_id=item_id,
        annotator=annotator,
        target_correct=tier is not Tier.D,
        anchor_natural=tier is Tier.A,
        placement_valid=tier is Tier.A,
        tier=tier,
    )


def make_sample(items: tuple[AuditItem, ...]) -> AuditSample:
    header = ArtifactHeader(
        schema_version=SCHEMA_VERSION,
        run_id="run-train",
        corpus_id="corpus-train",
        created_at="2026-07-31T00:00:00+00:00",
        config_fingerprint="sha256:cfg",
        producer_version="test",
    )
    return AuditSample(header=header, items=items)


def make_candidate(candidate_id: str, doc: str, start: int, end: int) -> SpanCandidate:
    return SpanCandidate(
        id=candidate_id,
        document_id=doc,
        unit_id=None,
        span=Span(start, end),
        text="candidate",
        region_kind=LinkRegionKind.PROSE,
        word_count=1,
    )


def make_rep_table(reps: dict[str, np.ndarray]) -> SpanRepTable:
    return SpanRepTable(
        reps,
        hidden_size=HIDDEN,
        encoder_fingerprint=ENCODER_FP,
        feature_names=FEATURE_NAMES,
    )


def tiered_training_data() -> TrainingData:
    """One item per tier plus confirmed/unconfirmed/overlapping candidates."""
    rng = np.random.default_rng(0)
    items = (
        make_item("item-a", "src", "t0", span=Span(0, 5)),
        make_item("item-b", "src", "t1"),
        make_item("item-c", "src", "t2"),
        make_item("item-d", "src", "t3"),
    )
    labels = [
        make_label("item-a", Tier.A),
        make_label("item-b", Tier.B),
        make_label("item-c", Tier.C),
        make_label("item-d", Tier.D),
    ]
    candidates = {
        "src": [
            make_candidate("cand-overlap", "src", 0, 5),  # same span as item-a: dropped
            make_candidate("cand-low", "src", 10, 15),  # confirmed negative
            make_candidate("cand-high", "src", 20, 25),  # stays pseudo-negative
        ]
    }
    reps = make_rep_table(
        {
            "item-a": planted_rep(0, rng),
            "item-b": planted_rep(1, rng),
            "item-c": planted_rep(2, rng),
            "item-d": planted_rep(3, rng),
            "cand-low": planted_rep(4, rng),
            "cand-high": planted_rep(5, rng),
        }
    )
    return build_training_data(
        labels,
        make_sample(items),
        candidates,
        reps=reps,
        catalog=make_catalog(),
        best_target_scores={"cand-low": 0.05, "cand-high": 0.9},
        confirmed_negative_threshold=0.2,
    )


class TestTierRouting:
    def test_examples_and_overlap_drop(self) -> None:
        data = tiered_training_data()
        keys = {example.key for example in data.examples}
        assert keys == {"item-a", "item-b", "item-c", "item-d", "cand-low", "cand-high"}

    def test_naturalness_labels_per_tier(self) -> None:
        by_key = {example.key: example for example in tiered_training_data().examples}
        assert by_key["item-a"].naturalness_label == 1.0
        assert by_key["item-b"].naturalness_label is None
        assert by_key["item-c"].naturalness_label is None  # C never reaches naturalness
        assert by_key["item-d"].naturalness_label == 0.0
        assert by_key["cand-low"].confirmed_negative
        assert not by_key["cand-high"].confirmed_negative

    def test_naturalness_arrays_and_pu_weights(self) -> None:
        data = tiered_training_data()
        reps, labels, weights, groups = naturalness_training_arrays(data, pi=0.05)
        assert reps.shape == (4, SPAN_DIM)
        np.testing.assert_array_equal(labels, [1.0, 0.0, 0.0, 0.0])
        np.testing.assert_allclose(weights, [1.0, 1.0, 1.0, 0.05])
        assert groups == ("src", "src", "src", "src")

    def test_retrieval_positives_are_tiers_a_b_c(self) -> None:
        reps, positives = retrieval_training_arrays(tiered_training_data())
        assert reps.shape == (3, SPAN_DIM)
        np.testing.assert_array_equal(positives, [0, 1, 2])

    def test_reranker_positives_are_tiers_a_b(self) -> None:
        keys = [example.key for example in reranker_positive_examples(tiered_training_data())]
        assert keys == ["item-a", "item-b"]

    def test_tie_between_annotators_resolves_to_worse_tier(self) -> None:
        rng = np.random.default_rng(1)
        items = (make_item("item-x", "src", "t0"),)
        labels = [
            make_label("item-x", Tier.A, annotator="one"),
            make_label("item-x", Tier.D, annotator="two"),
        ]
        data = build_training_data(
            labels,
            make_sample(items),
            {},
            reps=make_rep_table({"item-x": planted_rep(0, rng)}),
            catalog=make_catalog(),
        )
        assert data.examples[0].tier is Tier.D

    def test_catalog_outside_encoder_space_raises(self) -> None:
        rng = np.random.default_rng(2)
        wide = TargetCatalog(("t0",), np.zeros((1, HIDDEN + 1), dtype=np.float32))
        with pytest.raises(ContractError, match="hidden"):
            build_training_data(
                [make_label("item-a", Tier.A)],
                make_sample((make_item("item-a", "src", "t0"),)),
                {},
                reps=make_rep_table({"item-a": planted_rep(0, rng)}),
                catalog=wide,
            )


def make_decision(
    *,
    engine: str = "learned",
    source: str = "src",
    target: str = "t1",
    start: int = 30,
    end: int | None = None,
    verdict: str = "accept",
    target_ok: bool = True,
    anchor_ok: bool = True,
    reason: str = "good",
    score: float = 0.7,
) -> InlineReviewDecision:
    return InlineReviewDecision(
        engine=engine,
        source_document_id=source,
        span=Span(start, end if end is not None else start + 5),
        anchor_text="anchor",
        target_document_id=target,
        verdict=verdict,
        target_ok=target_ok,
        anchor_ok=anchor_ok,
        placement_ok=verdict == "accept",
        reason=reason,
        note="",
        combined_score=score,
    )


def review_reps(decisions: list[InlineReviewDecision]) -> SpanRepTable:
    rng = np.random.default_rng(7)
    return make_rep_table(
        {review_span_key(decision): planted_rep(0, rng) for decision in decisions}
    )


class TestReviewRouting:
    """Per-head routing of review decisions (deliberately NOT tier semantics)."""

    def test_accept_routes_tier_a_with_anchor_label(self) -> None:
        decision = make_decision(verdict="accept", anchor_ok=True, target="t2")
        [example] = review_training_examples(
            [decision], reps=review_reps([decision]), catalog=make_catalog()
        )
        assert example.tier is Tier.A
        assert example.naturalness_label == 1.0
        assert example.target_index == make_catalog().index_for("t2")
        assert example.key == review_span_key(decision)
        assert example.key.startswith("review:")
        assert example.group == "src"
        assert not example.pseudo_negative

    def test_reject_with_right_target_is_tier_b_labeled_by_anchor(self) -> None:
        natural = make_decision(
            verdict="reject", target_ok=True, anchor_ok=True, reason="bad_placement", start=10
        )
        unnatural = make_decision(
            verdict="reject",
            target_ok=True,
            anchor_ok=False,
            reason="unnatural_anchor",
            start=20,
        )
        examples = review_training_examples(
            [natural, unnatural],
            reps=review_reps([natural, unnatural]),
            catalog=make_catalog(),
        )
        assert [example.tier for example in examples] == [Tier.B, Tier.B]
        # Unlike audit Tier B (excluded from the naturalness head), review
        # decisions carry per-head anchor ground truth: always labeled.
        assert [example.naturalness_label for example in examples] == [1.0, 0.0]

    def test_wrong_target_is_tier_d_pointing_at_the_wrong_target(self) -> None:
        decision = make_decision(
            verdict="reject", target_ok=False, anchor_ok=True, reason="wrong_target", target="t3"
        )
        [example] = review_training_examples(
            [decision], reps=review_reps([decision]), catalog=make_catalog()
        )
        assert example.tier is Tier.D
        # The recorded target IS the wrong one — exactly the (span, wrong
        # target) pair the reranker's Tier-D negative BCE consumes.
        assert example.target_index == make_catalog().index_for("t3")
        assert example.naturalness_label == 1.0

    def test_broken_span_and_unknown_target_are_skipped(self) -> None:
        kept = make_decision(start=10)
        broken = make_decision(start=20, reason="broken_span", verdict="reject", target_ok=False)
        unknown = make_decision(start=40, target="t99")
        examples = review_training_examples(
            [kept, broken, unknown], reps=review_reps([kept]), catalog=make_catalog()
        )
        assert [example.key for example in examples] == [review_span_key(kept)]

    def test_review_heads_routing_table(self) -> None:
        """The full routing matrix over the three head consumers."""
        decisions = [
            make_decision(start=10, verdict="accept", target="t0"),
            make_decision(
                start=20, verdict="reject", target_ok=True, reason="bad_placement", target="t1"
            ),
            make_decision(
                start=30, verdict="reject", target_ok=False, reason="wrong_target", target="t2"
            ),
        ]
        rng = np.random.default_rng(8)
        reps = make_rep_table(
            {
                review_span_key(decision): planted_rep(row, rng)
                for row, decision in enumerate(decisions)
            }
        )
        data = build_training_data(
            [], make_sample(()), {}, reps=reps, catalog=make_catalog(), reviews=decisions
        )
        _, positives = retrieval_training_arrays(data)
        np.testing.assert_array_equal(positives, [0, 1])  # A and B only
        assert [example.target_index for example in reranker_positive_examples(data)] == [0, 1]
        _, labels, weights, _ = naturalness_training_arrays(data, pi=0.05)
        np.testing.assert_array_equal(labels, [1.0, 1.0, 1.0])  # anchor_ok everywhere
        np.testing.assert_array_equal(weights, [1.0, 1.0, 1.0])  # never pi-weighted

    def test_reviewed_spans_are_excluded_from_pu_pseudo_negatives(self) -> None:
        decision = make_decision(start=10, end=15)
        other = make_candidate("cand-free", "src", 40, 45)
        rng = np.random.default_rng(9)
        reps = make_rep_table(
            {
                review_span_key(decision): planted_rep(0, rng),
                "cand-free": planted_rep(4, rng),
            }
        )
        data = build_training_data(
            [],
            make_sample(()),
            {"src": [make_candidate("cand-reviewed", "src", 10, 15), other]},
            reps=reps,
            catalog=make_catalog(),
            reviews=[decision],
        )
        keys = [example.key for example in data.examples]
        # The candidate coinciding with the reviewed span is dropped; the
        # unreviewed candidate stays a PU pseudo-negative.
        assert keys == [review_span_key(decision), "cand-free"]
        assert not data.examples[0].pseudo_negative
        assert data.examples[1].pseudo_negative

    def test_review_examples_append_after_audit_examples(self) -> None:
        rng = np.random.default_rng(10)
        item = make_item("item-a", "src", "t0", span=Span(0, 5))
        decision = make_decision(start=10, end=15)
        reps = make_rep_table(
            {
                "item-a": planted_rep(0, rng),
                review_span_key(decision): planted_rep(1, rng),
            }
        )
        data = build_training_data(
            [make_label("item-a", Tier.A)],
            make_sample((item,)),
            {},
            reps=reps,
            catalog=make_catalog(),
            reviews=[decision],
        )
        assert [example.key for example in data.examples] == [
            "item-a",
            review_span_key(decision),
        ]

    def test_missing_review_rep_is_a_contract_error(self) -> None:
        decision = make_decision()
        with pytest.raises(ContractError, match="no span representation"):
            review_training_examples([decision], reps=make_rep_table({}), catalog=make_catalog())


class TestConfirmedNegativeMask:
    def test_threshold_split(self) -> None:
        scores = np.array([0.1, 0.19, 0.2, 0.5], dtype=np.float32)
        mask = confirmed_negative_mask(scores, threshold=0.2)
        np.testing.assert_array_equal(mask, [True, True, False, False])


class TestMineHardNegatives:
    def test_excludes_positives_and_excluded_targets(self) -> None:
        targets = np.eye(4, dtype=np.float32)
        queries = targets[[0, 1]]
        mined = mine_hard_negatives(queries, targets, np.array([0, 1]), k=2, exclude=(3,))
        assert mined.shape == (2, 2)
        for row, positive in zip(mined, (0, 1), strict=True):
            assert positive not in row
            assert 3 not in row

    def test_nearest_non_positive_comes_first(self) -> None:
        targets = np.array(
            [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]],
            dtype=np.float32,
        )
        mined = mine_hard_negatives(targets[[0]], targets, np.array([0]), k=2)
        np.testing.assert_array_equal(mined, [[1, 2]])

    def test_k_zero_yields_empty(self) -> None:
        targets = np.eye(3, dtype=np.float32)
        mined = mine_hard_negatives(targets[[0]], targets, np.array([0]), k=0)
        assert mined.shape == (1, 0)

    def test_k_too_large_raises(self) -> None:
        targets = np.eye(3, dtype=np.float32)
        with pytest.raises(ContractError, match="k must be between"):
            mine_hard_negatives(targets[[0]], targets, np.array([0]), k=3)

    def test_dimension_mismatch_raises(self) -> None:
        with pytest.raises(ContractError, match="equal widths"):
            mine_hard_negatives(
                np.zeros((1, 3), dtype=np.float32),
                np.zeros((4, 2), dtype=np.float32),
                np.array([0]),
                k=1,
            )


class TestTrainConfig:
    def test_defaults_match_spec_starting_points(self) -> None:
        config = TrainConfig()
        assert config.lr == pytest.approx(1e-3)
        assert config.epochs == 30
        assert config.pi == pytest.approx(0.05)
        assert config.negative_ratio == 6
        assert config.hard_negative_count == 2
        assert config.device == "cpu"

    def test_fingerprint_tracks_values(self) -> None:
        assert TrainConfig().fingerprint() == TrainConfig().fingerprint()
        assert TrainConfig().fingerprint() != TrainConfig(lr=2e-3).fingerprint()

    def test_invalid_values_raise(self) -> None:
        with pytest.raises(ConfigError, match="pi"):
            TrainConfig(pi=0.0)
        with pytest.raises(ConfigError, match="epochs"):
            TrainConfig(epochs=-1)
        with pytest.raises(ConfigError, match="device"):
            TrainConfig(device="tpu")


class TestSpanRepTable:
    def test_wrong_width_raises(self) -> None:
        with pytest.raises(ContractError, match="width"):
            make_rep_table({"x": np.zeros(SPAN_DIM + 1, dtype=np.float32)})

    def test_missing_key_raises(self) -> None:
        table = make_rep_table({"x": np.zeros(SPAN_DIM, dtype=np.float32)})
        assert "x" in table
        assert len(table) == 1
        assert table.dim == SPAN_DIM
        with pytest.raises(ContractError, match="no span representation"):
            table.rep_for("missing")


class TestTargetCatalog:
    def test_duplicate_ids_raise(self) -> None:
        with pytest.raises(ContractError, match="duplicate"):
            TargetCatalog(("t0", "t0"), np.zeros((2, HIDDEN), dtype=np.float32))

    def test_unknown_target_raises(self) -> None:
        with pytest.raises(ContractError, match="no target row"):
            make_catalog().index_for("t99")

    def test_section_matrix_defaults_to_document_vectors(self) -> None:
        catalog = make_catalog()
        np.testing.assert_array_equal(catalog.section_matrix, catalog.matrix)

    def test_section_matrix_shape_mismatch_raises(self) -> None:
        with pytest.raises(ContractError, match="section_matrix"):
            TargetCatalog(
                ("t0",),
                np.zeros((1, HIDDEN), dtype=np.float32),
                np.zeros((2, HIDDEN), dtype=np.float32),
            )


def planted_training_data(n_items: int = 30, n_candidates: int = 4) -> TrainingData:
    """Synthetic Tier-A corpus with a planted retrieval signal."""
    rng = np.random.default_rng(42)
    items = []
    labels = []
    reps: dict[str, np.ndarray] = {}
    for index in range(n_items):
        target_row = index % N_TARGETS
        item_id = f"item-{index}"
        items.append(make_item(item_id, f"doc-{index % 5}", f"t{target_row}"))
        labels.append(make_label(item_id, Tier.A))
        reps[item_id] = planted_rep(target_row, rng)
    candidates = {
        "doc-cand": [
            make_candidate(f"cand-{index}", "doc-cand", index * 10, index * 10 + 5)
            for index in range(n_candidates)
        ]
    }
    for index in range(n_candidates):
        reps[f"cand-{index}"] = planted_rep(rng.integers(N_TARGETS), rng)
    return build_training_data(
        labels,
        make_sample(tuple(items)),
        candidates,
        reps=make_rep_table(reps),
        catalog=make_catalog(),
    )


def retrieval_accuracy(heads: TrainedHeads, data: TrainingData) -> float:
    reps, positives = retrieval_training_arrays(data)
    probabilities = heads.score_targets(reps, data.catalog.matrix)
    np.testing.assert_allclose(probabilities.sum(axis=1), 1.0, rtol=1e-5)
    return float((probabilities.argmax(axis=1) == positives).mean())


def mixed_tier_training_data(n_positives: int = 12, n_tier_d: int = 10) -> TrainingData:
    """Tier-A positives plus Tier-D wrong-target pairs (the review-shaped mix).

    Each Tier-D item's rep points at one target while its recorded
    ``target_index`` is a DIFFERENT (wrong) target — the (span, wrong
    target) pair shape the review harvest supplies in volume.
    """
    rng = np.random.default_rng(21)
    items = []
    labels = []
    reps: dict[str, np.ndarray] = {}
    for index in range(n_positives):
        target_row = index % N_TARGETS
        item_id = f"pos-{index}"
        items.append(make_item(item_id, f"doc-{index % 3}", f"t{target_row}"))
        labels.append(make_label(item_id, Tier.A))
        reps[item_id] = planted_rep(target_row, rng)
    for index in range(n_tier_d):
        wrong_row = (index + 1) % N_TARGETS
        item_id = f"neg-{index}"
        items.append(make_item(item_id, f"doc-{index % 3}", f"t{wrong_row}"))
        labels.append(make_label(item_id, Tier.D))
        reps[item_id] = planted_rep(index % N_TARGETS, rng)
    return build_training_data(
        labels,
        make_sample(tuple(items)),
        {},
        reps=make_rep_table(reps),
        catalog=make_catalog(),
    )


def pair_rows_for_tier(data: TrainingData, tier: Tier) -> np.ndarray:
    """The (span, recorded target) reranker input rows of one tier's examples."""
    catalog = data.catalog
    rows = [
        build_pair_features(
            example.rep,
            catalog.matrix[example.target_index],
            catalog.section_matrix[example.target_index],
            hidden_size=HIDDEN,
            hand_features=default_pair_hand_features(
                example.rep, catalog.matrix[example.target_index], hidden_size=HIDDEN
            ),
        )
        for example in data.examples
        if example.tier is tier
    ]
    return np.stack(rows).astype(np.float32)


class TestTrainHeads:
    def test_learns_planted_retrieval_signal(self) -> None:
        data = planted_training_data()
        untrained = train_heads(data, config=TrainConfig(epochs=0), seed=3)
        assert untrained.loss_history["retrieval"] == ()
        trained = train_heads(data, config=TrainConfig(epochs=40, lr=0.05, batch_size=16), seed=3)
        pre_accuracy = retrieval_accuracy(untrained, data)
        post_accuracy = retrieval_accuracy(trained, data)
        assert post_accuracy > pre_accuracy
        assert post_accuracy >= 0.8
        history = trained.loss_history["retrieval"]
        assert len(history) == 40
        assert history[-1] < history[0]

    def test_metadata_pins_encoder_and_config(self) -> None:
        data = planted_training_data(n_items=6, n_candidates=2)
        config = TrainConfig(epochs=2, batch_size=8)
        heads = train_heads(data, config=config, seed=5)
        assert heads.encoder_fingerprint == ENCODER_FP
        assert heads.feature_names == FEATURE_NAMES
        assert heads.hidden_size == HIDDEN
        assert heads.train_config_fingerprint == config.fingerprint()
        assert set(heads.loss_history) == {"naturalness", "retrieval", "reranker"}
        assert heads.model_version.startswith("sha256:")

    def test_reranker_absolute_scale_survives_tier_d_negatives(self) -> None:
        """Regression: the listwise CE is shift-invariant within each group,
        so a zeros-only per-epoch BCE (Tier-D rows without positive anchors)
        let the optimizer uniformly shift all in-distribution logits down —
        rankings intact, training loss near zero, every absolute sigmoid
        probability collapsed to ~0.0. First observable with the review
        harvest's Tier-D volume (the audit produced zero Tier-D rows). The
        fixed BCE anchors true pairs at 1.0, so positives must clear an
        absolute floor, not merely outrank the wrong-target pairs."""
        data = mixed_tier_training_data()
        heads = train_heads(data, config=TrainConfig(epochs=25, lr=0.05, batch_size=32), seed=13)
        positive_probs = heads.score_pairs(pair_rows_for_tier(data, Tier.A))
        tier_d_probs = heads.score_pairs(pair_rows_for_tier(data, Tier.D))
        assert positive_probs.mean() > tier_d_probs.mean()
        # The absolute floor is what the shift-collapse failure mode broke:
        # the old code scored ~0.0 here while keeping the ordering above.
        assert positive_probs.mean() > 0.5
        assert tier_d_probs.mean() < 0.5

    def test_pu_weighting_downweights_pseudo_negatives(self) -> None:
        data = planted_training_data(n_items=5, n_candidates=10)
        config_low = TrainConfig(epochs=1, batch_size=64, pi=0.05)
        config_high = TrainConfig(epochs=1, batch_size=64, pi=1.0)
        loss_low = train_heads(data, config=config_low, seed=9).loss_history["naturalness"][0]
        loss_high = train_heads(data, config=config_high, seed=9).loss_history["naturalness"][0]
        assert loss_low < loss_high

    def test_deterministic_given_seed(self) -> None:
        data = planted_training_data(n_items=12, n_candidates=3)
        config = TrainConfig(epochs=3, batch_size=8)
        first = train_heads(data, config=config, seed=11)
        second = train_heads(data, config=config, seed=11)
        assert first.loss_history == second.loss_history
        assert first.model_version == second.model_version

    def test_different_seeds_differ(self) -> None:
        data = planted_training_data(n_items=12, n_candidates=3)
        config = TrainConfig(epochs=2, batch_size=8)
        first = train_heads(data, config=config, seed=1)
        second = train_heads(data, config=config, seed=2)
        assert first.model_version != second.model_version

    def test_candidates_only_data_trains_naturalness_only(self) -> None:
        rng = np.random.default_rng(4)
        candidates = {"doc": [make_candidate(f"c{i}", "doc", i * 10, i * 10 + 4) for i in range(3)]}
        reps = make_rep_table({f"c{i}": planted_rep(i, rng) for i in range(3)})
        data = build_training_data(
            [], make_sample(()), candidates, reps=reps, catalog=make_catalog()
        )
        heads = train_heads(data, config=TrainConfig(epochs=2, batch_size=8), seed=0)
        assert heads.loss_history["retrieval"] == ()
        assert heads.loss_history["reranker"] == ()
        assert len(heads.loss_history["naturalness"]) == 2

    def test_round_trip_through_save_load(self, tmp_path: Path) -> None:
        data = planted_training_data(n_items=6, n_candidates=2)
        heads = train_heads(data, config=TrainConfig(epochs=2, batch_size=8), seed=7)
        heads.save(tmp_path / "bundle")
        loaded = TrainedHeads.load(tmp_path / "bundle", encoder_fingerprint=ENCODER_FP)
        reps, _ = retrieval_training_arrays(data)
        np.testing.assert_allclose(
            loaded.score_targets(reps, data.catalog.matrix),
            heads.score_targets(reps, data.catalog.matrix),
            rtol=1e-6,
        )
