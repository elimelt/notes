"""Deterministic baseline engine for inline-link proposals.

This is the SPEC-INLINE-LINKING §12 kill-criterion fallback and the
Recommendations-section safety net: "Fall back to the deterministic
keyphraseness + anchor-dictionary + bi-encoder baseline (essentially the
Wikimedia XGBoost feature model: ngram length, anchor-target frequency,
ambiguity, Levenshtein, embedding similarity) as the review-tool engine."
Every score is an explicit hand formula over those signals — no learned
parameters — so the engine works with zero training data and serves as the
floor any learned model must beat.

Division of labor: :func:`propose_baseline` emits one draft
:class:`~linkdiscovery.inline.records.InlineProposal` per candidate span
(best target only) and performs **no selection**. Per-note budgets, MMR
diversity, and accept thresholds (SPEC §7 Q31, §10) belong to the select
stage, which consumes these drafts; keeping the three head scores separate
here is what lets selection express the target-correct-but-anchor-wrong
case (SPEC §6 Q24-25).

Decoupling note: this module never imports the anchor-dictionary or span
stages. It consumes plain ``SpanCandidate`` sequences, a ``target_lookup``
callable, target vectors, and titles, and reads hand features with
``features.get(name, 0.0)``, so it stays buildable and testable while those
stages evolve.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from linkdiscovery.errors import ConfigError
from linkdiscovery.fingerprint import fingerprint
from linkdiscovery.inline.records import InlineProposal, LinkRegionKind

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from numpy.typing import NDArray

    from linkdiscovery.inline.records import SpanCandidate

__all__ = [
    "BaselineConfig",
    "levenshtein_ratio",
    "propose_baseline",
    "score_baseline",
]

_WORD_SWEET_LOW = 2
"""Lower bound of the anchor word-count sweet spot (2-3 word anchors)."""

_WORD_SWEET_HIGH = 3
"""Upper bound of the anchor word-count sweet spot (2-3 word anchors)."""

_COMBINE_EXPONENT = 1.0 / 3.0
"""Geometric-mean exponent combining the three head scores."""


def _clamp01(value: float) -> float:
    """Clamp a value into ``[0, 1]``."""
    return min(1.0, max(0.0, value))


def _normalize_text(text: str) -> str:
    """Casefold and whitespace-collapse text for title/mention comparison."""
    return " ".join(text.split()).casefold()


@dataclass(frozen=True, slots=True)
class BaselineConfig:
    """Hand weights for the deterministic baseline (documented defaults).

    Naturalness head: ``keyphraseness_weight`` vs ``match_weight`` mix the
    corpus keyphraseness signal (normalized by ``keyphraseness_saturation``,
    the link-probability treated as maximal — the Milne-Witten eligibility
    floor is ~0.065, SPEC §10, so 0.30 is deep into "clearly linkable")
    against exact title/alias matches; the mix is scaled by a word-count
    factor with a 2-3-word sweet spot (``single_word_factor`` for 1-word
    anchors, decay ``long_span_decay`` per word past 3 down to
    ``long_span_floor``).

    Target head: ``commonness_weight`` / ``embedding_weight`` /
    ``levenshtein_weight`` mix the anchor-dictionary commonness prior, the
    bi-encoder cosine similarity, and the normalized Levenshtein similarity
    to the target title; the mix is discounted by ``1/(1 + ln(ambiguity))``.
    ``cross_family_penalty`` is the topic-family consistency prior for
    generic anchors (2026-08-01 report failure mode 2): when the caller
    supplies a ``same_family`` signal, target correctness is further scaled
    by ``1 - cross_family_penalty * (1 - same_family)`` — a full-strength
    discount for a cross-family target, none for a same-family one.
    Proper-name-shaped anchors are exempted upstream (they name globally
    unique concepts, and cross-family links through them are exactly the
    valuable novel connections). Note this field enters ``resolved_dict``
    and therefore changes the config fingerprint and ``model_version`` of
    every draft — intended, since the scores change.

    Placement head: prose spans score ``1 - position_penalty *
    sentence_position``; non-prose spans floor at ``non_prose_placement``
    (SPEC §4: non-prose links are graph edges, not anchor examples — the
    small floor keeps drafts rankable instead of annihilating the geometric
    mean).

    ``top_k_targets`` caps how many dictionary/title targets are scored per
    span (SPEC §9: "cap candidates per span (e.g., top-10 targets)").
    """

    keyphraseness_weight: float = 0.7
    match_weight: float = 0.3
    keyphraseness_saturation: float = 0.3
    single_word_factor: float = 0.7
    long_span_decay: float = 0.15
    long_span_floor: float = 0.3
    commonness_weight: float = 0.4
    embedding_weight: float = 0.35
    levenshtein_weight: float = 0.25
    cross_family_penalty: float = 0.35
    position_penalty: float = 0.25
    non_prose_placement: float = 0.05
    top_k_targets: int = 5

    def __post_init__(self) -> None:
        for name in (
            "keyphraseness_weight",
            "match_weight",
            "commonness_weight",
            "embedding_weight",
            "levenshtein_weight",
            "long_span_decay",
        ):
            value = getattr(self, name)
            if value < 0.0:
                raise ConfigError(f"BaselineConfig: field '{name}' must be >= 0, got {value}")
        for name in (
            "single_word_factor",
            "long_span_floor",
            "cross_family_penalty",
            "position_penalty",
            "non_prose_placement",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ConfigError(f"BaselineConfig: field '{name}' must be in [0, 1], got {value}")
        if self.keyphraseness_saturation <= 0.0:
            raise ConfigError(
                f"BaselineConfig: field 'keyphraseness_saturation' must be > 0, "
                f"got {self.keyphraseness_saturation}"
            )
        if self.keyphraseness_weight + self.match_weight <= 0.0:
            raise ConfigError("BaselineConfig: keyphraseness_weight + match_weight must be > 0")
        if self.commonness_weight + self.embedding_weight + self.levenshtein_weight <= 0.0:
            raise ConfigError(
                "BaselineConfig: commonness_weight + embedding_weight + "
                "levenshtein_weight must be > 0"
            )
        if self.top_k_targets < 1:
            raise ConfigError(
                f"BaselineConfig: field 'top_k_targets' must be >= 1, got {self.top_k_targets}"
            )

    def resolved_dict(self) -> dict[str, Any]:
        """Return the fully resolved (defaults filled) JSON-safe form."""
        return {
            "keyphraseness_weight": self.keyphraseness_weight,
            "match_weight": self.match_weight,
            "keyphraseness_saturation": self.keyphraseness_saturation,
            "single_word_factor": self.single_word_factor,
            "long_span_decay": self.long_span_decay,
            "long_span_floor": self.long_span_floor,
            "commonness_weight": self.commonness_weight,
            "embedding_weight": self.embedding_weight,
            "levenshtein_weight": self.levenshtein_weight,
            "cross_family_penalty": self.cross_family_penalty,
            "position_penalty": self.position_penalty,
            "non_prose_placement": self.non_prose_placement,
            "top_k_targets": self.top_k_targets,
        }

    def fingerprint(self) -> str:
        """Fingerprint of the resolved config, embedded in ``model_version``."""
        return fingerprint(self.resolved_dict())


def levenshtein_ratio(a: str, b: str) -> float:
    """Normalized Levenshtein similarity: ``1 - distance / max(len(a), len(b))``.

    Classic O(len(a) x len(b)) dynamic program with unit insert/delete/
    substitute costs — fine at anchor/title sizes, and dependency-free. Two
    empty strings are identical (1.0); one empty string against a non-empty
    one shares nothing (0.0). Example: ``levenshtein_ratio("kitten",
    "sitting")`` is ``1 - 3/7``.
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    previous = list(range(len(b) + 1))
    for row, char_a in enumerate(a, start=1):
        current = [row]
        for column, char_b in enumerate(b, start=1):
            substitution = previous[column - 1] + (0 if char_a == char_b else 1)
            current.append(min(previous[column] + 1, current[column - 1] + 1, substitution))
        previous = current
    return 1.0 - previous[-1] / max(len(a), len(b))


