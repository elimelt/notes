"""Three-head score combination and sparse global selection of inline proposals.

Implements SPEC-INLINE-LINKING §6 (Q24-Q25), §7 (Q31), and §10: the three
model heads (anchor naturalness, target correctness, placement validity)
stay separate through the pipeline and are combined only here, at global
selection; a per-note link budget (~1 link / 150-200 words, hard-capped)
enforces the WSDM 2016 finding that links compete for reader attention; and
greedy MMR (Carbonell & Goldstein) with a same-target redundancy penalty
keeps the accepted set diverse. Two hard constraints sit outside the learned
scores, per the spec's final caveat: selected spans within a note never
overlap each other, and overlap with *existing* links must have been
excluded upstream (violations are rejected loudly, never re-scored).

Score combination is a weighted geometric mean, so a near-zero score from
any head vetoes the proposal — a natural anchor pointing at the wrong target
(or vice versa) cannot be averaged into acceptability the way an arithmetic
mean would allow.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any

import numpy as np

from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.errors import ConfigError
from linkdiscovery.fingerprint import fingerprint as _fingerprint
from linkdiscovery.inline.records import (
    PRODUCER_VERSION,
    SCHEMA_VERSION,
    InlineProposal,
    InlineProposalSet,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from numpy.typing import NDArray

    from linkdiscovery.contracts.documents import SourceDocument
    from linkdiscovery.contracts.units import Span

__all__ = [
    "COMBINE_WEIGHT_KEYS",
    "Q25_TARGET_CORRECTNESS",
    "SelectionConfig",
    "combine_scores",
    "precision_recall_sweep",
    "select_proposals",
]

COMBINE_WEIGHT_KEYS = frozenset({"naturalness", "target", "placement"})
"""The only legal keys of ``SelectionConfig.combine_weights``."""

Q25_TARGET_CORRECTNESS = 0.7
"""Target-correctness level at which a low-naturalness draft is kept (spec §6 Q25)."""


def _default_combine_weights() -> dict[str, float]:
    return {"naturalness": 0.35, "target": 0.45, "placement": 0.20}


def _check_unit_interval(value: float, name: str, context: str) -> None:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ConfigError(f"{context}: {name} must be in [0, 1], got {value!r}")


def _check_weights(weights: Mapping[str, float], context: str) -> None:
    """Validate combine weights: known keys, finite non-negative values, positive sum."""
    unknown = sorted(set(weights) - COMBINE_WEIGHT_KEYS)
    if unknown:
        allowed = ", ".join(sorted(COMBINE_WEIGHT_KEYS))
        raise ConfigError(
            f"{context}: unknown combine_weights key(s) {unknown}; expected only: {allowed}"
        )
    for key, weight in weights.items():
        if not isinstance(weight, int | float) or isinstance(weight, bool):
            raise ConfigError(f"{context}: combine_weights[{key!r}] must be a number")
        if not math.isfinite(weight) or weight < 0.0:
            raise ConfigError(
                f"{context}: combine_weights[{key!r}] must be finite and >= 0, got {weight!r}"
            )
    if sum(weights.values()) <= 0.0:
        raise ConfigError(f"{context}: combine_weights must have a positive total weight")


@dataclass(frozen=True, slots=True)
class SelectionConfig:
    """Global-selection policy: thresholds, per-note budget, and MMR diversity.

    Defaults follow SPEC-INLINE-LINKING §10: an accept threshold on the
    calibrated probability, a budget of ~1 link per 175 words hard-capped at
    10 per note, MMR lambda 0.6 (relevance-leaning, for a precision-oriented
    review tool), and a same-target redundancy penalty. ``combine_weights``
    weights the geometric-mean head combination of :func:`combine_scores`;
    unknown keys are rejected at construction. Invariants are validated in
    ``__post_init__`` and violations raise
    :class:`~linkdiscovery.errors.ConfigError`.
    """

    accept_threshold: float = 0.5
    words_per_link: int = 175
    max_links_per_note: int = 10
    mmr_lambda: float = 0.6
    target_redundancy_penalty: float = 0.3
    naturalness_floor: float = 0.2
    combine_weights: dict[str, float] = field(default_factory=_default_combine_weights)

    def __post_init__(self) -> None:
        context = "SelectionConfig"
        _check_unit_interval(self.accept_threshold, "accept_threshold", context)
        _check_unit_interval(self.mmr_lambda, "mmr_lambda", context)
        _check_unit_interval(self.naturalness_floor, "naturalness_floor", context)
        if self.words_per_link < 1:
            raise ConfigError(f"{context}: words_per_link must be >= 1, got {self.words_per_link}")
        if self.max_links_per_note < 1:
            raise ConfigError(
                f"{context}: max_links_per_note must be >= 1, got {self.max_links_per_note}"
            )
        if (
            not math.isfinite(self.target_redundancy_penalty)
            or self.target_redundancy_penalty < 0.0
        ):
            raise ConfigError(
                f"{context}: target_redundancy_penalty must be finite and >= 0, "
                f"got {self.target_redundancy_penalty!r}"
            )
        _check_weights(self.combine_weights, context)

    def resolved_dict(self) -> dict[str, Any]:
        """Return the fully resolved (defaults filled) JSON-safe form."""
        return {
            "accept_threshold": self.accept_threshold,
            "words_per_link": self.words_per_link,
            "max_links_per_note": self.max_links_per_note,
            "mmr_lambda": self.mmr_lambda,
            "target_redundancy_penalty": self.target_redundancy_penalty,
            "naturalness_floor": self.naturalness_floor,
            "combine_weights": dict(self.combine_weights),
        }

    def fingerprint(self) -> str:
        """Fingerprint of the resolved config, recorded in the proposal-set header."""
        return _fingerprint(self.resolved_dict())


def combine_scores(
    naturalness: float,
    target_correctness: float,
    placement_validity: float,
    weights: Mapping[str, float],
) -> float:
    """Weighted geometric mean of the three head scores (spec §6 Q24).

    ``exp(sum_i w_i * ln(s_i) / sum_i w_i)`` over the heads with positive
    weight. The geometric mean is chosen over an arithmetic one because it
    vetoes: any near-zero head drives the combined score toward zero, so a
    wrong target cannot be rescued by a beautiful anchor. Heads remain
    separate on the :class:`~linkdiscovery.inline.records.InlineProposal`;
    this combination happens only at global selection.

    Raises ``ValueError`` for scores outside [0, 1] or invalid weights
    (unknown keys, negative values, zero total weight).
    """
    context = "combine_scores"
    try:
        _check_weights(weights, context)
    except ConfigError as exc:
        raise ValueError(str(exc)) from exc
    scores = {
        "naturalness": naturalness,
        "target": target_correctness,
        "placement": placement_validity,
    }
    for name, score in scores.items():
        if not math.isfinite(score) or not 0.0 <= score <= 1.0:
            raise ValueError(f"{context}: {name} score must be in [0, 1], got {score!r}")
    total_weight = 0.0
    log_sum = 0.0
    for name, score in scores.items():
        weight = weights.get(name, 0.0)
        if weight <= 0.0:
            continue
        if score == 0.0:
            return 0.0
        total_weight += weight
        log_sum += weight * math.log(score)
    return math.exp(log_sum / total_weight)


def _effective_score(proposal: InlineProposal) -> float:
    """The accept probability: calibrated when available, else the combined score."""
    if proposal.calibrated_probability is not None:
        return proposal.calibrated_probability
    return proposal.combined_score


def _spans_overlap(a: Span, b: Span) -> bool:
    """Whether two half-open character ranges intersect."""
    return a.start < b.end and b.start < a.end


def _note_budget(document: SourceDocument, config: SelectionConfig) -> int:
    """Per-note link budget from spec §7 Q31: min(cap, max(1, words // words_per_link))."""
    word_count = len(document.content.split())
    return min(config.max_links_per_note, max(1, word_count // config.words_per_link))


def _make_similarity(
    target_similarity: Mapping[tuple[str, str], float] | None,
) -> Callable[[str, str], float]:
    """Target-pair similarity for MMR; ``None`` means pure target-redundancy mode.

    The same target is always similarity 1.0. With a mapping, distinct pairs
    look up ``(a, b)`` then ``(b, a)`` and default to 0.0; without one,
    distinct targets are similarity 0.0.
    """

    def similarity(a: str, b: str) -> float:
        if a == b:
            return 1.0
        if target_similarity is None:
            return 0.0
        return target_similarity.get((a, b), target_similarity.get((b, a), 0.0))

    return similarity


def _validate_drafts(
    drafts: Sequence[InlineProposal], documents: Mapping[str, SourceDocument]
) -> None:
    """Enforce upstream hard constraints before any scoring happens.

    Overlap with existing links is a hard constraint the spec keeps outside
    the learned scores; upstream stages must have excluded such drafts. A
    draft arriving with a truthy ``overlaps_existing_link`` feature is a
    pipeline bug, reported loudly rather than silently filtered.
    """
    for draft in drafts:
        if draft.source_document_id not in documents:
            raise ValueError(
                f"select_proposals: draft {draft.id!r} references unknown source document "
                f"{draft.source_document_id!r}; pass every referenced document in `documents`"
            )
        if draft.features.get("overlaps_existing_link", 0.0) != 0.0:
            raise ValueError(
                f"select_proposals: draft {draft.id!r} overlaps an existing link "
                "(feature 'overlaps_existing_link' is set); such drafts must be "
                "excluded upstream, never re-scored at selection"
            )


def _partition(
    drafts: Sequence[InlineProposal], config: SelectionConfig
) -> tuple[list[InlineProposal], list[tuple[InlineProposal, str]]]:
    """Split drafts into MMR-eligible candidates and (draft, reason) rejections.

    Q25 behavior (documented decision): a draft with high target correctness
    (>= ``Q25_TARGET_CORRECTNESS``) but naturalness below the floor is KEPT —
    marked with feature ``suggest_better_anchor=1.0``, ``abstained`` False,
    review status untouched — and it DOES count against the per-note budget
    like any other candidate. Reporters surface these as anchor-improvement
    suggestions rather than auto-links; charging them to the budget keeps the
    budget an honest cap on total reviewer attention per note. The rescue
    applies only to the naturalness floor: an abstained draft or one below
    ``accept_threshold`` is rejected regardless of target correctness.
    """
    eligible: list[InlineProposal] = []
    rejected: list[tuple[InlineProposal, str]] = []
    for draft in drafts:
        if draft.abstained:
            rejected.append((draft, "abstained_upstream"))
        elif _effective_score(draft) < config.accept_threshold:
            rejected.append((draft, "below_accept_threshold"))
        elif draft.naturalness < config.naturalness_floor:
            if draft.target_correctness >= Q25_TARGET_CORRECTNESS:
                marked = replace(draft, features={**draft.features, "suggest_better_anchor": 1.0})
                eligible.append(marked)
            else:
                rejected.append((draft, "below_naturalness_floor"))
        else:
            eligible.append(draft)
    return eligible, rejected


def _mmr_select(
    candidates: Sequence[InlineProposal],
    budget: int,
    config: SelectionConfig,
    similarity: Callable[[str, str], float],
) -> tuple[list[tuple[InlineProposal, float]], list[tuple[InlineProposal, str]]]:
    """Greedy MMR within one note (spec §10), returning selections and rejections.

    Each round scores every remaining candidate as
    ``lambda * relevance - (1 - lambda) * max_sim(target, selected targets)
    - target_redundancy_penalty * |already selected with the same target|``
    where relevance is the calibrated (or combined) probability, and picks
    the maximum; ties break deterministically by span start then id. After a
    pick, remaining candidates whose spans overlap the picked span are
    rejected outright — the hard no-overlap constraint — which realizes
    "keep the higher score" because higher-scored spans are picked first.
    """
    selected: list[tuple[InlineProposal, float]] = []
    rejected: list[tuple[InlineProposal, str]] = []
    selected_targets: list[str] = []
    remaining = list(candidates)
    while remaining and len(selected) < budget:
        best_key: tuple[float, int, str] | None = None
        best: tuple[InlineProposal, float] | None = None
        for draft in remaining:
            max_sim = max(
                (similarity(draft.target_document_id, target) for target in selected_targets),
                default=0.0,
            )
            same_target = sum(
                1 for target in selected_targets if target == draft.target_document_id
            )
            adjusted = (
                config.mmr_lambda * _effective_score(draft)
                - (1.0 - config.mmr_lambda) * max_sim
                - config.target_redundancy_penalty * same_target
            )
            key = (-adjusted, draft.span.start, draft.id)
            if best_key is None or key < best_key:
                best_key = key
                best = (draft, adjusted)
        assert best is not None  # remaining is non-empty
        chosen, adjusted = best
        selected.append((chosen, adjusted))
        selected_targets.append(chosen.target_document_id)
        survivors: list[InlineProposal] = []
        for draft in remaining:
            if draft.id == chosen.id:
                continue
            if _spans_overlap(draft.span, chosen.span):
                rejected.append((draft, "overlaps_selected_span"))
            else:
                survivors.append(draft)
        remaining = survivors
    rejected.extend((draft, "over_budget") for draft in remaining)
    return selected, rejected


def _rejection_record(draft: InlineProposal, reason: str) -> InlineProposal:
    """An audit-preserving abstained copy of a rejected draft.

    Rejected drafts stay in the proposal set marked ``abstained=True`` with
    feature flags ``selection_rejected=1.0`` and ``rejected_<reason>=1.0``,
    per the :class:`InlineProposalSet` contract that abstentions are kept
    rather than deleted so the rejection decision stays auditable.
    """
    features = {**draft.features, "selection_rejected": 1.0, f"rejected_{reason}": 1.0}
    return replace(draft, abstained=True, features=features)


def select_proposals(
    drafts: Sequence[InlineProposal],
    documents: Mapping[str, SourceDocument],
    *,
    config: SelectionConfig,
    run_id: str = "adhoc",
    corpus_id: str = "",
    target_similarity: Mapping[tuple[str, str], float] | None = None,
) -> InlineProposalSet:
    """Sparse global selection over draft proposals (spec §6 Q24-25, §7 Q31, §10).

    Pipeline: (1) drop upstream abstentions, drafts below
    ``accept_threshold`` (on the calibrated probability, falling back to the
    combined score when uncalibrated), and drafts below the naturalness
    floor; (2) except the Q25 case — high target correctness with low
    naturalness is kept, marked ``suggest_better_anchor=1.0``, and charged
    to the budget (see :func:`_partition`); (3) compute each note's budget
    from its word count; (4) run greedy MMR with the same-target redundancy
    penalty within each note; (5) enforce the hard no-overlap constraint
    between selected spans; (6) order accepted proposals globally by
    calibrated probability descending (ties: source document, span start,
    id), followed by the rejected drafts marked abstained for auditability.

    Accepted proposals gain features ``selection_rank`` (1-based global
    rank), ``note_budget``, and ``mmr_adjusted_score``. ``target_similarity``
    maps unordered target-id pairs to similarity for the MMR term; ``None``
    means pure target-redundancy mode (1.0 for the same target, 0.0
    otherwise).

    Raises ``ValueError`` when a draft references a document missing from
    ``documents`` or arrives with the ``overlaps_existing_link`` feature set
    (that hard constraint belongs upstream).
    """
    _validate_drafts(drafts, documents)
    eligible, rejected = _partition(drafts, config)
    similarity = _make_similarity(target_similarity)

    by_note: dict[str, list[InlineProposal]] = {}
    for draft in eligible:
        by_note.setdefault(draft.source_document_id, []).append(draft)

    accepted: list[tuple[InlineProposal, float, int]] = []
    for note_id in sorted(by_note):
        budget = _note_budget(documents[note_id], config)
        note_selected, note_rejected = _mmr_select(by_note[note_id], budget, config, similarity)
        accepted.extend((draft, adjusted, budget) for draft, adjusted in note_selected)
        rejected.extend(note_rejected)

    accepted.sort(
        key=lambda entry: (
            -_effective_score(entry[0]),
            entry[0].source_document_id,
            entry[0].span.start,
            entry[0].id,
        )
    )
    final: list[InlineProposal] = []
    for rank, (draft, adjusted, budget) in enumerate(accepted, start=1):
        features = {
            **draft.features,
            "selection_rank": float(rank),
            "note_budget": float(budget),
            "mmr_adjusted_score": adjusted,
        }
        final.append(replace(draft, features=features))

    rejected.sort(key=lambda entry: (entry[0].source_document_id, entry[0].span.start, entry[0].id))
    final.extend(_rejection_record(draft, reason) for draft, reason in rejected)

    header = ArtifactHeader(
        schema_version=SCHEMA_VERSION,
        run_id=run_id,
        corpus_id=corpus_id,
        created_at=utc_now_iso(),
        config_fingerprint=config.fingerprint(),
        producer_version=PRODUCER_VERSION,
    )
    return InlineProposalSet(header=header, proposals=tuple(final))


def precision_recall_sweep(
    probs: NDArray[np.float64],
    labels: NDArray[np.bool_],
    thresholds: Sequence[float],
) -> list[dict[str, float]]:
    """The tau-tuning table from spec §10: precision/recall per accept threshold.

    For each threshold tau, items with ``prob >= tau`` are accepted; the row
    reports ``threshold``, ``precision`` (correct fraction of accepted, 0.0
    when nothing is accepted), ``recall`` (accepted fraction of all correct
    items), and ``accepted_count``. Used to pick the operating point where
    precision reaches the ~0.78 target of spec §10.

    Raises ``ValueError`` for empty inputs, probabilities outside [0, 1],
    an empty threshold list, or labels with no positive example (recall is
    undefined without any correct item).
    """
    context = "precision_recall_sweep"
    probs_arr = np.asarray(probs, dtype=np.float64)
    if probs_arr.ndim != 1 or probs_arr.size == 0:
        raise ValueError(f"{context}: probs must be a non-empty 1-D array")
    if not np.all(np.isfinite(probs_arr)) or np.any(probs_arr < 0.0) or np.any(probs_arr > 1.0):
        raise ValueError(f"{context}: probs must lie in [0, 1]")
    labels_arr = np.asarray(labels)
    if labels_arr.dtype != np.bool_ or labels_arr.shape != probs_arr.shape:
        raise ValueError(f"{context}: labels must be a boolean array matching probs")
    if not labels_arr.any():
        raise ValueError(
            f"{context}: labels contain no positive example, so recall is undefined; "
            "include at least one correct item"
        )
    if len(thresholds) == 0:
        raise ValueError(f"{context}: thresholds is empty; provide at least one tau to sweep")
    positives = int(labels_arr.sum())
    rows: list[dict[str, float]] = []
    for tau in thresholds:
        accepted = probs_arr >= tau
        accepted_count = int(accepted.sum())
        true_positives = int((accepted & labels_arr).sum())
        rows.append(
            {
                "threshold": float(tau),
                "precision": true_positives / accepted_count if accepted_count else 0.0,
                "recall": true_positives / positives,
                "accepted_count": float(accepted_count),
            }
        )
    return rows
