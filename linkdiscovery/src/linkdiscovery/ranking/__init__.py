"""Ranking stage: feature normalization, weighted scoring, calibration, diversity.

``features`` holds the versioned normalization and derived-feature policy;
``ranker`` implements the :class:`~linkdiscovery.interfaces.Ranker` protocol
(SPEC "Candidate algorithm" phase 4, "Direction and placement", "Diversity").
"""

from linkdiscovery.ranking.features import (
    NORMALIZATION_CONSTANTS,
    NORMALIZATION_VERSION,
    cross_neighborhood_value,
    graph_redundancy,
    hubness_penalty,
    normalize_features,
)
from linkdiscovery.ranking.ranker import RANKER_VERSION, WeightedRanker

__all__ = [
    "NORMALIZATION_CONSTANTS",
    "NORMALIZATION_VERSION",
    "RANKER_VERSION",
    "WeightedRanker",
    "cross_neighborhood_value",
    "graph_redundancy",
    "hubness_penalty",
    "normalize_features",
]
