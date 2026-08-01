"""Default high-recall candidate generator (SPEC "Candidate algorithm" phases 1-3).

Binding decisions implemented here:

- **Aliases.** Relationship kind ``"alias"`` means both endpoint IDs denote
  the same document. Alias classes are resolved by connected components; the
  canonical ID is the lexicographically smallest class member that is present
  in the processed corpus (falling back to the smallest member overall when
  none is present), so downstream stages — which resolve pair endpoints
  against the processed corpus — can always look the pair up. All pair logic
  operates on canonical IDs, so a pair inside one alias class is a self-pair
  and dropped. Feature aggregation unions the units of every class member
  present in the processed corpus.
- **Exclusions.** Adapter-excluded, generated, and archived documents never
  reach the processed corpus (the preprocessor skips them), so corpus
  membership itself is the exclusion filter; :class:`ProcessedCorpus` carries
  no flags by design. A relationship of kind ``"exclusion"`` additionally
  blocks its (canonical, unordered) document pair.
- **Existing direct links.** Unordered canonical pairs connected by a
  relationship whose kind appears in ``config.existing_relationship_kinds``
  never become candidates.
- **Hubness correction** follows CSLS (cross-domain similarity local scaling;
  Conneau et al., "Word Translation Without Parallel Data", ICLR 2018):
  ``csls_similarity = 2 * document_similarity - hubness_source -
  hubness_target``, where a document's hubness is the mean similarity to its
  (up to) ten nearest document-view neighbors — the SPEC's "local neighbor
  distribution". The same correction applies to the best section pair
  (``csls_best_chunk_similarity``) using section-level local densities, which
  is cheap because every section unit is already a retrieval query.
- **Near-duplicate probability** is the deterministic heuristic
  ``sim_gate * (0.6 + 0.25 * lex_gate + 0.15 * size_gate)`` where
  ``sim_gate = clamp01((document_similarity - 0.95) / 0.05)``,
  ``lex_gate = clamp01((lexical_similarity - 0.5) / 0.5)``, and
  ``size_gate = clamp01((token_ratio - 0.5) / 0.5)`` with ``token_ratio`` the
  smaller/larger document token count. It is zero unless document similarity
  exceeds 0.95 and reaches 1.0 only for near-identical documents.

Everything is deterministic: every collection is sorted before truncation and
no result depends on set or dict iteration order beyond insertion order of
already-sorted inputs.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from linkdiscovery.candidates.retrieval import exact_top_k, hnsw_top_k, select_backend
from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.contracts.candidates import (
    SCHEMA_VERSION,
    CandidatePair,
    CandidateSet,
    UnitMatch,
)
from linkdiscovery.embed.vectors import load_vector_table
from linkdiscovery.errors import CandidateError

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from linkdiscovery.artifacts.store import ArtifactStore
    from linkdiscovery.config import CandidateConfig
    from linkdiscovery.contracts.documents import RelationshipSet
    from linkdiscovery.contracts.embeddings import EmbeddingIndex
    from linkdiscovery.contracts.units import ProcessedCorpus, SemanticUnit
    from linkdiscovery.embed.vectors import VectorTable

__all__ = [
    "ALIAS_KIND",
    "EXCLUSION_KIND",
    "GRAPH_DISTANCE_CAP",
    "GRAPH_DISTANCE_UNREACHABLE",
    "LOCAL_DENSITY_NEIGHBORS",
    "MAX_MATCHES_PER_PAIR",
    "DefaultCandidateGenerator",
]

ALIAS_KIND = "alias"
"""Relationship kind whose endpoints denote the same document."""

EXCLUSION_KIND = "exclusion"
"""Relationship kind that blocks its document pair from candidates."""

MAX_MATCHES_PER_PAIR = 8
"""Strongest unit matches retained per pair (similarity desc, unit-id tiebreak)."""

TOP_R_SECTIONS = 3
"""``r`` in "mean of the top r distinct section-pair similarities"."""

LOCAL_DENSITY_NEIGHBORS = 10
"""``k`` for local-density (hubness) estimation over each retrieval view."""

BREADTH_SECTION_SCALE = 6
"""Distinct supporting sections at which ``support_breadth`` saturates at 1.0."""

GRAPH_DISTANCE_CAP = 5
"""Maximum BFS depth explored for ``graph_distance``."""

GRAPH_DISTANCE_UNREACHABLE = 6.0
"""``graph_distance`` value for pairs farther than the cap or disconnected."""

_MIN_LEXICAL_TOKEN_LENGTH = 3
_NEAR_DUP_SIMILARITY_FLOOR = 0.95
_NEAR_DUP_SIMILARITY_RANGE = 0.05
_NEAR_DUP_LEXICAL_FLOOR = 0.5
_NEAR_DUP_LEXICAL_RANGE = 0.5
_NEAR_DUP_SIZE_FLOOR = 0.5
_NEAR_DUP_SIZE_RANGE = 0.5
_NEAR_DUP_BASE_WEIGHT = 0.6
_NEAR_DUP_LEXICAL_WEIGHT = 0.25
_NEAR_DUP_SIZE_WEIGHT = 0.15

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

_MIN_RETRIEVAL_UNITS = 2

_DOCUMENT_VIEW = "document"
_SECTION_VIEW = "section"
_TITLE_VIEW = "title"

_PairKey = tuple[str, str]
_MatchKey = tuple[str, str, str]


def _clamp01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _alias_canonical_map(relationships: RelationshipSet, present: frozenset[str]) -> dict[str, str]:
    """Map every aliased document ID to its class's canonical ID.

    The canonical ID is the lexicographically smallest class member found in
    ``present`` (the processed corpus's document IDs); when no member is
    present, the smallest member overall. Preferring a present member keeps
    pair endpoints resolvable by the ranker and reporter, which look documents
    up in the processed corpus.
    """
    adjacency: dict[str, set[str]] = {}
    for rel in relationships.relationships:
        if rel.kind != ALIAS_KIND:
            continue
        adjacency.setdefault(rel.source_id, set()).add(rel.target_id)
        adjacency.setdefault(rel.target_id, set()).add(rel.source_id)
    canonical: dict[str, str] = {}
    for start in sorted(adjacency):
        if start in canonical:
            continue
        component = [start]
        queue = deque([start])
        seen = {start}
        while queue:
            node = queue.popleft()
            for neighbor in sorted(adjacency.get(node, ())):
                if neighbor not in seen:
                    seen.add(neighbor)
                    component.append(neighbor)
                    queue.append(neighbor)
        present_members = [member for member in component if member in present]
        smallest = min(present_members) if present_members else min(component)
        for member in component:
            canonical[member] = smallest
    return canonical


def _tokenize(text: str) -> frozenset[str]:
    """Lowercased word 1-grams, dropping tokens shorter than three characters."""
    return frozenset(
        token
        for token in _TOKEN_PATTERN.findall(text.lower())
        if len(token) >= _MIN_LEXICAL_TOKEN_LENGTH
    )


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    union = len(left | right)
    if union == 0:
        return 0.0
    return len(left & right) / union


@dataclass(frozen=True)
class _CorpusContext:
    """Alias-resolved, relationship-aware view of the inputs."""

    units_by_id: dict[str, SemanticUnit]
    canonical_of: dict[str, str]
    units_by_doc: dict[str, tuple[SemanticUnit, ...]]
    blocked_pairs: frozenset[_PairKey]
    adjacency: dict[str, frozenset[str]]

    def canonical(self, document_id: str) -> str:
        return self.canonical_of.get(document_id, document_id)

    def view_units(self, canonical_doc: str, view: str) -> tuple[SemanticUnit, ...]:
        return tuple(unit for unit in self.units_by_doc.get(canonical_doc, ()) if unit.view == view)


def _build_context(
    corpus: ProcessedCorpus, relationships: RelationshipSet, config: CandidateConfig
) -> _CorpusContext:
    present = frozenset(document.document_id for document in corpus.documents)
    canonical_of = _alias_canonical_map(relationships, present)

    def canon(document_id: str) -> str:
        return canonical_of.get(document_id, document_id)

    units_by_id: dict[str, SemanticUnit] = {}
    units_by_doc: dict[str, list[SemanticUnit]] = {}
    for document in corpus.documents:
        for unit in document.units:
            units_by_id[unit.id] = unit
            units_by_doc.setdefault(canon(document.document_id), []).append(unit)

    blocked: set[_PairKey] = set()
    adjacency: dict[str, set[str]] = {}
    existing_kinds = set(config.existing_relationship_kinds)
    for rel in relationships.relationships:
        if rel.kind == ALIAS_KIND:
            continue
        source, target = canon(rel.source_id), canon(rel.target_id)
        if source == target:
            continue
        pair = (source, target) if source < target else (target, source)
        if rel.kind in existing_kinds or rel.kind == EXCLUSION_KIND:
            blocked.add(pair)
        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set()).add(source)

    return _CorpusContext(
        units_by_id=units_by_id,
        canonical_of=canonical_of,
        units_by_doc={
            doc: tuple(sorted(units, key=lambda unit: unit.id))
            for doc, units in units_by_doc.items()
        },
        blocked_pairs=frozenset(blocked),
        adjacency={doc: frozenset(neighbors) for doc, neighbors in adjacency.items()},
    )


def _graph_distance(adjacency: dict[str, frozenset[str]], source: str, target: str) -> float:
    """BFS hop count between canonical documents, capped at the SPEC depth."""
    if source == target:
        return 0.0
    seen = {source}
    frontier = deque([(source, 0)])
    while frontier:
        node, depth = frontier.popleft()
        if depth >= GRAPH_DISTANCE_CAP:
            continue
        for neighbor in adjacency.get(node, frozenset()):
            if neighbor == target:
                return float(depth + 1)
            if neighbor not in seen:
                seen.add(neighbor)
                frontier.append((neighbor, depth + 1))
    return GRAPH_DISTANCE_UNREACHABLE


class _FeatureComputer:
    """Phase 2+3 per-pair aggregation and raw feature extraction."""

    def __init__(
        self, table: VectorTable, context: _CorpusContext, density: dict[str, float]
    ) -> None:
        self._table = table
        self._context = context
        self._density = density
        self._token_cache: dict[str, frozenset[str]] = {}
        self._hubness_cache: dict[str, float] = {}

    def _vector_ids(self, canonical_doc: str, view: str) -> list[str]:
        return [
            unit.id
            for unit in self._context.view_units(canonical_doc, view)
            if unit.id in self._table
        ]

    def _cross(self, a_ids: list[str], b_ids: list[str]) -> NDArray[np.float32] | None:
        if not a_ids or not b_ids:
            return None
        a = np.stack([self._table.vector_for_unit(unit_id) for unit_id in a_ids])
        b = np.stack([self._table.vector_for_unit(unit_id) for unit_id in b_ids])
        result: NDArray[np.float32] = a @ b.T
        return result

    def _max_view_similarity(self, source: str, target: str, view: str) -> float:
        sims = self._cross(self._vector_ids(source, view), self._vector_ids(target, view))
        return 0.0 if sims is None else float(sims.max())

    def _hubness(self, canonical_doc: str) -> float:
        """Mean local density of the document's document-view units (0.0 if none)."""
        cached = self._hubness_cache.get(canonical_doc)
        if cached is not None:
            return cached
        values = [
            self._density.get(unit_id, 0.0)
            for unit_id in self._vector_ids(canonical_doc, _DOCUMENT_VIEW)
        ]
        hubness = sum(values) / len(values) if values else 0.0
        self._hubness_cache[canonical_doc] = hubness
        return hubness

    def _doc_tokens(self, canonical_doc: str) -> frozenset[str]:
        """Lexical token set: section-unit texts, falling back to all units."""
        cached = self._token_cache.get(canonical_doc)
        if cached is not None:
            return cached
        units = self._context.view_units(
            canonical_doc, _SECTION_VIEW
        ) or self._context.units_by_doc.get(canonical_doc, ())
        tokens = (
            frozenset().union(*(_tokenize(unit.text) for unit in units)) if units else frozenset()
        )
        self._token_cache[canonical_doc] = tokens
        return tokens

    def _token_count(self, canonical_doc: str) -> float:
        """Token count over section units, else document units, else all units."""
        for view in (_SECTION_VIEW, _DOCUMENT_VIEW):
            units = self._context.view_units(canonical_doc, view)
            if units:
                return float(sum(unit.token_count for unit in units))
        return float(
            sum(unit.token_count for unit in self._context.units_by_doc.get(canonical_doc, ()))
        )

    def _section_pair_stats(self, source: str, target: str) -> tuple[float, float, float]:
        """(best_chunk, top_r_mean, csls_best_chunk) over the section cross product.

        The argmax pair for the CSLS correction is deterministic: among ties on
        the maximum similarity, the lexicographically smallest (source unit,
        target unit) pair wins.
        """
        source_ids = self._vector_ids(source, _SECTION_VIEW)
        target_ids = self._vector_ids(target, _SECTION_VIEW)
        sims = self._cross(source_ids, target_ids)
        if sims is None:
            return 0.0, 0.0, 0.0
        flat = np.sort(sims, axis=None)[::-1]
        best = float(flat[0])
        top_r = float(flat[: min(TOP_R_SECTIONS, flat.shape[0])].mean())
        tied = np.argwhere(sims >= flat[0])
        best_source, best_target = min((source_ids[i], target_ids[j]) for i, j in tied)
        csls_best = (
            2.0 * best - self._density.get(best_source, 0.0) - self._density.get(best_target, 0.0)
        )
        return best, top_r, csls_best

    def _directional_similarity(self, from_doc: str, to_doc: str) -> float:
        """Best similarity from ``from_doc``'s sections to ``to_doc``'s document view."""
        sims = self._cross(
            self._vector_ids(from_doc, _SECTION_VIEW), self._vector_ids(to_doc, _DOCUMENT_VIEW)
        )
        return 0.0 if sims is None else float(sims.max())

    def _support_breadth(self, matches: tuple[UnitMatch, ...]) -> float:
        source_sections = {match.source_unit_id for match in matches if match.view == _SECTION_VIEW}
        target_sections = {match.target_unit_id for match in matches if match.view == _SECTION_VIEW}
        distinct = len(source_sections) + len(target_sections)
        return min(1.0, distinct / BREADTH_SECTION_SCALE)

    @staticmethod
    def _near_duplicate_probability(
        document_similarity: float, lexical_similarity: float, token_ratio: float
    ) -> float:
        sim_gate = _clamp01(
            (document_similarity - _NEAR_DUP_SIMILARITY_FLOOR) / _NEAR_DUP_SIMILARITY_RANGE
        )
        lex_gate = _clamp01(
            (lexical_similarity - _NEAR_DUP_LEXICAL_FLOOR) / _NEAR_DUP_LEXICAL_RANGE
        )
        size_gate = _clamp01((token_ratio - _NEAR_DUP_SIZE_FLOOR) / _NEAR_DUP_SIZE_RANGE)
        return sim_gate * (
            _NEAR_DUP_BASE_WEIGHT
            + _NEAR_DUP_LEXICAL_WEIGHT * lex_gate
            + _NEAR_DUP_SIZE_WEIGHT * size_gate
        )

    def features(
        self, source: str, target: str, matches: tuple[UnitMatch, ...]
    ) -> dict[str, float]:
        """Compute the binding raw feature vocabulary for one canonical pair."""
        context = self._context
        document_similarity = self._max_view_similarity(source, target, _DOCUMENT_VIEW)
        title_similarity = self._max_view_similarity(source, target, _TITLE_VIEW)
        best_chunk, top_r_mean, csls_best_chunk = self._section_pair_stats(source, target)
        lexical = _jaccard(self._doc_tokens(source), self._doc_tokens(target))
        source_tokens = self._token_count(source)
        target_tokens = self._token_count(target)
        larger = max(source_tokens, target_tokens)
        token_ratio = (min(source_tokens, target_tokens) / larger) if larger > 0 else 0.0
        hubness_source = self._hubness(source)
        hubness_target = self._hubness(target)
        return {
            "document_similarity": document_similarity,
            "title_similarity": title_similarity,
            "best_chunk_similarity": best_chunk,
            "top_r_mean_similarity": top_r_mean,
            "support_breadth": self._support_breadth(matches),
            "source_chunk_count": float(len(context.view_units(source, _SECTION_VIEW))),
            "target_chunk_count": float(len(context.view_units(target, _SECTION_VIEW))),
            "source_token_count": source_tokens,
            "target_token_count": target_tokens,
            "lexical_similarity": lexical,
            "graph_distance": _graph_distance(context.adjacency, source, target),
            "common_neighbor_count": float(
                len(
                    context.adjacency.get(source, frozenset())
                    & context.adjacency.get(target, frozenset())
                )
            ),
            "hubness_source": hubness_source,
            "hubness_target": hubness_target,
            "csls_similarity": 2.0 * document_similarity - hubness_source - hubness_target,
            "csls_best_chunk_similarity": csls_best_chunk,
            "near_duplicate_probability": self._near_duplicate_probability(
                document_similarity, lexical, token_ratio
            ),
            "directional_similarity_source_to_target": self._directional_similarity(source, target),
            "directional_similarity_target_to_source": self._directional_similarity(target, source),
        }


class DefaultCandidateGenerator:
    """High-recall candidate generation over an embedding index.

    Implements the :class:`~linkdiscovery.interfaces.CandidateGenerator`
    protocol: per-view nearest-neighbor retrieval, alias resolution, exclusion
    of existing direct links, reciprocal-match collapse, deterministic
    bounding, and raw feature aggregation. Retrieval and judgment stay
    separate: this stage never filters on semantic quality beyond its recall
    budgets.
    """

    def __init__(
        self,
        store: ArtifactStore,
        *,
        run_id: str = "adhoc",
        producer_version: str = "linkdiscovery/0.1.0",
    ) -> None:
        """``store`` resolves the index's vector references; identity goes in headers."""
        self._store = store
        self._run_id = run_id
        self._producer_version = producer_version
        self.last_index_params: dict[str, dict[str, int | str]] = {}
        """Effective approximate-index construction parameters per retrieval
        view from the most recent :meth:`generate` call (empty for exact
        search). The SPEC requires index parameters in the run manifest; the
        orchestrator reads this after each run, mirroring the preprocessor's
        ``skipped_excluded_count``."""

    def generate(
        self,
        corpus: ProcessedCorpus,
        index: EmbeddingIndex,
        relationships: RelationshipSet,
        config: CandidateConfig,
    ) -> CandidateSet:
        """Retrieve nearest-neighbor unit matches and aggregate document pairs.

        Raises :class:`~linkdiscovery.errors.CandidateError` when the index
        references units absent from the processed corpus (index/corpus
        mismatch) or the configured backend is unavailable.
        """
        context = _build_context(corpus, relationships, config)
        table = load_vector_table(self._store, index)
        for unit_id in table.unit_ids:
            if unit_id not in context.units_by_id:
                raise CandidateError(
                    f"embedding index references unit {unit_id!r} that is absent from the "
                    f"processed corpus {corpus.header.corpus_id!r}; the index and corpus "
                    "are mismatched"
                )
        backend = select_backend(config, len(table))
        self.last_index_params = {}
        pair_matches, density = self._retrieve(table, context, config, backend)
        survivors, kept_matches = _bound_pairs(pair_matches, config)
        computer = _FeatureComputer(table, context, density)
        pairs = tuple(
            CandidatePair(
                source_document_id=source,
                target_document_id=target,
                matches=kept_matches[(source, target)],
                features=computer.features(source, target, kept_matches[(source, target)]),
            )
            for source, target in survivors
        )
        header = ArtifactHeader(
            schema_version=SCHEMA_VERSION,
            run_id=self._run_id,
            corpus_id=corpus.header.corpus_id,
            created_at=utc_now_iso(),
            config_fingerprint=config.fingerprint(),
            producer_version=self._producer_version,
        )
        return CandidateSet(header=header, pairs=pairs)

    def _retrieve(
        self,
        table: VectorTable,
        context: _CorpusContext,
        config: CandidateConfig,
        backend: str,
    ) -> tuple[dict[_PairKey, dict[_MatchKey, float]], dict[str, float]]:
        """Phase 1: per-view retrieval, alias-resolved pair construction.

        Reciprocal unit matches collapse into one canonical unordered pair
        whose source document is the lexicographically smaller ID; each match
        is oriented so its source unit belongs to the pair's source document.
        Also computes each query unit's local density (mean similarity to its
        up-to-:data:`LOCAL_DENSITY_NEIGHBORS` nearest same-view neighbors).
        """
        pair_matches: dict[_PairKey, dict[_MatchKey, float]] = {}
        density: dict[str, float] = {}
        view_of = {unit_id: context.units_by_id[unit_id].view for unit_id in table.unit_ids}
        views = sorted(set(view_of.values()))
        for view in views:
            view_ids = sorted(unit_id for unit_id in table.unit_ids if view_of[unit_id] == view)
            for unit_id in view_ids:
                density.setdefault(unit_id, 0.0)
            if len(view_ids) < _MIN_RETRIEVAL_UNITS:
                continue
            view_table = table.select(view_ids)
            k = min(config.neighbors_per_unit, len(view_table) - 1)
            if backend == "hnsw":
                results, params = hnsw_top_k(view_table, k)
                self.last_index_params[view] = params
            else:
                results = exact_top_k(view_table, k)
            for query_position, neighbors in enumerate(results):
                query_id = view_ids[query_position]
                top = [sim for _, sim in neighbors[:LOCAL_DENSITY_NEIGHBORS]]
                density[query_id] = float(sum(top) / len(top)) if top else 0.0
                query_doc = context.canonical(context.units_by_id[query_id].document_id)
                for neighbor_position, similarity in neighbors:
                    neighbor_id = view_ids[neighbor_position]
                    neighbor_doc = context.canonical(context.units_by_id[neighbor_id].document_id)
                    if query_doc == neighbor_doc:
                        continue
                    pair = (
                        (query_doc, neighbor_doc)
                        if query_doc < neighbor_doc
                        else (neighbor_doc, query_doc)
                    )
                    if pair in context.blocked_pairs:
                        continue
                    match: _MatchKey = (
                        (query_id, neighbor_id, view)
                        if query_doc == pair[0]
                        else (neighbor_id, query_id, view)
                    )
                    bucket = pair_matches.setdefault(pair, {})
                    previous = bucket.get(match)
                    if previous is None or similarity > previous:
                        bucket[match] = float(similarity)
        return pair_matches, density


def _bound_pairs(
    pair_matches: dict[_PairKey, dict[_MatchKey, float]], config: CandidateConfig
) -> tuple[list[_PairKey], dict[_PairKey, tuple[UnitMatch, ...]]]:
    """Truncate matches per pair, then bound pairs per document and globally.

    Per-document bounding is strict: a pair survives only when it ranks within
    ``config.max_pairs_per_document`` (by best-match similarity descending,
    then pair key ascending) for *both* endpoint documents, so no document
    exceeds its budget. The global bound and final ordering use the same key.
    """
    kept_matches: dict[_PairKey, tuple[UnitMatch, ...]] = {}
    best: dict[_PairKey, float] = {}
    for pair_key, bucket in pair_matches.items():
        ordered = sorted(bucket.items(), key=lambda item: (-item[1], item[0]))
        strongest = ordered[:MAX_MATCHES_PER_PAIR]
        kept_matches[pair_key] = tuple(
            UnitMatch(source_unit_id=src, target_unit_id=tgt, view=view, similarity=sim)
            for (src, tgt, view), sim in strongest
        )
        best[pair_key] = strongest[0][1]

    by_document: dict[str, list[_PairKey]] = {}
    for pair_key in best:
        by_document.setdefault(pair_key[0], []).append(pair_key)
        by_document.setdefault(pair_key[1], []).append(pair_key)
    dropped: set[_PairKey] = set()
    for document in sorted(by_document):
        ranked = sorted(by_document[document], key=lambda pk: (-best[pk], pk))
        dropped.update(ranked[config.max_pairs_per_document :])

    survivors = sorted((pk for pk in best if pk not in dropped), key=lambda pk: (-best[pk], pk))
    if config.max_total_pairs is not None:
        survivors = survivors[: config.max_total_pairs]
    return survivors, kept_matches