def _word_count_factor(word_count: int, config: BaselineConfig) -> float:
    """Word-count sweet-spot factor: 1.0 at 2-3 words, discounted elsewhere."""
    if _WORD_SWEET_LOW <= word_count <= _WORD_SWEET_HIGH:
        return 1.0
    if word_count < _WORD_SWEET_LOW:
        return config.single_word_factor
    return max(
        config.long_span_floor,
        1.0 - config.long_span_decay * (word_count - _WORD_SWEET_HIGH),
    )


def score_baseline(  # noqa: PLR0913 -- explicit hand-formula inputs, fixed by the spec
    candidate: SpanCandidate,
    target_id: str,
    *,
    commonness: float,
    target_vector_sim: float,
    ambiguity: int,
    levenshtein_title: float,
    same_family: float | None = None,
    config: BaselineConfig,
) -> tuple[float, float, float]:
    """Score one (span, target) pair with three explicit hand formulas.

    Returns ``(naturalness, target_correctness, placement_validity)``, each
    in ``[0, 1]``, mirroring the three separate heads of SPEC §6 Q24-25.
    ``target_id`` is carried for traceability only; all target-side signals
    arrive pre-computed as keyword arguments so this module stays decoupled
    from the anchor-dictionary and retrieval stages.

    - **Naturalness** = ``word_factor * (w_kp * kp + w_match * match) /
      (w_kp + w_match)`` where ``kp`` is the ``keyphraseness`` feature
      clamped after division by ``keyphraseness_saturation``, ``match`` is 1
      when the ``is_title_match`` or ``is_alias_match`` feature fires, and
      ``word_factor`` implements the 2-3-word sweet spot. Monotone
      non-decreasing in keyphraseness.
    - **Target correctness** = ``(w_c * commonness + w_e * cos + w_l * lev)
      / (w_c + w_e + w_l) * 1 / (1 + ln(max(ambiguity, 1)))`` — the
      anchor-dictionary commonness prior, the bi-encoder cosine (negative
      cosines clamp to 0), and the normalized Levenshtein similarity to the
      target title, discounted logarithmically by how many targets compete
      for the mention. When ``same_family`` is not ``None``, the result is
      then multiplied by ``1 - cross_family_penalty * (1 -
      clamp01(same_family))`` — the topic-family consistency prior for
      family-polysemous anchors ("memory management" means different things
      in OS notes and LLM-serving notes). ``None`` means "unknown or exempt
      — no penalty". Monotone non-increasing in ambiguity and monotone
      non-decreasing in ``same_family``.
    - **Placement validity** = ``prose * (1 - position_penalty *
      sentence_position)``, floored at ``non_prose_placement``; ``prose`` is
      1 for :attr:`~linkdiscovery.inline.records.LinkRegionKind.PROSE` spans
      and otherwise falls back to the ``region_prose`` feature (SPEC §4:
      non-prose regions are graph edges, not anchor placements).

    Missing hand features default to 0.0 via ``features.get``.
    """
    features = candidate.features

    keyphraseness = _clamp01(features.get("keyphraseness", 0.0) / config.keyphraseness_saturation)
    is_match = (
        features.get("is_title_match", 0.0) > 0.0 or features.get("is_alias_match", 0.0) > 0.0
    )
    naturalness_weights = config.keyphraseness_weight + config.match_weight
    naturalness_mix = (
        config.keyphraseness_weight * keyphraseness + config.match_weight * float(is_match)
    ) / naturalness_weights
    naturalness = _clamp01(naturalness_mix * _word_count_factor(candidate.word_count, config))

    target_weights = config.commonness_weight + config.embedding_weight + config.levenshtein_weight
    target_mix = (
        config.commonness_weight * _clamp01(commonness)
        + config.embedding_weight * _clamp01(target_vector_sim)
        + config.levenshtein_weight * _clamp01(levenshtein_title)
    ) / target_weights
    ambiguity_discount = 1.0 / (1.0 + math.log(max(ambiguity, 1)))
    target_correctness = _clamp01(target_mix * ambiguity_discount)
    if same_family is not None:
        family_factor = 1.0 - config.cross_family_penalty * (1.0 - _clamp01(same_family))
        target_correctness = _clamp01(target_correctness * family_factor)

    if candidate.region_kind is LinkRegionKind.PROSE:
        prose = 1.0
    else:
        prose = _clamp01(features.get("region_prose", 0.0))
    position = _clamp01(features.get("sentence_position", 0.0))
    placement_validity = _clamp01(
        max(prose * (1.0 - config.position_penalty * position), config.non_prose_placement)
    )

    return naturalness, target_correctness, placement_validity


