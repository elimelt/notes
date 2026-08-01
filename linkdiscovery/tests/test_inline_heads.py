"""Tests for the three learned heads and the TrainedHeads bundle."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("torch")

import torch

from linkdiscovery.errors import ContractError
from linkdiscovery.inline.encode import span_representation_dim
from linkdiscovery.inline.heads import (
    NaturalnessConfig,
    RerankerConfig,
    RetrievalConfig,
    TrainedHeads,
    build_naturalness_head,
    build_pair_features,
    build_reranker_head,
    build_retrieval_head,
    reranker_input_dim,
    retrieval_logits,
)

HIDDEN = 4
FEATURE_NAMES = ("keyphraseness",)
SPAN_DIM = span_representation_dim(HIDDEN, len(FEATURE_NAMES))
PAIR_DIM = reranker_input_dim(SPAN_DIM, HIDDEN, 1)


def make_heads(*, seed: int = 1, encoder_fingerprint: str = "sha256:encoder") -> TrainedHeads:
    naturalness_config = NaturalnessConfig(input_dim=SPAN_DIM, hidden=8)
    retrieval_config = RetrievalConfig(query_dim=SPAN_DIM, target_dim=HIDDEN, projection_dim=6)
    reranker_config = RerankerConfig(input_dim=PAIR_DIM, hidden=8)
    return TrainedHeads(
        naturalness=build_naturalness_head(naturalness_config, seed=seed),
        retrieval=build_retrieval_head(retrieval_config, seed=seed + 1),
        reranker=build_reranker_head(reranker_config, seed=seed + 2),
        naturalness_config=naturalness_config,
        retrieval_config=retrieval_config,
        reranker_config=reranker_config,
        encoder_fingerprint=encoder_fingerprint,
        feature_names=FEATURE_NAMES,
        hidden_size=HIDDEN,
        train_config_fingerprint="sha256:train-config",
        loss_history={"naturalness": (0.5, 0.25)},
    )


class TestConfigs:
    def test_invalid_dimensions_raise(self) -> None:
        with pytest.raises(ContractError, match="NaturalnessConfig"):
            NaturalnessConfig(input_dim=0)
        with pytest.raises(ContractError, match="RetrievalConfig"):
            RetrievalConfig(query_dim=8, target_dim=0)
        with pytest.raises(ContractError, match="RerankerConfig"):
            RerankerConfig(input_dim=8, hidden=0)


class TestHeadModules:
    def test_naturalness_head_shape(self) -> None:
        head = build_naturalness_head(NaturalnessConfig(input_dim=SPAN_DIM), seed=0)
        logits = head(torch.zeros(3, SPAN_DIM))
        assert tuple(logits.shape) == (3, 1)

    def test_reranker_head_shape(self) -> None:
        head = build_reranker_head(RerankerConfig(input_dim=PAIR_DIM), seed=0)
        logits = head(torch.zeros(5, PAIR_DIM))
        assert tuple(logits.shape) == (5, 1)

    def test_retrieval_logits_shape(self) -> None:
        config = RetrievalConfig(query_dim=SPAN_DIM, target_dim=HIDDEN, projection_dim=6)
        head = build_retrieval_head(config, seed=0)
        logits = retrieval_logits(head, torch.zeros(2, SPAN_DIM), torch.zeros(7, HIDDEN))
        assert tuple(logits.shape) == (2, 7)

    def test_seeded_builders_are_deterministic(self) -> None:
        first = build_naturalness_head(NaturalnessConfig(input_dim=SPAN_DIM), seed=3)
        second = build_naturalness_head(NaturalnessConfig(input_dim=SPAN_DIM), seed=3)
        for one, two in zip(first.parameters(), second.parameters(), strict=True):
            assert torch.equal(one, two)


class TestPairFeatures:
    def test_layout_is_exact(self) -> None:
        span_rep = np.arange(SPAN_DIM, dtype=np.float32)
        target = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
        section = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
        row = build_pair_features(
            span_rep, target, section, hidden_size=HIDDEN, hand_features=(7.0,)
        )
        interior = span_rep[2 * HIDDEN : 3 * HIDDEN]
        expected = np.concatenate([span_rep, target, section, interior * target, [7.0]])
        np.testing.assert_array_equal(row, expected.astype(np.float32))
        assert row.shape == (PAIR_DIM,)

    def test_target_width_mismatch_raises(self) -> None:
        span_rep = np.zeros(SPAN_DIM, dtype=np.float32)
        bad_target = np.zeros(HIDDEN + 1, dtype=np.float32)
        section = np.zeros(HIDDEN, dtype=np.float32)
        with pytest.raises(ContractError, match="target_vector"):
            build_pair_features(span_rep, bad_target, section, hidden_size=HIDDEN)

    def test_short_span_rep_raises(self) -> None:
        with pytest.raises(ContractError, match="span_rep"):
            build_pair_features(
                np.zeros(3, dtype=np.float32),
                np.zeros(HIDDEN, dtype=np.float32),
                np.zeros(HIDDEN, dtype=np.float32),
                hidden_size=HIDDEN,
            )

    def test_input_dim_helper_rejects_bad_values(self) -> None:
        with pytest.raises(ContractError, match="reranker_input_dim"):
            reranker_input_dim(0, HIDDEN, 1)


class TestTrainedHeadsScoring:
    def test_score_naturalness_probabilities(self) -> None:
        heads = make_heads()
        probabilities = heads.score_naturalness(np.zeros((3, SPAN_DIM), dtype=np.float32))
        assert probabilities.shape == (3,)
        assert probabilities.dtype == np.float32
        assert bool(((probabilities > 0.0) & (probabilities < 1.0)).all())

    def test_score_targets_full_catalog_softmax_sums_to_one(self) -> None:
        heads = make_heads()
        rng = np.random.default_rng(0)
        reps = rng.normal(size=(4, SPAN_DIM)).astype(np.float32)
        targets = rng.normal(size=(9, HIDDEN)).astype(np.float32)
        probabilities = heads.score_targets(reps, targets)
        assert probabilities.shape == (4, 9)
        np.testing.assert_allclose(probabilities.sum(axis=1), 1.0, rtol=1e-5)

    def test_score_pairs_probabilities(self) -> None:
        heads = make_heads()
        probabilities = heads.score_pairs(np.zeros((2, PAIR_DIM), dtype=np.float32))
        assert probabilities.shape == (2,)
        assert bool(((probabilities > 0.0) & (probabilities < 1.0)).all())

    def test_wrong_input_width_raises(self) -> None:
        heads = make_heads()
        with pytest.raises(ContractError, match="score_naturalness"):
            heads.score_naturalness(np.zeros((3, SPAN_DIM + 1), dtype=np.float32))
        with pytest.raises(ContractError, match="score_targets"):
            heads.score_targets(
                np.zeros((3, SPAN_DIM), dtype=np.float32),
                np.zeros((5, HIDDEN + 2), dtype=np.float32),
            )
        with pytest.raises(ContractError, match="score_pairs"):
            heads.score_pairs(np.zeros(PAIR_DIM, dtype=np.float32))


class TestTrainedHeadsPersistence:
    def test_save_load_round_trip(self, tmp_path: Path) -> None:
        heads = make_heads()
        directory = tmp_path / "heads"
        heads.save(directory)
        loaded = TrainedHeads.load(directory, encoder_fingerprint="sha256:encoder")
        assert loaded.model_version == heads.model_version
        assert loaded.encoder_fingerprint == heads.encoder_fingerprint
        assert loaded.feature_names == FEATURE_NAMES
        assert loaded.hidden_size == HIDDEN
        assert loaded.train_config_fingerprint == heads.train_config_fingerprint
        assert loaded.loss_history == {"naturalness": (0.5, 0.25)}
        rng = np.random.default_rng(1)
        reps = rng.normal(size=(3, SPAN_DIM)).astype(np.float32)
        targets = rng.normal(size=(6, HIDDEN)).astype(np.float32)
        np.testing.assert_allclose(
            loaded.score_naturalness(reps), heads.score_naturalness(reps), rtol=1e-6
        )
        np.testing.assert_allclose(
            loaded.score_targets(reps, targets), heads.score_targets(reps, targets), rtol=1e-6
        )

    def test_load_refuses_encoder_fingerprint_mismatch(self, tmp_path: Path) -> None:
        directory = tmp_path / "heads"
        make_heads().save(directory)
        with pytest.raises(ContractError, match="encoder fingerprint"):
            TrainedHeads.load(directory, encoder_fingerprint="sha256:other-encoder")

    def test_load_without_fingerprint_skips_the_check(self, tmp_path: Path) -> None:
        directory = tmp_path / "heads"
        make_heads().save(directory)
        loaded = TrainedHeads.load(directory)
        assert loaded.encoder_fingerprint == "sha256:encoder"

    def test_load_missing_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ContractError, match="missing"):
            TrainedHeads.load(tmp_path / "nope")

    def test_load_corrupt_metadata_raises(self, tmp_path: Path) -> None:
        directory = tmp_path / "heads"
        make_heads().save(directory)
        (directory / "metadata.json").write_text("{not json", encoding="utf-8")
        with pytest.raises(ContractError, match="unreadable"):
            TrainedHeads.load(directory)

    def test_tampered_weights_fail_integrity_check(self, tmp_path: Path) -> None:
        directory = tmp_path / "heads"
        heads = make_heads()
        heads.save(directory)
        other = make_heads(seed=99)
        torch.save(
            {
                "naturalness": other.naturalness.state_dict(),
                "retrieval": other.retrieval.state_dict(),
                "reranker": other.reranker.state_dict(),
            },
            directory / "weights.pt",
        )
        with pytest.raises(ContractError, match="integrity"):
            TrainedHeads.load(directory)

    def test_model_version_tracks_weights(self) -> None:
        assert make_heads(seed=1).model_version == make_heads(seed=1).model_version
        assert make_heads(seed=1).model_version != make_heads(seed=2).model_version

    def test_model_version_tracks_metadata(self) -> None:
        assert (
            make_heads().model_version
            != make_heads(encoder_fingerprint="sha256:another").model_version
        )
