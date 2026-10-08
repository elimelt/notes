"""Data records for the inline-link discovery subsystem.

These are the stage-boundary contracts for the learned inline-link pipeline
described in SPEC-INLINE-LINKING.md: the data audit (§4), span candidates and
proposals (§1-§3), and the frozen expert benchmark (§7). Every type follows
the house contract conventions from :mod:`linkdiscovery.contracts`: frozen
slotted dataclasses, ``to_dict``/``from_dict`` over JSON-safe primitives, and
strict deserialization raising :class:`~linkdiscovery.errors.ContractError`
on missing fields, wrong types, or out-of-domain values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, TypeVar

from linkdiscovery.contracts.base import (
    ArtifactHeader,
    check_schema_version,
    expect_bool,
    expect_float,
    expect_header,
    expect_int,
    expect_list,
    expect_mapping,
    expect_nullable_float,
    expect_nullable_str,
    expect_str,
    expect_str_float_map,
    expect_str_int_map,
    expect_str_tuple,
)
from linkdiscovery.contracts.proposals import ReviewState
from linkdiscovery.contracts.units import Span
from linkdiscovery.errors import ContractError

__all__ = [
    "PRODUCER_VERSION",
    "REVIEW_ENGINES",
    "REVIEW_REASONS",
    "REVIEW_VERDICTS",
    "SCHEMA_VERSION",
    "AuditItem",
    "AuditLabel",
    "AuditReport",
    "AuditSample",
    "Benchmark",
    "BenchmarkCase",
    "BenchmarkKind",
    "InlineProposal",
    "InlineProposalSet",
    "InlineReviewDecision",
    "LinkRegionKind",
    "SpanCandidate",
    "Tier",
]

SCHEMA_VERSION = 1
"""Schema version for inline-link subsystem artifacts."""

PRODUCER_VERSION = "linkdiscovery-inline/0.1.0"
"""Producer version recorded in artifact headers written by this subsystem."""

REVIEW_ENGINES = frozenset({"baseline", "learned"})
"""The engines whose proposals the human-standard review judged."""

REVIEW_VERDICTS = frozenset({"accept", "reject"})
"""Legal overall verdicts of one review decision."""

REVIEW_REASONS = frozenset(
    {
        "good",
        "wrong_target",
        "unnatural_anchor",
        "duplicate_nearby",
        "generic_low_value",
        "bad_placement",
        "broken_span",
        "other",
    }
)
"""The closed reason taxonomy of the review file (one primary reason per item)."""

_E = TypeVar("_E", bound=StrEnum)


class Tier(StrEnum):
    """Supervision tier for an audited existing link (SPEC-INLINE-LINKING §4).

    - ``A``: strong positive for *all* heads (naturalness, target
      correctness, placement validity).
    - ``B``: weak positive / review-only; usable for target-correctness
      supervision but not for the anchor-naturalness head.
    - ``C``: graph supervision only — a correct edge but a bad anchor or
      placement example (Related-notes lists, headings, tables, code);
      excluded from the naturalness head, kept for target retrieval.
    - ``D``: exclude entirely, or use as a negative (wrong target).
    """

    A = "a"
    B = "b"
    C = "c"
    D = "d"


class LinkRegionKind(StrEnum):
    """Where an existing link physically sits in its source document.

    This is the audit-facing region taxonomy from SPEC-INLINE-LINKING §4:
    prose links are candidate anchor-placement examples, while links in
    Related-notes sections, headings, tables, and code are graph edges only.
    """

    PROSE = "prose"
    RELATED_NOTES = "related_notes"
    HEADING = "heading"
    TABLE = "table"
    CODE = "code"
    CITATION = "citation"
    LIST = "list"
    OTHER = "other"


class BenchmarkKind(StrEnum):
    """The seven expert-benchmark judgment types (SPEC-INLINE-LINKING §7).

    Each frozen benchmark case asserts one judgment: a natural linkable span,
    an acceptable-but-non-ideal span, a correct target, an incorrect target,
    a should-not-link case, a valid source placement, or a valid
    reverse-direction anchor.
    """

    NATURAL_SPAN = "natural_span"
    ACCEPTABLE_SPAN = "acceptable_span"
    CORRECT_TARGET = "correct_target"
    INCORRECT_TARGET = "incorrect_target"
    NO_LINK = "no_link"
    VALID_PLACEMENT = "valid_placement"
    REVERSE_DIRECTION = "reverse_direction"


def _parse_enum(enum_cls: type[_E], value: str, field_name: str, context: str) -> _E:
    """Convert a serialized string to an enum member, or raise ``ContractError``."""
    try:
        return enum_cls(value)
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_cls)
        raise ContractError(
            f"{context}: unknown {field_name} {value!r}; expected one of: {allowed}"
        ) from exc


def _nullable_span(data: dict[str, Any], field_name: str, context: str) -> Span | None:
    """Read an optional span object field (absent or null means ``None``)."""
    span_data = data.get(field_name)
    if span_data is None:
        return None
    return Span.from_dict(expect_mapping(span_data, f"{context}: field '{field_name}'"))


@dataclass(frozen=True, slots=True)
class AuditItem:
    """One sampled existing link to be labeled in the data audit.

    ``id`` is a stable fingerprint of (source id, target id, span), so an item
    keeps its identity across re-sampled audits of the same corpus snapshot.
    ``context`` is a whitespace-collapsed window of source text around the
    link; ``strata_key`` is the deterministic composite the sampler
    stratified by (region kind, anchor word-count bucket, topic family,
    source doc type), per SPEC-INLINE-LINKING §4.
    """

    id: str
    source_document_id: str
    target_document_id: str
    anchor_text: str
    source_span: Span | None
    region_kind: LinkRegionKind
    context: str
    anchor_word_count: int
    topic_family: str
    strata_key: str

    def __post_init__(self) -> None:
        if self.anchor_word_count < 0:
            raise ContractError(
                f"AuditItem {self.id!r}: anchor_word_count must be >= 0, "
                f"got {self.anchor_word_count}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "id": self.id,
            "source_document_id": self.source_document_id,
            "target_document_id": self.target_document_id,
            "anchor_text": self.anchor_text,
            "source_span": self.source_span.to_dict() if self.source_span else None,
            "region_kind": self.region_kind.value,
            "context": self.context,
            "anchor_word_count": self.anchor_word_count,
            "topic_family": self.topic_family,
            "strata_key": self.strata_key,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditItem:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "AuditItem"
        mapping = expect_mapping(data, context)
        return cls(
            id=expect_str(mapping, "id", context),
            source_document_id=expect_str(mapping, "source_document_id", context),
            target_document_id=expect_str(mapping, "target_document_id", context),
            anchor_text=expect_str(mapping, "anchor_text", context),
            source_span=_nullable_span(mapping, "source_span", context),
            region_kind=_parse_enum(
                LinkRegionKind, expect_str(mapping, "region_kind", context), "region_kind", context
            ),
            context=expect_str(mapping, "context", context),
            anchor_word_count=expect_int(mapping, "anchor_word_count", context),
            topic_family=expect_str(mapping, "topic_family", context),
            strata_key=expect_str(mapping, "strata_key", context),
        )


@dataclass(frozen=True, slots=True)
class AuditLabel:
    """One annotator's judgment of one :class:`AuditItem`.

    Implements the label schema of SPEC-INLINE-LINKING §4: target
    correctness, anchor naturalness, placement validity, and the resulting
    supervision tier. ``labeled_at`` is an ISO-8601 timestamp string (empty
    only for hand-constructed labels).
    """

    item_id: str
    annotator: str
    target_correct: bool
    anchor_natural: bool
    placement_valid: bool
    tier: Tier
    note: str = ""
    labeled_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "item_id": self.item_id,
            "annotator": self.annotator,
            "target_correct": self.target_correct,
            "anchor_natural": self.anchor_natural,
            "placement_valid": self.placement_valid,
            "tier": self.tier.value,
            "note": self.note,
            "labeled_at": self.labeled_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditLabel:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "AuditLabel"
        mapping = expect_mapping(data, context)
        return cls(
            item_id=expect_str(mapping, "item_id", context),
            annotator=expect_str(mapping, "annotator", context),
            target_correct=expect_bool(mapping, "target_correct", context),
            anchor_natural=expect_bool(mapping, "anchor_natural", context),
            placement_valid=expect_bool(mapping, "placement_valid", context),
            tier=_parse_enum(Tier, expect_str(mapping, "tier", context), "tier", context),
            note=expect_str(mapping, "note", context, default=""),
            labeled_at=expect_str(mapping, "labeled_at", context, default=""),
        )


def _check_review_domain(value: str, allowed: frozenset[str], field_name: str) -> None:
    """Validate a review-decision string field against its closed domain."""
    if value not in allowed:
        expected = ", ".join(sorted(allowed))
        raise ContractError(
            f"InlineReviewDecision: unknown {field_name} {value!r}; expected one of: {expected}"
        )


@dataclass(frozen=True, slots=True)
class InlineReviewDecision:
    """One human judgment of one engine proposal from the 160-item review.

    Unlike an :class:`AuditLabel` (which grades an *existing* link through
    the tier taxonomy), a review decision grades a *proposed* link with
    per-head ground truth: ``target_ok``, ``anchor_ok``, and ``placement_ok``
    answer the three head questions directly, ``verdict`` is the overall
    accept/reject call, and ``reason`` names the primary failure mode from
    the closed :data:`REVIEW_REASONS` taxonomy. ``span`` indexes the raw
    source document content — the same coordinate system as audit items and
    span candidates — and is already a plain-text anchor span (it came from
    an engine proposal, never from wikilink markup, so it must NOT be
    narrowed). ``combined_score`` is the engine's combined score at review
    time, kept so review outcomes can calibrate the score scale.

    Domains (``engine``/``verdict``/``reason``) are validated at
    construction, so a hand-built decision is as strict as a deserialized
    one.
    """

    engine: str
    source_document_id: str
    span: Span
    anchor_text: str
    target_document_id: str
    verdict: str
    target_ok: bool
    anchor_ok: bool
    placement_ok: bool
    reason: str
    note: str
    combined_score: float

    def __post_init__(self) -> None:
        _check_review_domain(self.engine, REVIEW_ENGINES, "engine")
        _check_review_domain(self.verdict, REVIEW_VERDICTS, "verdict")
        _check_review_domain(self.reason, REVIEW_REASONS, "reason")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the review-file wire format (see :meth:`from_dict`)."""
        return {
            "engine": self.engine,
            "source": self.source_document_id,
            "target": self.target_document_id,
            "anchor": self.anchor_text,
            "start": self.span.start,
            "end": self.span.end,
            "score": self.combined_score,
            "verdict": self.verdict,
            "target_ok": self.target_ok,
            "anchor_ok": self.anchor_ok,
            "placement_ok": self.placement_ok,
            "reason": self.reason,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InlineReviewDecision:
        """Deserialize from the review-file wire format (``decisions.jsonl``).

        The wire format uses the review tool's short key names, mapped onto
        the canonical fields here: ``source`` -> ``source_document_id``,
        ``target`` -> ``target_document_id``, ``anchor`` -> ``anchor_text``,
        ``start``/``end`` -> ``span`` (character offsets into the raw source
        document content), and ``score`` -> ``combined_score``. The file's
        ``id`` (truncated proposal id), ``flag``, and ``rank`` keys are
        informational review-session bookkeeping and are ignored. Raises
        :class:`~linkdiscovery.errors.ContractError` on missing fields,
        wrong types, or out-of-domain ``engine``/``verdict``/``reason``
        values.
        """
        context = "InlineReviewDecision"
        mapping = expect_mapping(data, context)
        return cls(
            engine=expect_str(mapping, "engine", context),
            source_document_id=expect_str(mapping, "source", context),
            span=Span(
                start=expect_int(mapping, "start", context),
                end=expect_int(mapping, "end", context),
            ),
            anchor_text=expect_str(mapping, "anchor", context),
            target_document_id=expect_str(mapping, "target", context),
            verdict=expect_str(mapping, "verdict", context),
            target_ok=expect_bool(mapping, "target_ok", context),
            anchor_ok=expect_bool(mapping, "anchor_ok", context),
            placement_ok=expect_bool(mapping, "placement_ok", context),
            reason=expect_str(mapping, "reason", context),
            note=expect_str(mapping, "note", context, default=""),
            combined_score=expect_float(mapping, "score", context),
        )


@dataclass(frozen=True, slots=True)
class AuditSample:
    """The stratified audit sample: an artifact-level contract.

    ``strata_counts`` records how many items were selected per strata key,
    so the report can show which strata were thin. Invariant (enforced at
    construction): item IDs are unique.
    """

    header: ArtifactHeader
    items: tuple[AuditItem, ...] = ()
    strata_counts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for item in self.items:
            if item.id in seen:
                raise ContractError(f"AuditSample: duplicate item id {item.id!r}")
            seen.add(item.id)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "header": self.header.to_dict(),
            "items": [item.to_dict() for item in self.items],
            "strata_counts": dict(self.strata_counts),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditSample:
        """Deserialize, raising ``ContractError`` on invalid or unknown-version input."""
        context = "AuditSample"
        mapping = expect_mapping(data, context)
        header = expect_header(mapping, context)
        check_schema_version(header, SCHEMA_VERSION, context)
        items = expect_list(mapping, "items", context, default=[])
        return cls(
            header=header,
            items=tuple(
                AuditItem.from_dict(expect_mapping(item, f"{context}: field 'items[{index}]'"))
                for index, item in enumerate(items)
            ),
            strata_counts=expect_str_int_map(mapping, "strata_counts", context, default={}),
        )


@dataclass(frozen=True, slots=True)
class AuditReport:
    """The result of the data audit: an artifact-level contract.

    ``agreement`` carries per-field Cohen's kappa and Krippendorff's alpha
    values (keys such as ``kappa_anchor_natural`` or ``alpha_tier``); ``go``
    is the SPEC-INLINE-LINKING §4 go/no-go decision (kappa >= 0.6 and >= 150
    clean Tier A+B positives); ``notes`` states, honestly, anything that
    limits the decision (single annotator, unlabeled items, thin strata).
    """

    header: ArtifactHeader
    n_items: int
    n_labeled: int
    tier_counts: dict[str, int] = field(default_factory=dict)
    agreement: dict[str, float] = field(default_factory=dict)
    go: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.n_items < 0 or self.n_labeled < 0:
            raise ContractError(
                f"AuditReport: n_items and n_labeled must be >= 0, "
                f"got {self.n_items} and {self.n_labeled}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "header": self.header.to_dict(),
            "n_items": self.n_items,
            "n_labeled": self.n_labeled,
            "tier_counts": dict(self.tier_counts),
            "agreement": dict(self.agreement),
            "go": self.go,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditReport:
        """Deserialize, raising ``ContractError`` on invalid or unknown-version input."""
        context = "AuditReport"
        mapping = expect_mapping(data, context)
        header = expect_header(mapping, context)
        check_schema_version(header, SCHEMA_VERSION, context)
        return cls(
            header=header,
            n_items=expect_int(mapping, "n_items", context),
            n_labeled=expect_int(mapping, "n_labeled", context),
            tier_counts=expect_str_int_map(mapping, "tier_counts", context, default={}),
            agreement=expect_str_float_map(mapping, "agreement", context, default={}),
            go=expect_bool(mapping, "go", context, default=False),
            notes=expect_str_tuple(mapping, "notes", context, default=()),
        )


@dataclass(frozen=True, slots=True)
class SpanCandidate:
    """A candidate anchor span in a source document.

    Produced by the span-proposal stage (SPEC-INLINE-LINKING §1, §3):
    ``span`` indexes the raw source content, ``unit_id`` optionally names the
    semantic unit the span falls in, and ``features`` carries hand features
    (keyphraseness, casing, region signals) consumed by the naturalness head.
    """

    id: str
    document_id: str
    unit_id: str | None
    span: Span
    text: str
    region_kind: LinkRegionKind
    word_count: int
    features: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.word_count < 0:
            raise ContractError(
                f"SpanCandidate {self.id!r}: word_count must be >= 0, got {self.word_count}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "unit_id": self.unit_id,
            "span": self.span.to_dict(),
            "text": self.text,
            "region_kind": self.region_kind.value,
            "word_count": self.word_count,
            "features": dict(self.features),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpanCandidate:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "SpanCandidate"
        mapping = expect_mapping(data, context)
        return cls(
            id=expect_str(mapping, "id", context),
            document_id=expect_str(mapping, "document_id", context),
            unit_id=expect_nullable_str(mapping, "unit_id", context),
            span=Span.from_dict(expect_mapping(mapping.get("span"), f"{context}: field 'span'")),
            text=expect_str(mapping, "text", context),
            region_kind=_parse_enum(
                LinkRegionKind, expect_str(mapping, "region_kind", context), "region_kind", context
            ),
            word_count=expect_int(mapping, "word_count", context),
            features=expect_str_float_map(mapping, "features", context, default={}),
        )


@dataclass(frozen=True, slots=True)
class InlineProposal:
    """The subsystem's end product: a proposed inline link with three head scores.

    Per SPEC-INLINE-LINKING §6, the three heads (anchor naturalness, target
    correctness, placement validity) stay explicitly separate and are
    combined only at global selection, so a target-correct-but-anchor-wrong
    case remains expressible. ``calibrated_probability`` is the
    temperature-scaled (or conformal) accept probability, ``None`` before
    calibration; ``abstained`` records the no-link rejection decision.
    """

    id: str
    source_document_id: str
    span: Span
    anchor_text: str
    target_document_id: str
    target_section: str | None
    naturalness: float
    target_correctness: float
    placement_validity: float
    combined_score: float
    calibrated_probability: float | None = None
    abstained: bool = False
    features: dict[str, float] = field(default_factory=dict)
    model_version: str = ""
    review: ReviewState = field(default_factory=ReviewState)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "id": self.id,
            "source_document_id": self.source_document_id,
            "span": self.span.to_dict(),
            "anchor_text": self.anchor_text,
            "target_document_id": self.target_document_id,
            "target_section": self.target_section,
            "naturalness": self.naturalness,
            "target_correctness": self.target_correctness,
            "placement_validity": self.placement_validity,
            "combined_score": self.combined_score,
            "calibrated_probability": self.calibrated_probability,
            "abstained": self.abstained,
            "features": dict(self.features),
            "model_version": self.model_version,
            "review": self.review.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InlineProposal:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "InlineProposal"
        mapping = expect_mapping(data, context)
        review_data = mapping.get("review")
        review = (
            ReviewState.from_dict(expect_mapping(review_data, f"{context}: field 'review'"))
            if review_data is not None
            else ReviewState()
        )
        return cls(
            id=expect_str(mapping, "id", context),
            source_document_id=expect_str(mapping, "source_document_id", context),
            span=Span.from_dict(expect_mapping(mapping.get("span"), f"{context}: field 'span'")),
            anchor_text=expect_str(mapping, "anchor_text", context),
            target_document_id=expect_str(mapping, "target_document_id", context),
            target_section=expect_nullable_str(mapping, "target_section", context),
            naturalness=expect_float(mapping, "naturalness", context),
            target_correctness=expect_float(mapping, "target_correctness", context),
            placement_validity=expect_float(mapping, "placement_validity", context),
            combined_score=expect_float(mapping, "combined_score", context),
            calibrated_probability=expect_nullable_float(
                mapping, "calibrated_probability", context
            ),
            abstained=expect_bool(mapping, "abstained", context, default=False),
            features=expect_str_float_map(mapping, "features", context, default={}),
            model_version=expect_str(mapping, "model_version", context, default=""),
            review=review,
        )


@dataclass(frozen=True, slots=True)
class InlineProposalSet:
    """The inline proposals of one run: an artifact-level contract.

    Invariant (enforced at construction): proposal IDs are unique. Order
    follows the global selection policy (budget and diversity applied), but
    abstained proposals are kept rather than deleted so the rejection
    decision stays auditable.
    """

    header: ArtifactHeader
    proposals: tuple[InlineProposal, ...] = ()

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for proposal in self.proposals:
            if proposal.id in seen:
                raise ContractError(f"InlineProposalSet: duplicate proposal id {proposal.id!r}")
            seen.add(proposal.id)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "header": self.header.to_dict(),
            "proposals": [proposal.to_dict() for proposal in self.proposals],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InlineProposalSet:
        """Deserialize, raising ``ContractError`` on invalid or unknown-version input."""
        context = "InlineProposalSet"
        mapping = expect_mapping(data, context)
        header = expect_header(mapping, context)
        check_schema_version(header, SCHEMA_VERSION, context)
        proposals = expect_list(mapping, "proposals", context, default=[])
        return cls(
            header=header,
            proposals=tuple(
                InlineProposal.from_dict(
                    expect_mapping(item, f"{context}: field 'proposals[{index}]'")
                )
                for index, item in enumerate(proposals)
            ),
        )


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """One frozen expert-benchmark judgment (SPEC-INLINE-LINKING §7).

    ``expected`` states whether the judged property holds (for example, a
    ``no_link`` case with ``expected=True`` asserts the span must NOT be
    linked); ``hard_case`` marks the over-sampled difficult categories
    (different-vocabulary neighbors, code-heavy notes, generic anchors).
    ``span`` and ``target_document_id`` are nullable because some judgment
    kinds have no span (document-level) or no target (no-link cases).
    """

    id: str
    kind: BenchmarkKind
    source_document_id: str
    span: Span | None
    anchor_text: str
    target_document_id: str | None
    expected: bool
    hard_case: bool = False
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "id": self.id,
            "kind": self.kind.value,
            "source_document_id": self.source_document_id,
            "span": self.span.to_dict() if self.span else None,
            "anchor_text": self.anchor_text,
            "target_document_id": self.target_document_id,
            "expected": self.expected,
            "hard_case": self.hard_case,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkCase:
        """Deserialize, raising ``ContractError`` on invalid input."""
        context = "BenchmarkCase"
        mapping = expect_mapping(data, context)
        return cls(
            id=expect_str(mapping, "id", context),
            kind=_parse_enum(BenchmarkKind, expect_str(mapping, "kind", context), "kind", context),
            source_document_id=expect_str(mapping, "source_document_id", context),
            span=_nullable_span(mapping, "span", context),
            anchor_text=expect_str(mapping, "anchor_text", context),
            target_document_id=expect_nullable_str(mapping, "target_document_id", context),
            expected=expect_bool(mapping, "expected", context),
            hard_case=expect_bool(mapping, "hard_case", context, default=False),
            note=expect_str(mapping, "note", context, default=""),
        )


@dataclass(frozen=True, slots=True)
class Benchmark:
    """The frozen expert benchmark: an artifact-level contract.

    Never trained on (SPEC-INLINE-LINKING §7: "untouched during
    development"). Invariant (enforced at construction): case IDs are unique.
    """

    header: ArtifactHeader
    cases: tuple[BenchmarkCase, ...] = ()

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for case in self.cases:
            if case.id in seen:
                raise ContractError(f"Benchmark: duplicate case id {case.id!r}")
            seen.add(case.id)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe primitives."""
        return {
            "header": self.header.to_dict(),
            "cases": [case.to_dict() for case in self.cases],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Benchmark:
        """Deserialize, raising ``ContractError`` on invalid or unknown-version input."""
        context = "Benchmark"
        mapping = expect_mapping(data, context)
        header = expect_header(mapping, context)
        check_schema_version(header, SCHEMA_VERSION, context)
        cases = expect_list(mapping, "cases", context, default=[])
        return cls(
            header=header,
            cases=tuple(
                BenchmarkCase.from_dict(expect_mapping(item, f"{context}: field 'cases[{index}]'"))
                for index, item in enumerate(cases)
            ),
        )