def _cosine(a: NDArray[np.float32] | None, b: NDArray[np.float32] | None) -> float:
    """Cosine similarity, 0.0 when either vector is absent or zero-norm.

    Raises ``ValueError`` on a dimensionality mismatch — that is a wiring
    bug between the span embedder and the target vector table, not data.
    """
    if a is None or b is None:
        return 0.0
    vector_a = np.asarray(a, dtype=np.float32).ravel()
    vector_b = np.asarray(b, dtype=np.float32).ravel()
    if vector_a.shape != vector_b.shape:
        raise ValueError(
            f"cosine similarity requires equal dimensions, "
            f"got {vector_a.shape[0]} and {vector_b.shape[0]}"
        )
    norm_a = float(np.linalg.norm(vector_a))
    norm_b = float(np.linalg.norm(vector_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(vector_a, vector_b) / (norm_a * norm_b))


def _shortlist_targets(
    counts: Mapping[str, int], title_matches: frozenset[str], targets: set[str], top_k: int
) -> list[str]:
    """The top-``k`` targets by dictionary count, title matches preferred on ties."""
    prerank = sorted(
        (-counts.get(target_id, 0), 0 if target_id in title_matches else 1, target_id)
        for target_id in targets
    )
    return [target_id for _, _, target_id in prerank[:top_k]]


@dataclass(frozen=True, slots=True)
class _ProposalContext:
    """Shared read-only inputs threaded through per-candidate scoring.

    ``families`` optionally maps document ids to topic-family labels for the
    cross-family penalty; ids missing from the mapping have an unknown
    family and are never penalized.
    """

    target_lookup: Callable[[str], Mapping[str, int]]
    doc_vectors: Mapping[str, NDArray[np.float32]]
    span_vectors: Callable[[SpanCandidate], NDArray[np.float32]] | None
    titles: Mapping[str, str]
    config: BaselineConfig
    run_id: str
    corpus_id: str
    model_version: str
    families: Mapping[str, str] | None = None


def _same_family_signal(
    candidate: SpanCandidate, target_id: str, families: Mapping[str, str] | None
) -> float | None:
    """The ``same_family`` value passed to :func:`score_baseline` for one target.

    Proper-name-shaped anchors — span-stage features ``is_titlecase`` or
    ``is_acronym`` — are exempt (``None``): TitleCase/acronym anchors
    ("Paxos", "TCP", "Sharding") name globally unique concepts, and
    cross-family links through them are exactly the valuable novel
    connections. Lowercase common phrases ("memory management",
    "scheduling") are family-polysemous — the observed wrong-domain failures
    (2026-08-01 report, rank 61). ``None`` is also returned when no
    ``families`` mapping was supplied or either document's family is
    unknown; otherwise 1.0 for equal families, 0.0 for different ones.
    """
    features = candidate.features
    if features.get("is_titlecase", 0.0) > 0.0 or features.get("is_acronym", 0.0) > 0.0:
        return None
    if families is None:
        return None
    source_family = families.get(candidate.document_id)
    target_family = families.get(target_id)
    if source_family is None or target_family is None:
        return None
    return 1.0 if source_family == target_family else 0.0


def _propose_for_candidate(
    candidate: SpanCandidate,
    context: _ProposalContext,
) -> InlineProposal | None:
    """Score one span's shortlisted targets and draft its best proposal."""
    counts = dict(context.target_lookup(candidate.text))
    normalized_mention = _normalize_text(candidate.text)
    title_matches = frozenset(
        target_id
        for target_id, title in context.titles.items()
        if _normalize_text(title) == normalized_mention
    )
    targets = set(counts) | set(title_matches)
    targets.discard(candidate.document_id)  # never propose a self-link
    if not targets:
        return None

    ambiguity = len(targets)
    total_count = sum(counts.values())
    span_vector = context.span_vectors(candidate) if context.span_vectors is not None else None
    shortlist = _shortlist_targets(counts, title_matches, targets, context.config.top_k_targets)

    best: tuple[float, str, tuple[float, float, float], dict[str, float]] | None = None
    for target_id in shortlist:
        commonness = counts.get(target_id, 0) / total_count if total_count else 0.0
        similarity = _cosine(span_vector, context.doc_vectors.get(target_id))
        levenshtein_title = levenshtein_ratio(
            candidate.text.casefold(), context.titles.get(target_id, "").casefold()
        )
        same_family = _same_family_signal(candidate, target_id, context.families)
        scores = score_baseline(
            candidate,
            target_id,
            commonness=commonness,
            target_vector_sim=similarity,
            ambiguity=ambiguity,
            levenshtein_title=levenshtein_title,
            same_family=same_family,
            config=context.config,
        )
        combined = (scores[0] * scores[1] * scores[2]) ** _COMBINE_EXPONENT
        proposal_features = {
            "keyphraseness": candidate.features.get("keyphraseness", 0.0),
            "commonness": commonness,
            "embedding_similarity": similarity,
            "ambiguity": float(ambiguity),
            "levenshtein_title": levenshtein_title,
        }
        if same_family is not None:
            proposal_features["same_family"] = same_family
        key = (-combined, target_id)
        if best is None or key < (-best[0], best[1]):
            best = (combined, target_id, scores, proposal_features)

    if best is None:  # unreachable: targets is non-empty and top_k_targets >= 1
        return None
    combined, target_id, (naturalness, target_correctness, placement_validity), extras = best
    proposal_id = fingerprint(
        {
            "corpus_id": context.corpus_id,
            "run_id": context.run_id,
            "source_document_id": candidate.document_id,
            "span_start": candidate.span.start,
            "span_end": candidate.span.end,
            "target_document_id": target_id,
            "model_version": context.model_version,
        }
    )
    return InlineProposal(
        id=proposal_id,
        source_document_id=candidate.document_id,
        span=candidate.span,
        anchor_text=candidate.text,
        target_document_id=target_id,
        target_section=None,
        naturalness=naturalness,
        target_correctness=target_correctness,
        placement_validity=placement_validity,
        combined_score=combined,
        calibrated_probability=None,
        abstained=False,
        features=extras,
        model_version=context.model_version,
    )


def propose_baseline(  # noqa: PLR0913 -- stage-boundary signature fixed by the spec
    candidates_by_doc: Mapping[str, Sequence[SpanCandidate]],
    target_lookup: Callable[[str], Mapping[str, int]],
    doc_vectors: Mapping[str, NDArray[np.float32]],
    span_vectors: Callable[[SpanCandidate], NDArray[np.float32]] | None,
    titles: Mapping[str, str],
    *,
    config: BaselineConfig,
    run_id: str = "adhoc",
    corpus_id: str = "",
    families: Mapping[str, str] | None = None,
) -> tuple[InlineProposal, ...]:
    """Draft one baseline proposal per candidate span (SPEC §12 fallback).

    For each candidate: the target pool is the anchor-dictionary lookup for
    the raw span text (``target_lookup`` owns its own normalization) union
    exact normalized title matches, minus the source document itself (never
    self-link). The top ``config.top_k_targets`` targets (by dictionary
    count, title matches preferred on ties, then target id) are scored with
    :func:`score_baseline` — commonness = count / total dictionary mass for
    the mention, embedding cosine between ``span_vectors(candidate)`` and
    ``doc_vectors[target]`` (0.0 when ``span_vectors`` is ``None`` or the
    target vector is missing), ambiguity = pool size, and Levenshtein
    similarity of the casefolded span text against ``titles[target]``. The
    best target by combined score (geometric mean of the three heads, ties
    to the lexically smallest target id) becomes one draft
    :class:`~linkdiscovery.inline.records.InlineProposal` with
    ``model_version = "baseline-" + config.fingerprint()``,
    ``abstained=False``, ``calibrated_probability=None``, and a default
    (unreviewed) review state. Spans with an empty target pool draft
    nothing.

    ``families`` optionally maps document ids to topic-family labels
    (missing ids = unknown family). For anchors that are not
    proper-name-shaped, a target in a *different* family than the source is
    discounted by ``config.cross_family_penalty`` (see
    :func:`_same_family_signal` and :func:`score_baseline`); when the signal
    fires either way, the draft records feature ``same_family`` (1.0 equal /
    0.0 different).

    No selection happens here: budgets, MMR diversity, and accept
    thresholds (SPEC §7 Q31, §10) are the select stage's job, so *every*
    scoreable span yields a draft and downstream stages decide what
    surfaces. Output ordering is deterministic — documents in sorted-id
    order, candidates in their given per-document order; proposal ids are
    content fingerprints over (corpus, run, source, span, target, model),
    so identical inputs reproduce identical drafts byte for byte.
    """
    context = _ProposalContext(
        target_lookup=target_lookup,
        doc_vectors=doc_vectors,
        span_vectors=span_vectors,
        titles=titles,
        config=config,
        run_id=run_id,
        corpus_id=corpus_id,
        model_version="baseline-" + config.fingerprint(),
        families=families,
    )
    proposals: list[InlineProposal] = []
    for document_id in sorted(candidates_by_doc):
        for candidate in candidates_by_doc[document_id]:
            proposal = _propose_for_candidate(candidate, context)
            if proposal is not None:
                proposals.append(proposal)
    return tuple(proposals)
