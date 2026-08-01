"""Nearest-neighbor retrieval backends for candidate generation (SPEC phase 1).

Vectors are normalized upstream (the embedding contract records
``normalized=True``), so a dot product *is* the cosine similarity. Exact
search computes blocked matrix products and is memory-bounded: only one
``(block_size, n)`` similarity block exists at a time — the full ``n x n``
matrix is never materialized. The approximate backend wraps ``hnswlib``
behind a lazy import; the SPEC requires approximate indexes to use
deterministic construction where supported, so the index is built
single-threaded, in row order, from a fixed seed, and the effective
construction parameters are returned for the run manifest.

Both backends share one deterministic tie-breaking policy: neighbors are
ordered by similarity descending, then table unit ID ascending.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

import numpy as np

from linkdiscovery.errors import CandidateError

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from linkdiscovery.config import CandidateConfig
    from linkdiscovery.embed.vectors import VectorTable

__all__ = [
    "AUTO_BACKEND_THRESHOLD",
    "HNSW_EF_CONSTRUCTION",
    "HNSW_M",
    "HNSW_SEED",
    "exact_top_k",
    "hnsw_top_k",
    "select_backend",
]

AUTO_BACKEND_THRESHOLD = 50_000
"""Unit count at which the ``auto`` backend switches from exact to hnsw."""

HNSW_M = 16
"""hnswlib graph degree (``M``): links per node, fixed for determinism."""

HNSW_EF_CONSTRUCTION = 200
"""hnswlib construction beam width (``ef_construction``), fixed for determinism."""

HNSW_SEED = 42
"""hnswlib level-generator seed, fixed for deterministic construction."""

_EXPLICIT_BACKENDS = frozenset({"exact", "hnsw"})


def _row_top_k(
    similarities: NDArray[np.float32],
    unit_ids: tuple[str, ...],
    k: int,
    exclude_row: int | None,
) -> list[tuple[int, float]]:
    """Deterministic top-k for one query row.

    Ties are resolved exactly: the k-th largest similarity is used as a
    threshold, every row at or above it is collected, and the collection is
    sorted by (similarity desc, unit id asc) before truncation. This removes
    any dependence on ``argpartition`` boundary order.
    """
    n = similarities.shape[0]
    if exclude_row is not None:
        similarities = similarities.copy()
        similarities[exclude_row] = -np.inf
    effective = n - (1 if exclude_row is not None else 0)
    limit = min(k, effective)
    if limit <= 0:
        return []
    kth = np.partition(similarities, n - limit)[n - limit]
    candidates = np.flatnonzero(similarities >= kth)
    entries = sorted(
        (-float(similarities[j]), unit_ids[j], int(j))
        for j in candidates
        if np.isfinite(similarities[j])
    )
    return [(row, -negated) for negated, _, row in entries[:limit]]


def exact_top_k(
    table: VectorTable,
    k: int,
    *,
    query: VectorTable | None = None,
    block_size: int = 1024,
) -> list[list[tuple[int, float]]]:
    """Blocked exact cosine top-k over normalized vectors.

    Returns one neighbor list per query row (``query`` defaults to ``table``
    itself, in which case each row's self-match is excluded). Each neighbor is
    a ``(table_row, similarity)`` pair ordered by similarity descending with
    unit-ID-ascending tie-breaking. Memory is bounded by ``block_size``: at
    most one ``(block_size, len(table))`` block of similarities exists at a
    time. Raises :class:`~linkdiscovery.errors.CandidateError` on invalid
    ``k``/``block_size`` or a dimension mismatch between query and table.
    """
    if k < 1:
        raise CandidateError(f"exact_top_k requires k >= 1, got {k}")
    if block_size < 1:
        raise CandidateError(f"exact_top_k requires block_size >= 1, got {block_size}")
    self_mode = query is None or query is table
    queries = table if query is None else query
    if len(queries) and len(table) and queries.dimensions != table.dimensions:
        raise CandidateError(
            f"query vectors have {queries.dimensions} dimensions but the table has "
            f"{table.dimensions}; the tables come from different embedding runs"
        )
    results: list[list[tuple[int, float]]] = []
    if len(table) == 0:
        return [[] for _ in range(len(queries))]
    for start in range(0, len(queries), block_size):
        stop = min(start + block_size, len(queries))
        block = queries.matrix[start:stop] @ table.matrix.T
        for offset in range(stop - start):
            row = start + offset
            exclude = row if self_mode else None
            results.append(_row_top_k(block[offset], table.unit_ids, k, exclude))
    return results


def _load_hnswlib() -> Any:
    """Import ``hnswlib`` lazily, with an actionable error when missing."""
    try:
        return importlib.import_module("hnswlib")
    except ImportError as exc:
        raise CandidateError(
            "the 'hnsw' retrieval backend requires the optional dependency 'hnswlib'; "
            "install it with the 'ann' extra: pip install 'linkdiscovery[ann]' "
            "(or: uv sync --extra ann)"
        ) from exc


def hnsw_top_k(
    table: VectorTable,
    k: int,
    *,
    query: VectorTable | None = None,
    ef_search: int | None = None,
) -> tuple[list[list[tuple[int, float]]], dict[str, int | str]]:
    """Approximate cosine top-k via hnswlib, plus the effective index parameters.

    Same result shape and tie-breaking as :func:`exact_top_k`; additionally
    returns a params dict (space, M, ef_construction, ef_search, seed) for the
    run manifest, because approximate construction parameters must be
    recorded. Construction is deterministic: fixed seed, single-threaded,
    row-order insertion. Raises :class:`~linkdiscovery.errors.CandidateError`
    when ``hnswlib`` is not installed or ``k < 1``.
    """
    if k < 1:
        raise CandidateError(f"hnsw_top_k requires k >= 1, got {k}")
    hnswlib = _load_hnswlib()
    self_mode = query is None or query is table
    queries = table if query is None else query
    fetch = min(len(table), k + (1 if self_mode else 0))
    effective_ef = max(ef_search if ef_search is not None else 2 * k + 16, fetch, 64)
    params: dict[str, int | str] = {
        "backend": "hnsw",
        "space": "ip",
        "m": HNSW_M,
        "ef_construction": HNSW_EF_CONSTRUCTION,
        "ef_search": effective_ef,
        "seed": HNSW_SEED,
    }
    if len(table) == 0 or len(queries) == 0 or fetch == 0:
        return [[] for _ in range(len(queries))], params
    index = hnswlib.Index(space="ip", dim=table.dimensions)
    index.init_index(
        max_elements=len(table),
        M=HNSW_M,
        ef_construction=HNSW_EF_CONSTRUCTION,
        random_seed=HNSW_SEED,
    )
    index.set_num_threads(1)
    index.add_items(table.matrix, np.arange(len(table)))
    index.set_ef(effective_ef)
    labels, distances = index.knn_query(queries.matrix, k=fetch, num_threads=1)
    results: list[list[tuple[int, float]]] = []
    for row in range(len(queries)):
        entries: list[tuple[float, str, int]] = []
        for label, distance in zip(labels[row], distances[row], strict=True):
            neighbor = int(label)
            if self_mode and neighbor == row:
                continue
            similarity = 1.0 - float(distance)
            entries.append((-similarity, table.unit_ids[neighbor], neighbor))
        entries.sort()
        results.append([(neighbor, -negated) for negated, _, neighbor in entries[:k]])
    return results, params


def select_backend(config: CandidateConfig, unit_count: int) -> str:
    """Resolve the retrieval backend for a corpus of ``unit_count`` units.

    ``"auto"`` selects exact search below :data:`AUTO_BACKEND_THRESHOLD` units
    and hnsw at or above it (an all-pairs scan past that size exceeds the time
    and memory budget); explicit backend names pass through. Raises
    :class:`~linkdiscovery.errors.CandidateError` on an unknown backend, which
    indicates a config built outside the strict parser.
    """
    if config.backend == "auto":
        return "exact" if unit_count < AUTO_BACKEND_THRESHOLD else "hnsw"
    if config.backend not in _EXPLICIT_BACKENDS:
        allowed = ", ".join(sorted(_EXPLICIT_BACKENDS | {"auto"}))
        raise CandidateError(
            f"unknown candidate backend {config.backend!r}; expected one of: {allowed}"
        )
    return config.backend
