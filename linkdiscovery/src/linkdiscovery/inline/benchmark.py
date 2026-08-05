"""Frozen expert-benchmark runner (SPEC-INLINE-LINKING §7).

The frozen benchmark (``benchmarks/expert-benchmark-v1.json``, the
:class:`~linkdiscovery.inline.records.Benchmark` contract shape) asserts one
expert judgment per case; this module turns one engine run — its
pre-selection drafts plus its post-selection proposal set — into the
per-case boolean outcomes that :func:`~linkdiscovery.inline.evaluate.
score_benchmark` scores. Everything here is pure (no I/O, no RNG) and
deterministic: cases are evaluated in benchmark order, and the one tie-break
(the highest-combined-score overlapping draft) resolves by proposal id.

Two levels of system output feed the outcomes, on purpose. *Draft*-level
kinds (``natural_span``, ``acceptable_span``, ``correct_target``) judge what
the engine's heads believe about a span before budgets, MMR, and thresholds
intervene — a benchmark about scoring quality must not be graded through the
selection funnel. *Selection*-level kinds (``incorrect_target``, ``no_link``,
``valid_placement``, ``reverse_direction``) judge what the system actually
commits to: only ACCEPTED post-selection proposals (``abstained`` False)
count, because an abstention IS the system declining the pairing.

Cases locate their span by ``case.span`` when set, else by the FIRST
verbatim occurrence of the case's anchor text in the source document
(:func:`locate_case_span`). A case whose source document is missing or whose
span cannot be located is OMITTED from the outcome dict — ``score_benchmark``
already reports such cases as unevaluated rather than failed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from linkdiscovery.contracts.units import Span
from linkdiscovery.inline.records import Benchmark, BenchmarkCase, BenchmarkKind, InlineProposal
from linkdiscovery.inline.select import Q25_TARGET_CORRECTNESS

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from linkdiscovery.contracts.documents import SourceDocument
    from linkdiscovery.inline.records import InlineProposalSet

__all__ = [
    "NATURAL_SPAN_NATURALNESS",
    "locate_case_span",
    "run_benchmark",
]

NATURAL_SPAN_NATURALNESS: Final = 0.5
"""Naturalness-head level at which a draft counts as detecting a natural span."""


def locate_case_span(case: BenchmarkCase, document: SourceDocument) -> Span | None:
    """The character span a benchmark case judges, or ``None`` if unlocatable.

    Convention: a case with an explicit ``span`` uses it verbatim; otherwise
    the case locates by anchor text — the FIRST verbatim occurrence of
    ``case.anchor_text`` in ``document.content`` (the frozen v1 benchmark
    records every case this way, ``span`` null everywhere, so the benchmark
    survives content drift as long as the anchor phrase itself survives).
    ``None`` — an empty anchor or a phrase that no longer occurs — means the
    case is unevaluated, never failed.
    """
    if case.span is not None:
        return case.span
    if not case.anchor_text:
        return None
    offset = document.content.find(case.anchor_text)
    if offset < 0:
        return None
    return Span(start=offset, end=offset + len(case.anchor_text))


def _overlapping(
    proposals: Sequence[InlineProposal], source_document_id: str, span: Span
) -> list[InlineProposal]:
    """Proposals in the case's source document whose half-open span intersects."""
    return [
        proposal
        for proposal in proposals
        if proposal.source_document_id == source_document_id
        and proposal.span.start < span.end
        and span.start < proposal.span.end
    ]


def _case_outcome(  # noqa: PLR0911 -- one explicit branch per benchmark kind
    case: BenchmarkCase,
    drafts: Sequence[InlineProposal],
    accepted: Sequence[InlineProposal],
) -> bool:
    """The system's judgment of one located case (see :func:`run_benchmark`)."""
    kind = case.kind
    if kind is BenchmarkKind.NATURAL_SPAN:
        return any(draft.naturalness >= NATURAL_SPAN_NATURALNESS for draft in drafts)
    if kind is BenchmarkKind.ACCEPTABLE_SPAN:
        return any(
            draft.target_document_id == case.target_document_id
            and draft.target_correctness >= Q25_TARGET_CORRECTNESS
            for draft in drafts
        )
    if kind is BenchmarkKind.CORRECT_TARGET:
        if not drafts:
            return False
        best = min(drafts, key=lambda draft: (-draft.combined_score, draft.id))
        return best.target_document_id == case.target_document_id
    if kind is BenchmarkKind.INCORRECT_TARGET:
        return not any(
            proposal.target_document_id == case.target_document_id for proposal in accepted
        )
    if kind is BenchmarkKind.NO_LINK:
        return not accepted
    if kind is BenchmarkKind.VALID_PLACEMENT:
        if case.target_document_id is None:
            return bool(accepted)
        return any(proposal.target_document_id == case.target_document_id for proposal in accepted)
    assert kind is BenchmarkKind.REVERSE_DIRECTION  # the enum is closed
    return any(proposal.target_document_id == case.target_document_id for proposal in accepted)


def run_benchmark(
    benchmark: Benchmark,
    *,
    drafts: Sequence[InlineProposal],
    selected: InlineProposalSet,
    documents: Mapping[str, SourceDocument],
) -> dict[str, bool]:
    """Judge every locatable benchmark case against one engine run.

    ``drafts`` are the engine's PRE-selection draft proposals (one per
    scoreable candidate span); ``selected`` is the POST-selection proposal
    set, of which only the accepted (non-abstained) proposals participate.
    Overlap everywhere is half-open character-range intersection within the
    case's source document. Outcome semantics per kind — each is the
    system's claim that the judged property holds, scored against
    ``case.expected`` by ``score_benchmark``:

    - ``natural_span``: some overlapping DRAFT has ``naturalness >=``
      :data:`NATURAL_SPAN_NATURALNESS` — the naturalness head, judged before
      selection can hide it.
    - ``acceptable_span``: some overlapping draft pairs the case's target
      with ``target_correctness >=`` the spec §6 Q25 rescue level
      (:data:`~linkdiscovery.inline.select.Q25_TARGET_CORRECTNESS`) — the
      "right target, tolerable span" judgment.
    - ``correct_target``: the highest-combined-score overlapping draft
      exists and points at the case's target (ties break by proposal id,
      deterministically) — precision@1 of the target stack.
    - ``incorrect_target``: NO accepted proposal overlaps the span with the
      case's (known-wrong) target — the system "judges the pairing wrong"
      by declining to confidently link it; an abstention counts as a
      correct refusal.
    - ``no_link``: no accepted proposal overlaps the span at all.
    - ``valid_placement``: some accepted proposal overlaps the span (and
      matches the case's target when one is recorded) — the system commits
      a link at the judged placement.
    - ``reverse_direction``: some accepted proposal overlaps the span with
      the case's target — the reverse-direction anchor was actually linked.

    Cases whose source document is missing from ``documents`` or whose span
    cannot be located (:func:`locate_case_span`) are OMITTED — never scored
    as failures. Pure and deterministic: the result dict follows benchmark
    case order.
    """
    accepted = [proposal for proposal in selected.proposals if not proposal.abstained]
    outcomes: dict[str, bool] = {}
    for case in benchmark.cases:
        document = documents.get(case.source_document_id)
        if document is None:
            continue
        span = locate_case_span(case, document)
        if span is None:
            continue
        outcomes[case.id] = _case_outcome(
            case,
            _overlapping(drafts, case.source_document_id, span),
            _overlapping(accepted, case.source_document_id, span),
        )
    return outcomes
