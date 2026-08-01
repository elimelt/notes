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
from linkdiscovery.inline.heads import TrainedHeads
from linkdiscovery.inline.records import (
    SCHEMA_VERSION,
    AuditItem,
    AuditLabel,
    AuditSample,
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
    mine_hard_negatives,
    naturalness_training_arrays,
    reranker_positive_examples,
    retrieval_training_arrays,
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
