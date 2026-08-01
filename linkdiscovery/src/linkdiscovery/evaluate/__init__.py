"""Evaluation and calibration stage: weak supervision, metrics, stability.

Implements the SPEC "Evaluation and calibration" section:
:mod:`linkdiscovery.evaluate.holdout` hides a stratified sample of existing
links, :mod:`linkdiscovery.evaluate.metrics` measures held-out recovery and
reviewer quality, and :mod:`linkdiscovery.evaluate.stability` compares
rankings across runs or devices (SPEC acceptance criterion 11). Every
function is a pure, deterministic function over contract types.
"""

from linkdiscovery.evaluate.holdout import DEGREE_BUCKETS, degree_bucket, split_relationships
from linkdiscovery.evaluate.metrics import (
    recovery_by_degree,
    recovery_metrics,
    reviewer_precision_at_k,
)
from linkdiscovery.evaluate.stability import rank_agreement

__all__ = [
    "DEGREE_BUCKETS",
    "degree_bucket",
    "rank_agreement",
    "recovery_by_degree",
    "recovery_metrics",
    "reviewer_precision_at_k",
    "split_relationships",
]
