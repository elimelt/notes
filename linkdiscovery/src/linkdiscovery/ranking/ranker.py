"""Interpretable weighted ranker (SPEC phase 4, direction, diversity, calibration).

Pipeline per :meth:`WeightedRanker.rank`:

1. **Hard filters.** Pairs referencing documents absent from the ranker's
   corpus are dropped, as are pairs where either document is empty (no unit
   with text). Pairs whose ``near_duplicate_probability`` exceeds
   :data:`NEAR_DUPLICATE_FILTER_THRESHOLD` are dropped because deduplication
   is a different action than linking (SPEC phase 3); the emptiness check runs
   first, so the near-duplicate filter only ever sees nonempty documents.
   Self-pairs, alias-equivalent pairs, and existing direct links were already
   removed by the generator — that is its contract, not re-verified here.
2. **Score** = the SPEC weighted formula over normalized features, with the
   CSLS hubness-corrected similarity as the document term (the raw
   ``document_similarity`` stays in the output features), clipped to
   ``[0, 1]``.
3. **Estimates.** ``relatedness`` blends the normalized document, best-chunk,
   and top-r similarities; ``usefulness`` squashes breadth + bridge - hubness
   - duplication into ``[0, 1]``; ``missingness`` grows linearly with graph
   distance (``0.3`` at distance 2 up to ``1.0`` at ``>= 6``; existing direct
   links never reach the ranker, so distance 6 means no known path).
4. **Confidence.** With no usable feedback, fixed thresholds over the quality
   signal ``relatedness * usefulness`` assign bands. With at least
   :data:`CALIBRATION_MIN_DECISIONS` accept/reject decisions joinable to the
   current proposals by ID (proposal IDs are stable across identical runs),
   thresholds are calibrated: matched proposals are sorted by quality and
   split into deciles, and the HIGH (MEDIUM) band extends down through every
   leading decile whose acceptance rate stays at or above 2/3 (1/3).
5. **Direction.** The document whose *section* unit carries the clearest
   placement evidence hosts the link: the generator's directional features
   (best section-to-other-document-view similarity per side) are compared, and
   the stronger side wins. If they differ by at most
   :data:`DIRECTION_EPSILON`, the features are unavailable, or the pair's
   evidence comes only from document/title views, the proposal is
   ``undirected``.
6. **Evidence.** The top :data:`MAX_EVIDENCE` unit matches become
   :class:`~linkdiscovery.contracts.proposals.Evidence` records with source
   spans looked up from the corpus; an unknown unit yields empty spans and a
   logged warning, never a crash.
7. **Diversity.** Maximal marginal relevance per source document with
   ``lambda = 1 - config.diversity`` over target lexical signatures reorders
   presentation only; membership is decided before MMR runs. The
   ``results_per_document`` cap is the configured presentation bound applied
   after MMR ordering.
8. **Total order.** Proposals are ordered by ``(position within their source
   document's MMR ordering, score descending, source ID, target ID)``; the
   1-based index in that order is the global ``rank``. This preserves each
   document's diversity ordering while ranking across documents by score.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.contracts.proposals import (
    SCHEMA_VERSION,
    Confidence,
    Evidence,
    LinkProposal,
    ProposalSet,
    ReviewState,
)
from linkdiscovery.contracts.reviews import DecisionKind
from linkdiscovery.fingerprint import combine_fingerprints, fingerprint
from linkdiscovery.ranking.features import (
    NORMALIZATION_CONSTANTS,
    NORMALIZATION_VERSION,
    clamp01,
    cross_neighborhood_value,
    graph_redundancy,
    hubness_penalty,
    normalize_features,
)

if TYPE_CHECKING:
    from linkdiscovery.config import RankingConfig
    from linkdiscovery.contracts.candidates import CandidatePair, CandidateSet
    from linkdiscovery.contracts.reviews import ReviewHistory
    from linkdiscovery.contracts.units import ProcessedCorpus, SemanticUnit, Span

__all__ = [
    "CALIBRATION_MIN_DECISIONS",
    "DIRECTION_EPSILON",
    "MAX_EVIDENCE",
    "NEAR_DUPLICATE_FILTER_THRESHOLD",
    "RANKER_VERSION",
    "WeightedRanker",
]

_LOGGER = logging.getLogger(__name__)

RANKER_VERSION = "weighted-ranker-v1"
"""Version of this ranker's policy; part of ``ranking_version``."""

