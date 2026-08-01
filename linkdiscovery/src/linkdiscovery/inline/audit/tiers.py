"""Tier assignment rules and the audit go/no-go report.

Implements the tiering rules of SPEC-INLINE-LINKING §4: Tier A links are
strong positives for all heads, Tier B links supervise target correctness
only, Tier C links are graph supervision only (correct edges, bad anchor
examples), and Tier D links are excluded or used as negatives. The go/no-go
decision follows the spec's "Decision thresholds": kappa >= 0.6 on the
overlap-labeled subset and at least ~150 clean Tier A+B positives.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence

from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.fingerprint import fingerprint
from linkdiscovery.inline.audit.agreement import agreement_report
from linkdiscovery.inline.records import (
    PRODUCER_VERSION,
    SCHEMA_VERSION,
    AuditLabel,
    AuditReport,
    AuditSample,
    LinkRegionKind,
    Tier,
)

__all__ = ["GRAPH_ONLY_REGIONS", "build_audit_report", "derive_tier"]

GRAPH_ONLY_REGIONS = frozenset(
    {
        LinkRegionKind.RELATED_NOTES,
        LinkRegionKind.HEADING,
        LinkRegionKind.TABLE,
        LinkRegionKind.CODE,
    }
)
"""Region kinds that cap a link at Tier C (SPEC-INLINE-LINKING §4).

Related-notes lists, headings, tables, and code links "are good graph edges
but bad anchor-placement examples": correct targets there stay retrieval
positives while never feeding the naturalness head.
"""

_TIER_BADNESS: dict[Tier, int] = {Tier.A: 0, Tier.B: 1, Tier.C: 2, Tier.D: 3}
"""Ordering used for consensus tie-breaking: ties resolve to the worse tier."""


def derive_tier(
    target_correct: bool,
    anchor_natural: bool,
    placement_valid: bool,
    region_kind: LinkRegionKind,
) -> Tier:
    """Map one audit judgment onto a supervision tier per SPEC-INLINE-LINKING §4.

    Rules, in order of precedence:

    1. Wrong target -> Tier D ("exclude or use as negatives"): an edge to
       the wrong note is unusable for any head.
    2. Graph-only region (:data:`GRAPH_ONLY_REGIONS`) -> at best Tier C
       ("graph supervision only"), even when all boolean judgments are
       positive, because such links are correct edges but terrible anchor
       and placement examples.
    3. Prose-like region with a natural anchor and valid placement ->
       Tier A ("strong positives for all heads").
    4. Prose-like region, correct target, but an unnatural anchor or
       invalid placement -> Tier B ("weak positives, use for
       target-correctness but not anchor-naturalness").

    Prose-like means any region outside :data:`GRAPH_ONLY_REGIONS`
    (``prose``, ``citation``, ``list``, ``other``); the spec singles out
    prose, and the same A/B logic is applied to the remaining
    non-graph-only kinds since they are judged case by case by annotators.
    """
    if not target_correct:
        return Tier.D
    if region_kind in GRAPH_ONLY_REGIONS:
        return Tier.C
    if anchor_natural and placement_valid:
        return Tier.A
    return Tier.B


def _consensus_tier(labels: Sequence[AuditLabel]) -> Tier:
    """Majority tier over one item's labels; a tie resolves to the worse tier.

    Resolving ties pessimistically keeps the clean-positive count honest:
    a disputed link never inflates the Tier A+B tally that gates modeling.
    """
    counts = Counter(label.tier for label in labels)
    top = max(counts.values())
    tied = [tier for tier, count in counts.items() if count == top]
    return max(tied, key=lambda tier: _TIER_BADNESS[tier])


def build_audit_report(
    sample: AuditSample,
    labels: Sequence[AuditLabel],
    *,
    run_id: str = "adhoc",
    min_kappa: float = 0.6,
    min_clean_positives: int = 150,
) -> AuditReport:
    """Compute tier counts, agreement, and the go/no-go decision for an audit.

    Consensus per item is the majority tier over that item's labels (one
    label per annotator, later labels replacing earlier ones from the same
    annotator; ties resolve to the worse tier). Agreement comes from
    :func:`~linkdiscovery.inline.audit.agreement.agreement_report` over the
    annotator-overlap subset. Labels whose ``item_id`` is not in the sample
    are ignored and noted.

    ``go`` is ``True`` only when (SPEC-INLINE-LINKING §4, "Decision
    thresholds"): agreement is measurable (some item labeled by at least two
    annotators), every per-field Cohen's kappa is >= ``min_kappa``, and the
    consensus Tier A+B count is >= ``min_clean_positives``. With a single
    annotator the decision is ``False`` with an explanatory note, never a
    silent pass.
    """
    item_ids = {item.id for item in sample.items}
    by_item: dict[str, dict[str, AuditLabel]] = defaultdict(dict)
    ignored = 0
    for label in labels:
        if label.item_id not in item_ids:
            ignored += 1
            continue
        by_item[label.item_id][label.annotator] = label

    tier_counts: dict[str, int] = {tier.value: 0 for tier in Tier}
    for item_labels in by_item.values():
        consensus = _consensus_tier(tuple(item_labels.values()))
        tier_counts[consensus.value] += 1

    kept_labels = [label for per_item in by_item.values() for label in per_item.values()]
    agreement = agreement_report(kept_labels)

    notes: list[str] = []
    if ignored:
        notes.append(f"ignored {ignored} label(s) whose item_id is not in the sample")
    n_labeled = len(by_item)
    if n_labeled < len(sample.items):
        notes.append(f"{len(sample.items) - n_labeled} of {len(sample.items)} items unlabeled")

    clean_positives = tier_counts[Tier.A.value] + tier_counts[Tier.B.value]
    kappas = [value for key, value in agreement.items() if key.startswith("kappa_")]
    if not kappas:
        go = False
        notes.append("single annotator: agreement unavailable, go decision requires overlap labels")
    else:
        worst_kappa = min(kappas)
        go = worst_kappa >= min_kappa and clean_positives >= min_clean_positives
        if worst_kappa < min_kappa:
            notes.append(f"minimum kappa {worst_kappa:.3f} is below threshold {min_kappa}")
        if clean_positives < min_clean_positives:
            notes.append(
                f"clean Tier A+B positives {clean_positives} below threshold {min_clean_positives}"
            )

    header = ArtifactHeader(
        schema_version=SCHEMA_VERSION,
        run_id=run_id,
        corpus_id=sample.header.corpus_id,
        created_at=utc_now_iso(),
        config_fingerprint=fingerprint(
            {"min_kappa": min_kappa, "min_clean_positives": min_clean_positives}
        ),
        producer_version=PRODUCER_VERSION,
    )
    return AuditReport(
        header=header,
        n_items=len(sample.items),
        n_labeled=n_labeled,
        tier_counts=tier_counts,
        agreement=agreement,
        go=go,
        notes=tuple(notes),
    )
