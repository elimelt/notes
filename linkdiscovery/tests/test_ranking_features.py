"""Normalization and derived-feature tests for the ranking stage."""

from __future__ import annotations

import math

import pytest

from linkdiscovery.ranking.features import (
    NORMALIZATION_CONSTANTS,
    NORMALIZATION_VERSION,
    clamp01,
    cross_neighborhood_value,
    graph_redundancy,
    hubness_penalty,
    normalize_features,
)


def test_clamp01_bounds() -> None:
    assert clamp01(-0.5) == 0.0
    assert clamp01(0.25) == 0.25
    assert clamp01(1.5) == 1.0


def test_normalize_features_known_values() -> None:
    raw = {
        "document_similarity": 0.8,
        "lexical_similarity": 0.25,
        "csls_similarity": 0.5,
        "graph_distance": 3.0,
        "common_neighbor_count": 0.0,
        "source_token_count": 8192.0,
        "support_breadth": 1.4,
        "hubness_source": -0.2,
    }
    normalized = normalize_features(raw)
    assert normalized["document_similarity_norm"] == 0.8
    assert normalized["lexical_similarity_norm"] == pytest.approx(0.5)  # 0.25 / 0.5
    assert normalized["csls_similarity_norm"] == pytest.approx(0.75)  # (0.5 + 1) / 2
    assert normalized["graph_distance_norm"] == pytest.approx(0.5)  # 3 / 6
    assert normalized["common_neighbor_count_norm"] == 0.0
    assert normalized["source_token_count_norm"] == pytest.approx(1.0)
    assert normalized["support_breadth_norm"] == 1.0  # clamped
    assert normalized["hubness_source_norm"] == 0.0  # clamped


def test_normalize_features_defaults_missing_keys_to_zero() -> None:
    normalized = normalize_features({})
    assert normalized["document_similarity_norm"] == 0.0
    assert normalized["csls_similarity_norm"] == pytest.approx(0.5)  # (0 + 1) / 2
    assert all(0.0 <= value <= 1.0 for value in normalized.values())
    assert all(key.endswith("_norm") for key in normalized)


def test_normalize_features_log_squash_counts() -> None:
    normalized = normalize_features({"common_neighbor_count": 4.0})
    expected = math.log1p(4.0) / math.log1p(NORMALIZATION_CONSTANTS["common_neighbor_count_cap"])
    assert normalized["common_neighbor_count_norm"] == pytest.approx(expected)


def test_graph_redundancy_piecewise() -> None:
    assert graph_redundancy(0.0) == 1.0
    assert graph_redundancy(1.0) == 1.0
    assert graph_redundancy(2.0) == 0.7
    assert graph_redundancy(3.0) == 0.3
    assert graph_redundancy(4.0) == 0.1
    assert graph_redundancy(5.0) == 0.0
    assert graph_redundancy(6.0) == 0.0  # unreachable is not redundant


def test_cross_neighborhood_value_gated_by_distance() -> None:
    assert cross_neighborhood_value(0.8, 1.0) == 0.0
    assert cross_neighborhood_value(0.8, 2.0) == 0.0
    assert cross_neighborhood_value(0.8, 3.0) == pytest.approx(0.4)
    assert cross_neighborhood_value(0.8, 4.0) == pytest.approx(0.64)
    assert cross_neighborhood_value(0.8, 5.0) == pytest.approx(0.8)
    assert cross_neighborhood_value(0.8, 6.0) == pytest.approx(0.8)
    assert cross_neighborhood_value(1.7, 6.0) == 1.0  # strength is clamped


def test_hubness_penalty_mean_and_clamp() -> None:
    assert hubness_penalty(0.2, 0.4) == pytest.approx(0.3)
    assert hubness_penalty(1.5, 1.5) == 1.0
    assert hubness_penalty(-1.0, 0.0) == 0.0


def test_normalization_is_versioned() -> None:
    assert NORMALIZATION_VERSION
    assert NORMALIZATION_CONSTANTS["csls_scale"] == 2.0