NEAR_DUPLICATE_FILTER_THRESHOLD = 0.98
"""Pairs above this ``near_duplicate_probability`` are dedup work, not links."""

DIRECTION_EPSILON = 0.02
"""Directional-evidence gap below which a proposal stays undirected."""

MAX_EVIDENCE = 3
"""Supporting unit matches attached to each proposal."""

CALIBRATION_MIN_DECISIONS = 20
"""Matched accept/reject decisions required before calibration replaces fixed bands."""

FIXED_HIGH_THRESHOLD = 0.45
"""Uncalibrated quality (relatedness * usefulness) threshold for HIGH."""

FIXED_MEDIUM_THRESHOLD = 0.25
"""Uncalibrated quality threshold for MEDIUM."""

CALIBRATION_HIGH_ACCEPT_RATE = 2.0 / 3.0
"""Observed acceptance rate a decile must sustain to extend the HIGH band."""

CALIBRATION_MEDIUM_ACCEPT_RATE = 1.0 / 3.0
"""Observed acceptance rate a decile must sustain to extend the MEDIUM band."""

_CALIBRATION_DECILES = 10

_SECTION_VIEW = "section"
_MIN_LEXICAL_TOKEN_LENGTH = 3
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

_RELATEDNESS_DOCUMENT_WEIGHT = 0.4
_RELATEDNESS_CHUNK_WEIGHT = 0.4
_RELATEDNESS_TOP_R_WEIGHT = 0.2

_USEFULNESS_BASE = 0.5
_USEFULNESS_BREADTH_WEIGHT = 0.25
_USEFULNESS_BRIDGE_WEIGHT = 0.25
_USEFULNESS_HUB_WEIGHT = 0.25
_USEFULNESS_DUPLICATE_WEIGHT = 0.5

_MISSINGNESS_BASE = 0.3
_MISSINGNESS_SLOPE = 0.175
_MISSINGNESS_PIVOT = 2.0
_MISSINGNESS_FLOOR = 0.1


@dataclass
class _Scored:
    """One surviving pair with everything needed to emit a proposal."""

    pair: CandidatePair
    direction: str
    score: float
    quality: float
    features: dict[str, float]
    evidence: tuple[Evidence, ...]
    proposal_id: str
    group_position: int = field(default=0)


def _missingness(graph_distance: float) -> float:
    """Confidence that the relationship is absent, from graph distance alone."""
    value = _MISSINGNESS_BASE + _MISSINGNESS_SLOPE * (graph_distance - _MISSINGNESS_PIVOT)
    return min(max(value, _MISSINGNESS_FLOOR), 1.0)


def _tokenize(text: str) -> frozenset[str]:
    """Lowercased word 1-grams of length >= 3 (matches the generator's policy)."""
    return frozenset(
        token
        for token in _TOKEN_PATTERN.findall(text.lower())
        if len(token) >= _MIN_LEXICAL_TOKEN_LENGTH
    )


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    union = len(left | right)
    return len(left & right) / union if union else 0.0


def _split_deciles(count: int) -> list[int]:
    """Sizes of ``_CALIBRATION_DECILES`` contiguous buckets covering ``count`` items."""
    base, remainder = divmod(count, _CALIBRATION_DECILES)
    return [base + (1 if index < remainder else 0) for index in range(_CALIBRATION_DECILES)]


def _calibrated_thresholds(matched: list[tuple[float, bool]]) -> tuple[float, float]:
    """Derive (high, medium) quality thresholds from matched review decisions.

    ``matched`` is sorted by quality descending. Deciles are scanned from the
    top: the HIGH band extends through every leading decile whose acceptance
    rate is at least :data:`CALIBRATION_HIGH_ACCEPT_RATE`; the MEDIUM band then
    extends through deciles at or above
    :data:`CALIBRATION_MEDIUM_ACCEPT_RATE`; the first decile below the medium
    rate stops the scan. A band with no qualifying decile gets an infinite
    threshold (the band stays empty).
    """
    high = math.inf
    medium = math.inf
    position = 0
    in_high_zone = True
    for size in _split_deciles(len(matched)):
        if size == 0:
            continue
        bucket = matched[position : position + size]
        position += size
        rate = sum(1 for _, accepted in bucket if accepted) / len(bucket)
        lowest_quality = bucket[-1][0]
        if in_high_zone:
            if rate >= CALIBRATION_HIGH_ACCEPT_RATE:
                high = lowest_quality
                continue
            in_high_zone = False
        if rate >= CALIBRATION_MEDIUM_ACCEPT_RATE:
            medium = lowest_quality
            continue
        break
    if medium is math.inf:
        medium = high
    return high, medium


