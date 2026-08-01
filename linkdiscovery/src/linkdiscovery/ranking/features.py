"""Versioned feature normalization and derived ranking features.

Raw candidate features are unnormalized floats; the ranker scores over the
``[0, 1]`` normalizations produced here. The policy is deliberately simple and
fully documented:

- Cosine-shaped raw features (view similarities, hubness, breadth, near-
  duplicate probability) are clamped into ``[0, 1]``.
- CSLS-corrected similarities live in roughly ``[-1, 1]`` for realistic
  inputs, so they are min-max mapped from ``[-csls_offset, csls_scale -
  csls_offset]`` = ``[-1, 1]`` into ``[0, 1]``.
- ``lexical_similarity`` (Jaccard) rarely exceeds 0.5 for distinct documents,
  so it is min-max scaled by ``lexical_similarity_scale`` and clamped.
- Counts are squashed logarithmically: ``log1p(x) / log1p(cap)``.
- ``graph_distance`` is divided by its cap (6 = unreachable).

Every constant lives in :data:`NORMALIZATION_CONSTANTS`, and any change to the
piecewise tables below must bump :data:`NORMALIZATION_VERSION`; both are
fingerprinted into ``ranking_version`` so scores are never compared across
incompatible normalizations.

Derived features (SPEC phase 4):

- ``graph_redundancy``: high when two documents are already connected through
  a short path (``graph_distance <= 2``). It is a *penalty weight*, never an
  exclusion — per the SPEC an indirect path is a ranking signal.
- ``cross_neighborhood_value`` (the ``w_bridge`` term): high when a pair is
  semantically strong *and* graph-distant (``>= 3``), rewarding bridges
  between currently disconnected neighborhoods.
- ``hubness_penalty``: the mean of the two documents' local densities,
  clamped to ``[0, 1]``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "NORMALIZATION_CONSTANTS",
    "NORMALIZATION_VERSION",
    "clamp01",
    "cross_neighborhood_value",
    "graph_redundancy",
    "hubness_penalty",
    "normalize_features",
]

NORMALIZATION_VERSION = "feature-norm-v1"
"""Version of the normalization policy, including the piecewise tables below."""

NORMALIZATION_CONSTANTS: dict[str, float] = {
    "lexical_similarity_scale": 0.5,
    "csls_offset": 1.0,
    "csls_scale": 2.0,
    "graph_distance_cap": 6.0,
    "common_neighbor_count_cap": 16.0,
    "chunk_count_cap": 64.0,
    "token_count_cap": 8192.0,
}
"""Documented normalization constants, fingerprinted into ``ranking_version``."""

_CLAMPED_KEYS = (
    "document_similarity",
    "title_similarity",
    "best_chunk_similarity",
    "top_r_mean_similarity",
    "support_breadth",
    "hubness_source",
    "hubness_target",
    "near_duplicate_probability",
    "directional_similarity_source_to_target",
    "directional_similarity_target_to_source",
)

_CSLS_KEYS = ("csls_similarity", "csls_best_chunk_similarity")

# (upper distance bound, redundancy) rows, scanned in order; beyond -> 0.0.
_REDUNDANCY_STEPS: tuple[tuple[float, float], ...] = (
    (1.0, 1.0),
    (2.0, 0.7),
    (3.0, 0.3),
    (4.0, 0.1),
)

# (upper distance bound, bridge gate) rows, scanned in order; beyond -> 1.0.
_BRIDGE_STEPS: tuple[tuple[float, float], ...] = (
    (2.0, 0.0),
    (3.0, 0.5),
    (4.0, 0.8),
)


def clamp01(value: float) -> float:
    """Clamp ``value`` into the closed interval ``[0, 1]``."""
    return min(max(value, 0.0), 1.0)


def _log_squash(value: float, cap: float) -> float:
    """Map a non-negative count into ``[0, 1]`` with ``log1p(x) / log1p(cap)``."""
    return clamp01(math.log1p(max(value, 0.0)) / math.log1p(cap))


def normalize_features(raw: Mapping[str, float]) -> dict[str, float]:
    """Normalize raw candidate features into ``[0, 1]``, suffixing keys ``_norm``.

    Missing raw features default to ``0.0`` (features are optional and
    discoverable per the SPEC), so the returned vocabulary is always complete
    and reporters can rely on every key being present.
    """
    constants = NORMALIZATION_CONSTANTS

    def get(name: str) -> float:
        return float(raw.get(name, 0.0))

    normalized = {f"{key}_norm": clamp01(get(key)) for key in _CLAMPED_KEYS}
    for key in _CSLS_KEYS:
        normalized[f"{key}_norm"] = clamp01(
            (get(key) + constants["csls_offset"]) / constants["csls_scale"]
        )
    normalized["lexical_similarity_norm"] = clamp01(
        get("lexical_similarity") / constants["lexical_similarity_scale"]
    )
    normalized["graph_distance_norm"] = clamp01(
        get("graph_distance") / constants["graph_distance_cap"]
    )
    normalized["common_neighbor_count_norm"] = _log_squash(
        get("common_neighbor_count"), constants["common_neighbor_count_cap"]
    )
    for key in ("source_chunk_count", "target_chunk_count"):
        normalized[f"{key}_norm"] = _log_squash(get(key), constants["chunk_count_cap"])
    for key in ("source_token_count", "target_token_count"):
        normalized[f"{key}_norm"] = _log_squash(get(key), constants["token_count_cap"])
    return normalized


def graph_redundancy(graph_distance: float) -> float:
    """Redundancy penalty weight: high when a short indirect path already exists.

    Piecewise by hop count: ``<=1 -> 1.0``, ``2 -> 0.7``, ``3 -> 0.3``,
    ``4 -> 0.1``, ``>=5`` (including unreachable) ``-> 0.0``. A penalty, never
    an exclusion: a direct link can still win when its semantic evidence
    outweighs the redundancy term.
    """
    for bound, value in _REDUNDANCY_STEPS:
        if graph_distance <= bound:
            return value
    return 0.0


def cross_neighborhood_value(semantic_strength: float, graph_distance: float) -> float:
    """The ``w_bridge`` feature: semantic strength gated by graph distance.

    Zero at distance ``<= 2`` (the neighborhoods already touch), then
    ``3 -> 0.5``, ``4 -> 0.8``, ``>= 5`` (including unreachable) ``-> 1.0``
    times the clamped semantic strength, so only semantically strong pairs
    earn the bridge bonus.
    """
    strength = clamp01(semantic_strength)
    for bound, gate in _BRIDGE_STEPS:
        if graph_distance <= bound:
            return strength * gate
    return strength


def hubness_penalty(hubness_source: float, hubness_target: float) -> float:
    """Mean of the two documents' local densities, clamped into ``[0, 1]``."""
    return clamp01((hubness_source + hubness_target) / 2.0)
