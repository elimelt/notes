"""Evaluation suite for the inline-link subsystem.

Implements the evaluation discipline of SPEC-INLINE-LINKING §7 (Questions
27-32), the leakage-safe split design of §8 (plus §5 Question 20), and the
§12 kill criterion:

- :func:`three_way_split`: a document + anchor-string + target grouped split
  so no identifier straddles train/val/test (§8, Q20).
- :func:`span_detection_f1`: source-span detection F1 for the mention stage
  (§7 Q27, "source-span F1 for the detection stage").
- :func:`retrieval_metrics`: target Recall@k and MRR retrieval diagnostics
  (§7 Q27).
- :func:`judged_only_precision` and :func:`bpref`: TREC-style judged-only
  pooling metrics that never score unjudged proposals as wrong (§7 Q28).
- :func:`score_benchmark`: accuracy over the seven frozen expert-benchmark
  judgment types (§7 Q29).
- :func:`operating_point` and :func:`kill_criterion`: the §7 Q30 deploy gate
  and the §12 kill signal for the learned approach.

Every function is pure and deterministic; empty inputs yield well-defined
zeros rather than ``ZeroDivisionError``.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from linkdiscovery.contracts.base import (
    expect_int,
    expect_mapping,
    expect_str_float_map,
    expect_str_tuple,
)
from linkdiscovery.errors import ContractError
from linkdiscovery.inline.records import BenchmarkKind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from linkdiscovery.contracts.units import Span
    from linkdiscovery.inline.records import (
        AuditItem,
        Benchmark,
        BenchmarkCase,
        InlineProposal,
        InlineProposalSet,
        SpanCandidate,
    )

__all__ = [
    "KILL_PRECISION_FLOOR",
    "KILL_RECALL_FLOOR",
    "SplitAssignment",
    "bpref",
    "judged_only_precision",
    "kill_criterion",
    "operating_point",
    "retrieval_metrics",
    "score_benchmark",
    "span_detection_f1",
    "three_way_split",
]

SPLIT_NAMES: tuple[str, str, str] = ("train", "val", "test")
"""The three split labels, in greedy tie-break priority order."""

KILL_PRECISION_FLOOR = 0.70
"""SPEC §12: minimum benchmark precision@1 the learned linker must reach."""

KILL_RECALL_FLOOR = 0.20
"""SPEC §12: minimum recall for an operating point to count as usable."""


def _normalize_anchor(anchor: str) -> str:
    """Casefold and whitespace-collapse an anchor string for identity."""
    return " ".join(anchor.split()).casefold()


@dataclass(frozen=True, slots=True)
class SplitAssignment:
    """The result of :func:`three_way_split`.

    ``assignments[i]`` is the split ("train"/"val"/"test") of item ``i`` in
    the input sequence. ``achieved_fractions`` reports the fraction of items
    that actually landed in each split — with heavily linked identifiers the
    grouped constraint can force large deviations from the requested
    fractions, and this field reports that honestly rather than hiding it.
    ``group_count`` is the number of connected identifier groups found.
    """

    assignments: tuple[str, ...]
    achieved_fractions: dict[str, float] = field(default_factory=dict)
    group_count: int = 0

    def __post_init__(self) -> None:
        for index, split in enumerate(self.assignments):
            if split not in SPLIT_NAMES:
                allowed = ", ".join(SPLIT_NAMES)
                raise ContractError(
                    f"SplitAssignment: assignments[{index}] is {split!r}; "
                    f"expected one of: {allowed}"
                )
        if self.group_count < 0:
            raise ContractError(
                f"SplitAssignment: group_count must be >= 0, got {self.group_count}"
            )

    def split_of(self, index: int) -> str:
        """The split label of item ``index``."""
        return self.assignments[index]

    def indices_for(self, split: str) -> tuple[int, ...]:
        """All item indices assigned to ``split``, in input order."""
        return tuple(index for index, name in enumerate(self.assignments) if name == split)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "assignments": list(self.assignments),
            "achieved_fractions": dict(self.achieved_fractions),
            "group_count": self.group_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SplitAssignment:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "SplitAssignment"
        mapping = expect_mapping(data, context)
        return cls(
            assignments=expect_str_tuple(mapping, "assignments", context),
            achieved_fractions=expect_str_float_map(
                mapping, "achieved_fractions", context, default={}
            ),
            group_count=expect_int(mapping, "group_count", context, default=0),
        )


def _find(parent: dict[str, str], node: str) -> str:
    """Union-find root lookup with path compression."""
    root = node
    while parent[root] != root:
        root = parent[root]
    while parent[node] != root:
        parent[node], node = root, parent[node]
    return root


def _union(parent: dict[str, str], a: str, b: str) -> None:
    """Merge the union-find groups containing ``a`` and ``b``."""
    parent[_find(parent, a)] = _find(parent, b)


def three_way_split(
    items: Sequence[tuple[str, str, str]],
    *,
    seed: int,
    test_fraction: float,
    val_fraction: float,
) -> SplitAssignment:
    """Split link items into train/val/test with no straddling identifier.

    Implements the leakage control of SPEC-INLINE-LINKING §8 and §5 Q20:
    "Split by **document** *and* by **anchor-string** *and* by **target** so
    no anchor or target straddles the split." Each item is
    ``(document_id, anchor_string, target_id)``; anchor strings are
    casefolded and whitespace-collapsed before comparison. Items are joined
    into connected groups via union-find over the tripartite identifier
    graph (an item ties its document, anchor, and target nodes together), so
    two items sharing any identifier land in the same group and therefore
    the same split.

    Groups are then assigned greedily: largest group first (ties shuffled by
    ``seed``), each group goes to the split with the largest remaining
    deficit against its target count, with ties preferring train, then val,
    then test. Honesty note: with heavy linkage a few giant groups can make
    the achieved fractions deviate substantially from the requested ones —
    the deviation is reported in ``achieved_fractions``, never hidden.

    Raises ``ValueError`` when a fraction is outside ``[0, 1)`` or the two
    fractions sum to ``>= 1`` (train must remain non-degenerate as a target).
    """
    if not 0.0 <= test_fraction < 1.0 or not 0.0 <= val_fraction < 1.0:
        raise ValueError(
            f"test_fraction and val_fraction must each be in [0, 1), "
            f"got {test_fraction} and {val_fraction}"
        )
    if test_fraction + val_fraction >= 1.0:
        raise ValueError(
            f"test_fraction + val_fraction must be < 1, "
            f"got {test_fraction} + {val_fraction} = {test_fraction + val_fraction}"
        )
    total = len(items)
    if total == 0:
        return SplitAssignment((), dict.fromkeys(SPLIT_NAMES, 0.0), 0)

    parent: dict[str, str] = {}

    def node(kind: str, value: str) -> str:
        key = f"{kind}:{value}"
        parent.setdefault(key, key)
        return key

    for document_id, anchor, target_id in items:
        doc_node = node("doc", document_id)
        _union(parent, doc_node, node("anchor", _normalize_anchor(anchor)))
        _union(parent, doc_node, node("target", target_id))

    groups: dict[str, list[int]] = {}
    for index, (document_id, _, _) in enumerate(items):
        groups.setdefault(_find(parent, f"doc:{document_id}"), []).append(index)

    # Deterministic group order: by first item index, then a seeded shuffle
    # key for size ties, then largest-first for the greedy fill.
    rng = random.Random(seed)
    ordered = sorted(groups.values(), key=lambda group: group[0])
    keyed = sorted(
        ((len(group), rng.random(), group) for group in ordered),
        key=lambda entry: (-entry[0], entry[1]),
    )

    train_fraction = 1.0 - test_fraction - val_fraction
    targets = {
        "train": train_fraction * total,
        "val": val_fraction * total,
        "test": test_fraction * total,
    }
    assigned = dict.fromkeys(SPLIT_NAMES, 0)
    labels = [""] * total
    for size, _, group in keyed:
        deficits = {split: targets[split] - assigned[split] for split in SPLIT_NAMES}
        best_split = max(SPLIT_NAMES, key=deficits.__getitem__)
        for index in group:
            labels[index] = best_split
        assigned[best_split] += size

    achieved = {split: assigned[split] / total for split in SPLIT_NAMES}
    return SplitAssignment(tuple(labels), achieved, len(groups))


def _span_jaccard(a: Span, b: Span) -> float:
    """Character-range Jaccard overlap of two half-open spans (0 when disjoint)."""
    intersection = min(a.end, b.end) - max(a.start, b.start)
    if intersection <= 0:
        return 0.0
    union = (a.end - a.start) + (b.end - b.start) - intersection
    return intersection / union if union > 0 else 0.0


def _precision_recall_f1(matches: int, n_predicted: int, n_gold: int) -> tuple[float, float, float]:
    """Zero-safe precision/recall/F1 from a one-to-one match count."""
    precision = matches / n_predicted if n_predicted else 0.0
    recall = matches / n_gold if n_gold else 0.0
    denominator = precision + recall
    f1 = 2.0 * precision * recall / denominator if denominator else 0.0
    return precision, recall, f1


def span_detection_f1(
    predicted: Sequence[SpanCandidate],
    gold: Sequence[AuditItem],
    *,
    overlap_threshold: float = 0.8,
) -> dict[str, float]:
    """Span-detection precision/recall/F1 with exact and overlap matching.

    The SPEC-INLINE-LINKING §7 Q27 detection-stage diagnostic ("source-span
    F1 for the detection stage"). ``gold`` is the caller-filtered set of
    prose-region audit items judged ``anchor_natural`` by consensus — this
    function scores exactly what it is given. Gold items lacking a
    ``source_span`` cannot be located and are excluded from both matching
    and the recall denominator (their count is visible via ``gold_count``).

    Exact matching requires the same document and identical span offsets;
    overlap matching requires the same document and character-range Jaccard
    ``>= overlap_threshold``, matched greedily one-to-one by descending
    overlap. Returns ``precision_exact``, ``recall_exact``, ``f1_exact``,
    ``precision_overlap``, ``recall_overlap``, ``f1_overlap``, plus
    ``predicted_count`` and ``gold_count``. Empty inputs yield zeros.

    Raises ``ValueError`` when ``overlap_threshold`` is outside ``(0, 1]``.
    """
    if not 0.0 < overlap_threshold <= 1.0:
        raise ValueError(f"overlap_threshold must be in (0, 1], got {overlap_threshold}")
    gold_spans = [
        (item.source_document_id, item.source_span) for item in gold if item.source_span is not None
    ]

    remaining = Counter(gold_spans)
    exact_matches = 0
    for candidate in predicted:
        key = (candidate.document_id, candidate.span)
        if remaining[key] > 0:
            remaining[key] -= 1
            exact_matches += 1

    pairs: list[tuple[float, int, int]] = []
    for predicted_index, candidate in enumerate(predicted):
        for gold_index, (document_id, span) in enumerate(gold_spans):
            if candidate.document_id != document_id:
                continue
            overlap = _span_jaccard(candidate.span, span)
            if overlap >= overlap_threshold:
                pairs.append((-overlap, predicted_index, gold_index))
    pairs.sort()
    used_predicted: set[int] = set()
    used_gold: set[int] = set()
    overlap_matches = 0
    for _, predicted_index, gold_index in pairs:
        if predicted_index in used_predicted or gold_index in used_gold:
            continue
        used_predicted.add(predicted_index)
        used_gold.add(gold_index)
        overlap_matches += 1

    n_predicted, n_gold = len(predicted), len(gold_spans)
    precision_exact, recall_exact, f1_exact = _precision_recall_f1(
        exact_matches, n_predicted, n_gold
    )
    precision_overlap, recall_overlap, f1_overlap = _precision_recall_f1(
        overlap_matches, n_predicted, n_gold
    )
    return {
        "precision_exact": precision_exact,
        "recall_exact": recall_exact,
        "f1_exact": f1_exact,
        "precision_overlap": precision_overlap,
        "recall_overlap": recall_overlap,
        "f1_overlap": f1_overlap,
        "predicted_count": float(n_predicted),
        "gold_count": float(n_gold),
    }


def retrieval_metrics(
    ranked_targets: Sequence[Sequence[str]],
    gold_targets: Sequence[str],
    *,
    k_values: Sequence[int] = (1, 3, 5, 10),
) -> dict[str, float]:
    """Target Recall@k and MRR retrieval diagnostics (SPEC §7 Q27).

    ``ranked_targets[i]`` is the ranked target-id list retrieved for query
    ``i`` and ``gold_targets[i]`` its single gold target. Recall@k is the
    fraction of queries whose gold target appears in the top ``k``; MRR is
    the mean reciprocal rank of the gold target, contributing 0 when it is
    absent. Also reports ``query_count``. Empty inputs yield zeros.

    Raises ``ValueError`` when the two sequences differ in length.
    """
    if len(ranked_targets) != len(gold_targets):
        raise ValueError(
            f"ranked_targets and gold_targets must align: "
            f"got {len(ranked_targets)} rankings for {len(gold_targets)} gold targets"
        )
    result = {f"recall_at_{k}": 0.0 for k in k_values}
    result["mrr"] = 0.0
    result["query_count"] = float(len(gold_targets))
    if not gold_targets:
        return result

    ranks: list[int] = []
    for ranked, gold in zip(ranked_targets, gold_targets, strict=True):
        rank = 0
        for position, target in enumerate(ranked, start=1):
            if target == gold:
                rank = position
                break
        ranks.append(rank)
    total = len(ranks)
    for k in k_values:
        result[f"recall_at_{k}"] = sum(1 for rank in ranks if 0 < rank <= k) / total
    result["mrr"] = sum(1.0 / rank for rank in ranks if rank > 0) / total
    return result


def _surfaced_proposals(proposals: InlineProposalSet) -> list[InlineProposal]:
    """Proposals in selection order, excluding abstained (never surfaced) ones."""
    return [proposal for proposal in proposals.proposals if not proposal.abstained]


def judged_only_precision(
    proposals: InlineProposalSet,
    judgments: Mapping[str, bool],
    *,
    k_values: Sequence[int] = (1, 5, 10, 25),
) -> dict[str, float]:
    """Judged-only precision@k with an explicit unjudged residual (SPEC §7 Q28).

    Implements the pooling discipline of §7 Q28: "compute precision over
    judged items; treat unjudged as unknown (report a residual...) rather
    than silently scoring them non-relevant." ``judgments`` maps proposal id
    to the human relevance judgment; proposals absent from it are unjudged
    and are *never* counted as wrong. Abstained proposals were never
    surfaced for review and are excluded from the ranking; the remaining
    proposals are taken in set order (the global selection order).

    For each ``k``, ``precision_at_{k}`` is the fraction of judged top-``k``
    proposals judged relevant (0.0 when none are judged), and
    ``judged_fraction_at_{k}`` is the judged share of the top-``k`` — the
    visible unjudged residual. Empty inputs yield zeros.
    """
    ranked = _surfaced_proposals(proposals)
    result: dict[str, float] = {}
    for k in k_values:
        top = ranked[:k]
        judged = [judgments[proposal.id] for proposal in top if proposal.id in judgments]
        result[f"precision_at_{k}"] = sum(judged) / len(judged) if judged else 0.0
        result[f"judged_fraction_at_{k}"] = len(judged) / len(top) if top else 0.0
    return result


def bpref(proposals: InlineProposalSet, judgments: Mapping[str, bool]) -> float:
    """Buckley-Voorhees bpref over the judged proposals (SPEC §7 Q28).

    bpref is the incomplete-judgment measure of Buckley & Voorhees
    ("Retrieval Evaluation with Incomplete Information", SIGIR 2004)::

        bpref = (1/R) * sum over judged-relevant r of
                (1 - min(n_before(r), R) / min(R, N))

    where ``R`` is the number of judged-relevant proposals, ``N`` the number
    of judged-nonrelevant proposals, and ``n_before(r)`` how many of the
    first ``R`` judged-nonrelevant proposals rank above ``r``. Only judged
    proposals participate; unjudged proposals are skipped entirely rather
    than scored as nonrelevant. Abstained proposals are excluded (never
    surfaced); ranking is the proposal-set order (global selection order).

    Returns 0.0 when nothing is judged relevant, and 1.0 when everything
    judged relevant ranks above every judged nonrelevant proposal (including
    the degenerate ``N == 0`` case, where each term is 1).
    """
    ranked = [proposal for proposal in _surfaced_proposals(proposals) if proposal.id in judgments]
    relevant_total = sum(1 for proposal in ranked if judgments[proposal.id])
    nonrelevant_total = len(ranked) - relevant_total
    if relevant_total == 0:
        return 0.0
    denominator = min(relevant_total, nonrelevant_total)
    total = 0.0
    nonrelevant_above = 0
    for proposal in ranked:
        if judgments[proposal.id]:
            if denominator == 0:
                total += 1.0
            else:
                total += 1.0 - min(nonrelevant_above, relevant_total) / denominator
        else:
            nonrelevant_above += 1
    return total / relevant_total


def _slice_stats(cases: Sequence[BenchmarkCase], outcomes: Mapping[str, bool]) -> dict[str, float]:
    """Accuracy plus evaluated/unevaluated counts for one benchmark slice."""
    evaluated = [case for case in cases if case.id in outcomes]
    correct = sum(1 for case in evaluated if outcomes[case.id] == case.expected)
    return {
        "accuracy": correct / len(evaluated) if evaluated else 0.0,
        "evaluated": float(len(evaluated)),
        "unevaluated": float(len(cases) - len(evaluated)),
        "total": float(len(cases)),
    }


def score_benchmark(
    benchmark: Benchmark, outcomes: Mapping[str, bool]
) -> dict[str, dict[str, float]]:
    """Score frozen expert-benchmark outcomes per judgment kind (SPEC §7 Q29).

    ``outcomes`` maps case id to the system's judgment of the case's
    property; a case is correct when its outcome equals ``expected``. The
    caller runs the system — this function only scores. The result has one
    entry per :class:`~linkdiscovery.inline.records.BenchmarkKind` (all
    seven, even when empty), plus ``overall`` and the ``hard_case`` slice
    (the §7 over-sampled difficult categories). Each entry reports
    ``accuracy`` (over evaluated cases only; 0.0 when none), ``evaluated``,
    ``unevaluated``, and ``total`` counts. Cases with no outcome are counted
    as unevaluated and reported — never scored as failures.
    """
    result = {
        kind.value: _slice_stats([case for case in benchmark.cases if case.kind is kind], outcomes)
        for kind in BenchmarkKind
    }
    result["overall"] = _slice_stats(benchmark.cases, outcomes)
    result["hard_case"] = _slice_stats(
        [case for case in benchmark.cases if case.hard_case], outcomes
    )
    return result


def operating_point(
    sweep: Sequence[Mapping[str, float]],
    *,
    min_precision: float = 0.75,
) -> dict[str, float] | None:
    """Pick the highest-recall sweep row meeting the precision bar (SPEC §7 Q30).

    This is the deploy-gate logic behind the SPEC §7 Q30 quality bar —
    "**precision@1 ~ 0.75-0.80 at ~40% recall for v1.** This mirrors the
    deployed Wikimedia add-a-link deploy gate: per Gerlach et al. (CIKM
    2021), 'In practice, we required a precision of 0.7-0.75 or higher such
    that the majority of suggestions would be true positives. As a result,
    we discarded models for 23 languages'" — each ``sweep`` row is one
    threshold setting with at least ``precision`` and ``recall`` keys (plus
    anything else, such as the threshold itself). Among rows with
    ``precision >= min_precision`` the highest-recall row wins (ties broken
    by higher precision, then first occurrence); the row is returned as a
    plain dict.

    Returns ``None`` when no row meets the bar — the §12 kill signal
    ("cannot reach ~0.70 at any usable recall"). Raises ``ValueError`` when
    a row lacks the required keys.
    """
    best: dict[str, float] | None = None
    for index, row in enumerate(sweep):
        if "precision" not in row or "recall" not in row:
            raise ValueError(
                f"operating_point: sweep row {index} must carry 'precision' and 'recall' keys"
            )
        if row["precision"] < min_precision:
            continue
        if best is None or (row["recall"], row["precision"]) > (best["recall"], best["precision"]):
            best = dict(row)
    return best


def kill_criterion(benchmark_p1: float, recall: float) -> bool:
    """The SPEC §12 kill decision for the learned linker, over its best point.

    SPEC §12: "if ... end-to-end precision@1 on the frozen expert benchmark
    cannot reach ~0.70 at any usable recall (say >= 20%), the learned linker
    is not ready to ship" and the fallback is the deterministic baseline
    (:mod:`linkdiscovery.inline.baseline`). The caller passes the *best*
    achievable benchmark operating point (for example the result of
    :func:`operating_point` with ``min_precision=0.70``, or the
    highest-precision point among those with recall >= 0.20). Returns
    ``True`` (kill) when that point fails either floor: recall below
    :data:`KILL_RECALL_FLOOR` (no usable recall exists at all) or
    precision@1 below :data:`KILL_PRECISION_FLOOR`.
    """
    return recall < KILL_RECALL_FLOOR or benchmark_p1 < KILL_PRECISION_FLOOR