def _confidence_thresholds(
    scored: list[_Scored], feedback: ReviewHistory | None
) -> tuple[float, float]:
    """(high, medium) quality thresholds: fixed, or calibrated from feedback.

    Calibration requires decisions joinable to the current proposals by ID
    (only joinable decisions carry a quality score to bucket); deferred
    decisions are ignored and the latest decision per proposal wins.
    """
    fixed = (FIXED_HIGH_THRESHOLD, FIXED_MEDIUM_THRESHOLD)
    if feedback is None:
        return fixed
    latest: dict[str, DecisionKind] = {}
    for decision in feedback.decisions:
        latest[decision.proposal_id] = decision.decision
    quality_by_id = {item.proposal_id: item.quality for item in scored}
    matched = sorted(
        (
            (quality_by_id[proposal_id], decision is DecisionKind.ACCEPT, proposal_id)
            for proposal_id, decision in latest.items()
            if proposal_id in quality_by_id
            and decision in (DecisionKind.ACCEPT, DecisionKind.REJECT)
        ),
        key=lambda item: (-item[0], item[2]),
    )
    if len(matched) < CALIBRATION_MIN_DECISIONS:
        return fixed
    return _calibrated_thresholds([(quality, accepted) for quality, accepted, _ in matched])


def _band(quality: float, thresholds: tuple[float, float]) -> Confidence:
    high, medium = thresholds
    if quality >= high:
        return Confidence.HIGH
    if quality >= medium:
        return Confidence.MEDIUM
    return Confidence.LOW


def _direction(pair: CandidatePair) -> str:
    """SPEC "Direction and placement": the side with clearer section evidence hosts.

    Uses the generator's directional features (best section-unit similarity to
    the other document's document view per side). Symmetric evidence (within
    :data:`DIRECTION_EPSILON`), missing directional features, or evidence that
    comes only from document/title views all yield ``undirected``.
    """
    if not any(match.view == _SECTION_VIEW for match in pair.matches):
        return "undirected"
    forward = pair.features.get("directional_similarity_source_to_target")
    backward = pair.features.get("directional_similarity_target_to_source")
    if forward is None or backward is None:
        return "undirected"
    if forward - backward > DIRECTION_EPSILON:
        return "source-to-target"
    if backward - forward > DIRECTION_EPSILON:
        return "target-to-source"
    return "undirected"


