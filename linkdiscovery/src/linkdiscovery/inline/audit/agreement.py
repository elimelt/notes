"""Inter-annotator agreement statistics: Cohen's kappa and Krippendorff's alpha.

Pure, hand-verifiable math over nominal labels (numpy only), implementing the
agreement requirements of SPEC-INLINE-LINKING §4: "use two annotators on an
overlapping subset and report Cohen's kappa (two raters, nominal) or
Krippendorff's alpha (handles >2 raters / missing data)". The audit's
go/no-go decision consumes :func:`agreement_report`.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from itertools import combinations

import numpy as np

from linkdiscovery.inline.records import AuditLabel

__all__ = ["agreement_report", "cohen_kappa", "krippendorff_alpha"]

_LABEL_FIELDS = ("target_correct", "anchor_natural", "placement_valid", "tier")
"""The audited judgment fields agreement is reported for."""

_MIN_RATERS = 2
"""A unit contributes to agreement only when at least two annotators labeled it."""


def cohen_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    """Cohen's kappa for two raters over paired nominal labels.

    ``kappa = (p_o - p_e) / (1 - p_e)`` where ``p_o`` is observed agreement
    and ``p_e`` is chance agreement from the raters' marginal distributions.
    Interpretation follows the Landis-Koch bands cited by
    SPEC-INLINE-LINKING §4: 0.41-0.60 moderate, 0.61-0.80 substantial,
    >= 0.81 almost perfect; the audit targets kappa >= 0.6.

    Degenerate cases: empty or unequal-length inputs raise ``ValueError``;
    when chance agreement is 1.0 (both raters constant on the same category)
    the result is 1.0 if observed agreement is also 1.0, else 0.0, so
    perfect agreement on a constant category scores 1.0 instead of 0/0.
    """
    if len(labels_a) != len(labels_b):
        raise ValueError(
            f"cohen_kappa requires equal-length label sequences, "
            f"got {len(labels_a)} and {len(labels_b)}"
        )
    if not labels_a:
        raise ValueError("cohen_kappa requires at least one paired label")
    categories = sorted(set(labels_a) | set(labels_b))
    index = {category: position for position, category in enumerate(categories)}
    matrix = np.zeros((len(categories), len(categories)), dtype=np.float64)
    for value_a, value_b in zip(labels_a, labels_b, strict=True):
        matrix[index[value_a], index[value_b]] += 1.0
    total = float(matrix.sum())
    observed = float(np.trace(matrix)) / total
    expected = float((matrix.sum(axis=1) / total) @ (matrix.sum(axis=0) / total))
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else 0.0
    return (observed - expected) / (1.0 - expected)


def krippendorff_alpha(labels_by_annotator: Mapping[str, Mapping[str, str]]) -> float:
    """Krippendorff's alpha for nominal labels with missing data.

    ``labels_by_annotator`` maps annotator -> (unit id -> label); units may
    be labeled by any subset of annotators, and only units labeled by at
    least two annotators (pairable units) contribute.

    Implements the standard coincidence-matrix formulation: each pairable
    unit with ``m`` labels contributes ``1 / (m - 1)`` to the coincidence
    count ``o[c, k]`` for every ordered pair of its labels. With
    ``n_c = sum_k o[c, k]`` and ``n = sum_c n_c``, the nominal form is::

        alpha = 1 - D_o / D_e
        D_o   = n - trace(o)                     # observed disagreement
        D_e   = (n^2 - sum_c n_c^2) / (n - 1)    # expected disagreement

    Degenerate cases: no pairable unit raises ``ValueError``; when expected
    disagreement is zero (a single observed category) the result is 1.0.
    """
    values_by_unit: dict[str, list[str]] = defaultdict(list)
    for annotator in sorted(labels_by_annotator):
        for unit_id, value in labels_by_annotator[annotator].items():
            values_by_unit[unit_id].append(value)
    pairable = [values for values in values_by_unit.values() if len(values) >= _MIN_RATERS]
    if not pairable:
        raise ValueError(
            "krippendorff_alpha requires at least one unit labeled by two or more annotators"
        )
    categories = sorted({value for values in pairable for value in values})
    index = {category: position for position, category in enumerate(categories)}
    coincidence = np.zeros((len(categories), len(categories)), dtype=np.float64)
    for values in pairable:
        weight = 1.0 / (len(values) - 1)
        for position_a, value_a in enumerate(values):
            for position_b, value_b in enumerate(values):
                if position_a != position_b:
                    coincidence[index[value_a], index[value_b]] += weight
    margins = coincidence.sum(axis=1)
    total = float(margins.sum())
    observed_disagreement = total - float(np.trace(coincidence))
    expected_disagreement = (total * total - float(np.sum(margins**2))) / (total - 1.0)
    if math.isclose(expected_disagreement, 0.0):
        return 1.0
    return 1.0 - observed_disagreement / expected_disagreement


def _field_value(label: AuditLabel, field_name: str) -> str:
    """Encode one judgment field of a label as a nominal category string."""
    if field_name == "tier":
        return label.tier.value
    value = getattr(label, field_name)
    return "true" if value else "false"


def agreement_report(labels: Sequence[AuditLabel]) -> dict[str, float]:
    """Per-field agreement over the annotator-overlap subset of ``labels``.

    For each judgment field (``target_correct``, ``anchor_natural``,
    ``placement_valid``, ``tier``) the report contains ``kappa_<field>``
    (the mean pairwise Cohen's kappa over annotator pairs that share at
    least one item) and ``alpha_<field>`` (Krippendorff's alpha over all
    annotators). A later label replaces an earlier one from the same
    annotator for the same item.

    When no item is labeled by two or more annotators there is no overlap
    to measure and the result is ``{}`` — the caller must treat agreement
    as unknown, not perfect.
    """
    by_annotator: dict[str, dict[str, AuditLabel]] = defaultdict(dict)
    for label in labels:
        by_annotator[label.annotator][label.item_id] = label
    annotators = sorted(by_annotator)

    labeled_by: dict[str, int] = defaultdict(int)
    for items in by_annotator.values():
        for item_id in items:
            labeled_by[item_id] += 1
    if not any(count >= _MIN_RATERS for count in labeled_by.values()):
        return {}

    report: dict[str, float] = {}
    for field_name in _LABEL_FIELDS:
        kappas: list[float] = []
        for annotator_a, annotator_b in combinations(annotators, 2):
            shared = sorted(set(by_annotator[annotator_a]) & set(by_annotator[annotator_b]))
            if not shared:
                continue
            values_a = [
                _field_value(by_annotator[annotator_a][item], field_name) for item in shared
            ]
            values_b = [
                _field_value(by_annotator[annotator_b][item], field_name) for item in shared
            ]
            kappas.append(cohen_kappa(values_a, values_b))
        if kappas:
            report[f"kappa_{field_name}"] = float(np.mean(kappas))
        mapping = {
            annotator: {
                item_id: _field_value(label, field_name)
                for item_id, label in by_annotator[annotator].items()
            }
            for annotator in annotators
        }
        report[f"alpha_{field_name}"] = krippendorff_alpha(mapping)
    return report
