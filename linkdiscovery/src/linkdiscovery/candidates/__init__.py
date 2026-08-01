"""Candidate generation stage: high-recall retrieval and pair aggregation.

``retrieval`` provides the exact and approximate nearest-neighbor backends;
``generator`` implements the :class:`~linkdiscovery.interfaces.CandidateGenerator`
protocol on top of them (SPEC "Candidate algorithm" phases 1-3).
"""

from linkdiscovery.candidates.generator import DefaultCandidateGenerator
from linkdiscovery.candidates.retrieval import (
    AUTO_BACKEND_THRESHOLD,
    exact_top_k,
    hnsw_top_k,
    select_backend,
)

__all__ = [
    "AUTO_BACKEND_THRESHOLD",
    "DefaultCandidateGenerator",
    "exact_top_k",
    "hnsw_top_k",
    "select_backend",
]