class WeightedRanker:
    """The SPEC's interpretable weighted ranker over normalized features.

    Implements the :class:`~linkdiscovery.interfaces.Ranker` protocol. The
    constructor takes the processed corpus because evidence spans, document
    emptiness, and diversity signatures come from unit texts; the ``rank``
    signature itself stays exactly as the protocol defines it.
    """

    def __init__(
        self,
        corpus: ProcessedCorpus,
        *,
        run_id: str = "adhoc",
        producer_version: str = "linkdiscovery/0.1.0",
    ) -> None:
        """Index the corpus once; instances are reusable across rank() calls."""
        self._run_id = run_id
        self._producer_version = producer_version
        self._units_by_id: dict[str, SemanticUnit] = {}
        self._units_by_doc: dict[str, tuple[SemanticUnit, ...]] = {}
        for document in corpus.documents:
            self._units_by_doc[document.document_id] = document.units
            for unit in document.units:
                self._units_by_id[unit.id] = unit
        self._nonempty_docs = frozenset(
            document_id
            for document_id, units in self._units_by_doc.items()
            if any(unit.text.strip() for unit in units)
        )
        self._token_cache: dict[str, frozenset[str]] = {}

    def rank(
        self,
        candidates: CandidateSet,
        config: RankingConfig,
        feedback: ReviewHistory | None = None,
    ) -> ProposalSet:
        """Filter, score, calibrate, and order candidates into proposals."""
        ranking_version = _ranking_version(config)
        scored = [
            item
            for pair in candidates.pairs
            if (item := self._score_pair(pair, config, ranking_version)) is not None
        ]
        thresholds = _confidence_thresholds(scored, feedback)
        selected = self._apply_diversity(scored, config)
        proposals = tuple(
            LinkProposal(
                id=item.proposal_id,
                source_document_id=item.pair.source_document_id,
                target_document_id=item.pair.target_document_id,
                direction=item.direction,
                rank=rank,
                score=item.score,
                confidence=_band(item.quality, thresholds),
                features=item.features,
                evidence=item.evidence,
                existing_relationship=False,
                ranking_version=ranking_version,
                review=ReviewState(),
            )
            for rank, item in enumerate(selected, start=1)
        )
        header = ArtifactHeader(
            schema_version=SCHEMA_VERSION,
            run_id=self._run_id,
            corpus_id=candidates.header.corpus_id,
            created_at=utc_now_iso(),
            config_fingerprint=config.fingerprint(),
            producer_version=self._producer_version,
        )
        return ProposalSet(header=header, proposals=proposals)

    def _passes_hard_filters(self, pair: CandidatePair) -> bool:
        """SPEC phase 3 hard filters (see module docstring for the rationale)."""
        for document_id in (pair.source_document_id, pair.target_document_id):
            if document_id not in self._units_by_doc:
                return False
            if document_id not in self._nonempty_docs:
                return False
        return pair.features.get("near_duplicate_probability", 0.0) <= (
            NEAR_DUPLICATE_FILTER_THRESHOLD
        )

    def _score_pair(
        self, pair: CandidatePair, config: RankingConfig, ranking_version: str
    ) -> _Scored | None:
        """Score one pair, returning ``None`` when a filter removes it."""
        if not self._passes_hard_filters(pair):
            return None
        raw = dict(pair.features)
        normalized = normalize_features(raw)
        distance = raw.get("graph_distance", 6.0)
        redundancy = graph_redundancy(distance)
        bridge = cross_neighborhood_value(normalized["csls_similarity_norm"], distance)
        hub = hubness_penalty(raw.get("hubness_source", 0.0), raw.get("hubness_target", 0.0))
        near_duplicate = normalized["near_duplicate_probability_norm"]
        weights = config.weights
        score = clamp01(
            weights["w_document"] * normalized["csls_similarity_norm"]
            + weights["w_local"] * normalized["best_chunk_similarity_norm"]
            + weights["w_breadth"] * normalized["support_breadth_norm"]
            + weights["w_lexical"] * normalized["lexical_similarity_norm"]
            + weights["w_bridge"] * bridge
            - weights["w_hub"] * hub
            - weights["w_duplicate"] * near_duplicate
            - weights["w_redundancy"] * redundancy
        )
        relatedness = clamp01(
            _RELATEDNESS_DOCUMENT_WEIGHT * normalized["document_similarity_norm"]
            + _RELATEDNESS_CHUNK_WEIGHT * normalized["best_chunk_similarity_norm"]
            + _RELATEDNESS_TOP_R_WEIGHT * normalized["top_r_mean_similarity_norm"]
        )
        if relatedness < config.minimum_relatedness:
            return None
        usefulness = clamp01(
            _USEFULNESS_BASE
            + _USEFULNESS_BREADTH_WEIGHT * normalized["support_breadth_norm"]
            + _USEFULNESS_BRIDGE_WEIGHT * bridge
            - _USEFULNESS_HUB_WEIGHT * hub
            - _USEFULNESS_DUPLICATE_WEIGHT * near_duplicate
        )
        missingness = _missingness(distance)
        direction = _direction(pair)
        features = dict(raw)
        features.update(normalized)
        features.update(
            {
                "hubness_penalty": hub,
                "graph_redundancy_penalty": redundancy,
                "cross_neighborhood_value": bridge,
                "relatedness": relatedness,
                "usefulness": usefulness,
                "missingness": missingness,
            }
        )
        proposal_id = fingerprint(
            [
                pair.source_document_id,
                pair.target_document_id,
                direction,
                ranking_version,
            ]
        )
        return _Scored(
            pair=pair,
            direction=direction,
            score=score,
            quality=relatedness * usefulness,
            features=features,
            evidence=self._evidence(pair),
            proposal_id=proposal_id,
        )

    def _spans(self, unit_id: str) -> tuple[Span, ...]:
        unit = self._units_by_id.get(unit_id)
        if unit is None:
            _LOGGER.warning(
                "evidence unit %r is not in the processed corpus; emitting empty spans",
                unit_id,
            )
            return ()
        return unit.source_spans

    def _evidence(self, pair: CandidatePair) -> tuple[Evidence, ...]:
        """The strongest matches as evidence, spans resolved from corpus units."""
        strongest = sorted(
            pair.matches,
            key=lambda match: (
                -match.similarity,
                match.source_unit_id,
                match.target_unit_id,
                match.view,
            ),
        )[:MAX_EVIDENCE]
        return tuple(
            Evidence(
                source_unit_id=match.source_unit_id,
                target_unit_id=match.target_unit_id,
                similarity=match.similarity,
                source_spans=self._spans(match.source_unit_id),
                target_spans=self._spans(match.target_unit_id),
            )
            for match in strongest
        )

    def _doc_tokens(self, document_id: str) -> frozenset[str]:
        """Lexical signature: section-unit tokens, falling back to all units."""
        cached = self._token_cache.get(document_id)
        if cached is not None:
            return cached
        units = self._units_by_doc.get(document_id, ())
        sections = tuple(unit for unit in units if unit.view == _SECTION_VIEW) or units
        tokens = (
            frozenset().union(*(_tokenize(unit.text) for unit in sections))
            if sections
            else frozenset()
        )
        self._token_cache[document_id] = tokens
        return tokens

    def _mmr_order(self, group: list[_Scored], diversity: float) -> list[_Scored]:
        """Maximal marginal relevance over target lexical signatures.

        ``lambda = 1 - diversity`` weighs relevance (the pair score) against
        the maximum Jaccard similarity to already-selected targets. Ties break
        on score descending, then target ID ascending. Reorders presentation
        only; the caller decides membership.
        """
        remaining = sorted(group, key=lambda item: (-item.score, item.pair.target_document_id))
        if diversity <= 0.0:
            return remaining
        lambda_ = 1.0 - diversity
        ordered: list[_Scored] = []
        selected_tokens: list[frozenset[str]] = []
        while remaining:
            best_index = 0
            best_key: tuple[float, float, str] | None = None
            for index, item in enumerate(remaining):
                tokens = self._doc_tokens(item.pair.target_document_id)
                redundancy = max(
                    (_jaccard(tokens, chosen) for chosen in selected_tokens), default=0.0
                )
                mmr = lambda_ * item.score - (1.0 - lambda_) * redundancy
                key = (-mmr, -item.score, item.pair.target_document_id)
                if best_key is None or key < best_key:
                    best_key = key
                    best_index = index
            chosen_item = remaining.pop(best_index)
            ordered.append(chosen_item)
            selected_tokens.append(self._doc_tokens(chosen_item.pair.target_document_id))
        return ordered

    def _apply_diversity(self, scored: list[_Scored], config: RankingConfig) -> list[_Scored]:
        """Per-source-document MMR ordering, presentation cap, and total order."""
        groups: dict[str, list[_Scored]] = {}
        for item in scored:
            groups.setdefault(item.pair.source_document_id, []).append(item)
        selected: list[_Scored] = []
        for source_id in sorted(groups):
            ordered = self._mmr_order(groups[source_id], config.diversity)
            for position, item in enumerate(ordered[: config.results_per_document]):
                item.group_position = position
                selected.append(item)
        selected.sort(
            key=lambda item: (
                item.group_position,
                -item.score,
                item.pair.source_document_id,
                item.pair.target_document_id,
            )
        )
        return selected


def _ranking_version(config: RankingConfig) -> str:
    """Fingerprint of everything that makes scores comparable."""
    return combine_fingerprints(
        config.fingerprint(),
        fingerprint(
            {
                "ranker_version": RANKER_VERSION,
                "normalization_version": NORMALIZATION_VERSION,
                "normalization_constants": NORMALIZATION_CONSTANTS,
            }
        ),
    )
