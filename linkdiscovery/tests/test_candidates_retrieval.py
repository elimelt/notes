"""Retrieval backend tests: exact blocked top-k, hnsw parity, backend selection."""

from __future__ import annotations

import importlib

import numpy as np
import pytest

from linkdiscovery.candidates.retrieval import (
    AUTO_BACKEND_THRESHOLD,
    exact_top_k,
    hnsw_top_k,
    select_backend,
)
from linkdiscovery.config import CandidateConfig
from linkdiscovery.embed.vectors import VectorTable
from linkdiscovery.errors import CandidateError


def normalized(rows: list[list[float]]) -> np.ndarray:
    matrix = np.asarray(rows, dtype=np.float64)
    return (matrix / np.linalg.norm(matrix, axis=1, keepdims=True)).astype(np.float32)


def make_table(ids: list[str], rows: list[list[float]]) -> VectorTable:
    return VectorTable(ids, normalized(rows))


def test_exact_planted_nearest_neighbor_found() -> None:
    table = make_table(
        ["u-a", "u-b", "u-c", "u-d"],
        [[1.0, 0.0, 0.0], [0.95, 0.31, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    )
    results = exact_top_k(table, 1)
    assert results[0][0][0] == 1  # u-b is planted next to u-a
    assert results[1][0][0] == 0
    assert results[0][0][1] == pytest.approx(0.95, abs=1e-2)


def test_exact_excludes_self_when_query_is_table() -> None:
    table = make_table(["u-a", "u-b"], [[1.0, 0.0], [0.9, 0.44]])
    for row, neighbors in enumerate(exact_top_k(table, 5)):
        assert all(index != row for index, _ in neighbors)
        assert len(neighbors) == 1  # only one other unit exists


def test_exact_separate_query_keeps_identical_match() -> None:
    table = make_table(["u-a", "u-b"], [[1.0, 0.0], [0.0, 1.0]])
    query = make_table(["q-0"], [[1.0, 0.0]])
    results = exact_top_k(table, 2, query=query)
    assert results == [[(0, pytest.approx(1.0)), (1, pytest.approx(0.0, abs=1e-6))]]


def test_exact_tie_break_by_unit_id_ascending() -> None:
    table = make_table(
        ["u-query", "u-bbb", "u-aaa"],
        [[1.0, 0.0, 0.0], [0.6, 0.8, 0.0], [0.6, 0.0, 0.8]],
    )
    results = exact_top_k(table, 1)
    # Both neighbors have similarity 0.6 to the query; "u-aaa" (row 2) wins.
    assert results[0] == [(2, pytest.approx(0.6, abs=1e-6))]


def test_exact_blocked_matches_unblocked() -> None:
    rng = np.random.RandomState(7)
    matrix = rng.randn(9, 6)
    table = VectorTable(
        [f"u-{i:02d}" for i in range(9)],
        (matrix / np.linalg.norm(matrix, axis=1, keepdims=True)).astype(np.float32),
    )
    whole = exact_top_k(table, 3)
    blocked = exact_top_k(table, 3, block_size=2)
    assert [[i for i, _ in row] for row in whole] == [[i for i, _ in row] for row in blocked]
    for row_a, row_b in zip(whole, blocked, strict=True):
        for (_, sim_a), (_, sim_b) in zip(row_a, row_b, strict=True):
            assert sim_a == pytest.approx(sim_b, abs=1e-6)


def test_exact_k_larger_than_table_returns_all_others() -> None:
    table = make_table(["u-a", "u-b", "u-c"], [[1.0, 0.0], [0.9, 0.44], [0.0, 1.0]])
    results = exact_top_k(table, 50)
    assert all(len(neighbors) == 2 for neighbors in results)


def test_exact_rejects_invalid_arguments() -> None:
    table = make_table(["u-a"], [[1.0, 0.0]])
    with pytest.raises(CandidateError, match="k >= 1"):
        exact_top_k(table, 0)
    with pytest.raises(CandidateError, match="block_size"):
        exact_top_k(table, 1, block_size=0)


def test_exact_rejects_dimension_mismatch() -> None:
    table = make_table(["u-a"], [[1.0, 0.0]])
    query = make_table(["q-0"], [[1.0, 0.0, 0.0]])
    with pytest.raises(CandidateError, match="dimensions"):
        exact_top_k(table, 1, query=query)


def test_select_backend_auto_switches_on_threshold() -> None:
    config = CandidateConfig(backend="auto")
    assert select_backend(config, AUTO_BACKEND_THRESHOLD - 1) == "exact"
    assert select_backend(config, AUTO_BACKEND_THRESHOLD) == "hnsw"


def test_select_backend_explicit_passthrough() -> None:
    assert select_backend(CandidateConfig(backend="exact"), 10**6) == "exact"
    assert select_backend(CandidateConfig(backend="hnsw"), 3) == "hnsw"


def test_select_backend_unknown_backend_raises() -> None:
    with pytest.raises(CandidateError, match="unknown candidate backend"):
        select_backend(CandidateConfig(backend="bogus"), 10)


def test_hnsw_missing_dependency_names_the_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = importlib.import_module

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "hnswlib":
            raise ImportError("No module named 'hnswlib'")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(importlib, "import_module", fake_import)
    table = make_table(["u-a"], [[1.0, 0.0]])
    with pytest.raises(CandidateError, match=r"linkdiscovery\[ann\]"):
        hnsw_top_k(table, 1)


def test_hnsw_matches_exact_on_small_table() -> None:
    pytest.importorskip("hnswlib")
    rng = np.random.RandomState(3)
    matrix = rng.randn(20, 8)
    table = VectorTable(
        [f"u-{i:02d}" for i in range(20)],
        (matrix / np.linalg.norm(matrix, axis=1, keepdims=True)).astype(np.float32),
    )
    exact = exact_top_k(table, 5)
    approx, params = hnsw_top_k(table, 5)
    assert params["seed"] == 42
    assert params["m"] == 16
    assert params["ef_construction"] == 200
    assert [[i for i, _ in row] for row in approx] == [[i for i, _ in row] for row in exact]
    for row_a, row_b in zip(approx, exact, strict=True):
        for (_, sim_a), (_, sim_b) in zip(row_a, row_b, strict=True):
            assert sim_a == pytest.approx(sim_b, abs=1e-5)


def test_hnsw_deterministic_across_calls() -> None:
    pytest.importorskip("hnswlib")
    rng = np.random.RandomState(11)
    matrix = rng.randn(15, 6)
    table = VectorTable(
        [f"u-{i:02d}" for i in range(15)],
        (matrix / np.linalg.norm(matrix, axis=1, keepdims=True)).astype(np.float32),
    )
    first, params_a = hnsw_top_k(table, 4)
    second, params_b = hnsw_top_k(table, 4)
    assert first == second
    assert params_a == params_b
