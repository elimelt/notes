"""Orchestration of the inline-link subsystem (SPEC-INLINE-LINKING §11).

Each function here is one independently callable step of the phased build
plan, mirroring the style of :mod:`linkdiscovery.pipeline`:

- :func:`load_inline_inputs` runs (or reuses, via the embedding cache) the v1
  stages the inline subsystem consumes: adapter load -> preprocess -> embed.
- :func:`build_audit_artifacts` is phase 1 (the data audit sample).
- :func:`check_span_recall` is phase 2 (the recall-ceiling gate).
- :func:`build_anchor_artifacts` builds the §5 anchor dictionary artifacts.
- :func:`propose_inline_baseline` is the deterministic §12 fallback engine.
- :func:`train_inline_heads` / :func:`propose_inline_learned` are phase 3
  (Architecture A: frozen encoder + three trained heads).

Encoder-space honesty note (the §6/§9 dimensional contract): the *learned*
path re-derives every target vector by pushing each note's title+description
through the **same frozen token encoder** that produces span representations
(mean of its token states), because ``build_training_data`` and
``build_pair_features`` require ``target_dim == hidden_size``. The v1
bi-encoder vectors (1024-dim Qwen or the hashing baseline table) are **only**
used by the deterministic baseline's cosine feature. The default token
encoder is the dependency-free :class:`~linkdiscovery.inline.encode.
HashingTokenEncoder`; the production path injects a factory returning a
:class:`~linkdiscovery.inline.encode.QwenTokenEncoder` so token states come
from the real frozen model.

All outputs are deterministic for fixed inputs and seeds, and every file is
written atomically via :func:`linkdiscovery.report._io.atomic_write_text`.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Final

import numpy as np

from linkdiscovery.artifacts.cache import ArtifactCache
from linkdiscovery.artifacts.store import ArtifactStore
from linkdiscovery.contracts.units import Span
from linkdiscovery.embed import DefaultEmbedder
from linkdiscovery.embed.vectors import load_vector_table
from linkdiscovery.errors import ContractError
from linkdiscovery.fingerprint import canonical_json, fingerprint
from linkdiscovery.inline.anchors import AnchorConfig, AnchorDictionary, build_anchor_dictionary
from linkdiscovery.inline.audit.annotate import load_audit_labels
from linkdiscovery.inline.audit.sampler import build_audit_sample
from linkdiscovery.inline.baseline import BaselineConfig, propose_baseline
from linkdiscovery.inline.calibrate import apply_temperature
from linkdiscovery.inline.encode import (
    HashingTokenEncoder,
    TokenStateEncoder,
    TokenStates,
    span_representation,
)
from linkdiscovery.inline.heads import build_pair_features
from linkdiscovery.inline.records import (
    AuditItem,
    AuditSample,
    InlineProposal,
    LinkRegionKind,
    SpanCandidate,
)
from linkdiscovery.inline.select import SelectionConfig, combine_scores, select_proposals
from linkdiscovery.inline.spans import SpanConfig, propose_spans, span_recall
from linkdiscovery.inline.train import (
    SpanRepTable,
    TargetCatalog,
    TrainConfig,
    build_training_data,
    default_pair_hand_features,
    train_heads,
)
from linkdiscovery.interfaces import RegionParser, SourceAdapter
from linkdiscovery.pipeline import (
    PRODUCER_VERSION,
    _exclude_ineligible,
    _select_token_counter,
)
from linkdiscovery.plugins import instantiate_plugin
from linkdiscovery.preprocess import DefaultPreprocessor
from linkdiscovery.report._io import atomic_write_text

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from numpy.typing import NDArray

    from linkdiscovery.config import PipelineConfig
    from linkdiscovery.contracts.documents import Corpus, RelationshipSet, SourceDocument
    from linkdiscovery.contracts.embeddings import EmbeddingIndex
    from linkdiscovery.contracts.units import ProcessedCorpus
    from linkdiscovery.embed.vectors import VectorTable
    from linkdiscovery.inline.heads import TrainedHeads
    from linkdiscovery.inline.records import InlineProposalSet

__all__ = [
    "INLINE_FEATURE_NAMES",
    "InlineInputs",
    "build_anchor_artifacts",
    "build_audit_artifacts",
    "check_span_recall",
    "load_audit_sample",
    "load_inline_inputs",
    "propose_inline_baseline",
    "propose_inline_learned",
    "train_inline_heads",
]

_LOGGER = logging.getLogger(__name__)

INLINE_FEATURE_NAMES: Final = (
    "keyphraseness",
    "commonness_top",
    "anchor_count",
    "target_count",
    "word_count",
    "char_count",
    "is_title_match",
    "is_alias_match",
    "is_acronym",
    "is_titlecase",
    "is_hyphenated",
    "sentence_position",
    "region_prose",
)
"""The hand-feature vocabulary of :class:`~linkdiscovery.inline.records.
SpanCandidate` in the fixed order appended to every span representation."""

_LEARNED_SHORTLIST: Final = 5
"""Targets per span passed from the retrieval head to the reranker (SPEC §9)."""

_PLACEMENT_POSITION_PENALTY: Final = 0.25
"""Sentence-position penalty of the deterministic placement rule (baseline default)."""

_PLACEMENT_NON_PROSE_FLOOR: Final = 0.05
"""Placement floor for non-prose spans (SPEC §4: graph edges, not anchors)."""

_PROBABILITY_EPSILON: Final = 1e-6
"""Clamp keeping combined scores strictly inside (0, 1) before the logit."""

_ACRONYM = re.compile(r"[A-Z][A-Z0-9]+")
_HYPHENATED = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+")
_MD_SIGNIFICANT = re.compile(r"([\\`*_\[\]#|<>{}])")
_EXPLICIT_LINK_KIND: Final = "explicit-link"


@dataclass(frozen=True, slots=True)
class InlineInputs:
    """Everything the inline workflow needs from the v1 pipeline stages.

    ``corpus`` is the effective corpus (generated/archived documents marked
    ``excluded``, matching the pipeline's eligibility policy) with the full
    relationship set intact; ``processed`` covers exactly the non-excluded
    documents; ``index``/``vectors`` are the v1 embedding index and its
    resolved vector table (the bi-encoder space — used by the baseline only).
    """

    config: PipelineConfig
    corpus: Corpus
    processed: ProcessedCorpus
    index: EmbeddingIndex
    vectors: VectorTable
    relationships: RelationshipSet


def load_inline_inputs(config: PipelineConfig, *, artifacts_root: Path) -> InlineInputs:
    """Run (or reuse) the v1 stages the inline subsystem consumes.

    Executes adapter load -> eligibility exclusion -> preprocess -> embed
    exactly as :class:`~linkdiscovery.pipeline.Pipeline` does, reusing the
    pipeline's own token-counter and exclusion helpers and the artifact-store
    embedding cache under ``artifacts_root`` (a second call with unchanged
    inputs re-embeds nothing). No candidates are generated, no proposals are
    ranked, and no run manifest is written.
    """
    store = ArtifactStore(Path(artifacts_root))
    adapter: SourceAdapter = instantiate_plugin(config.source.adapter, SourceAdapter)
    parser: RegionParser = instantiate_plugin(config.preprocess.parser, RegionParser)
    corpus = adapter.load(config.source)
    effective, auto_excluded = _exclude_ineligible(corpus)
    token_counter = _select_token_counter(config.embedding)
    preprocessor = DefaultPreprocessor(
        parser, token_counter, run_id="inline", producer_version=PRODUCER_VERSION
    )
    processed = preprocessor.process(effective, config.preprocess)
    cache = ArtifactCache(store)
    embedder = DefaultEmbedder(store, run_id="inline", producer_version=PRODUCER_VERSION)
    index = embedder.embed(processed, config.embedding, cache)
    vectors = load_vector_table(store, index)
    _LOGGER.info(
        "inline inputs: %d documents (%d auto-excluded), %d units, %d vectors",
        len(effective.documents),
        auto_excluded,
        sum(len(document.units) for document in processed.documents),
        len(vectors),
    )
    return InlineInputs(
        config=config,
        corpus=effective,
        processed=processed,
        index=index,
        vectors=vectors,
        relationships=effective.relationships,
    )


def load_audit_sample(path: Path) -> AuditSample:
    """Load an ``audit-sample.json`` written by :func:`build_audit_artifacts`.

    Raises :class:`~linkdiscovery.errors.ContractError` when the file is
    missing, unreadable, or violates the :class:`AuditSample` contract.
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContractError(f"cannot read audit sample {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"audit sample {path} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ContractError(f"audit sample {path} must be a JSON object")
    return AuditSample.from_dict(raw)


def _escape_md(text: str) -> str:
    """Escape markdown-significant characters in corpus-derived text."""
    return _MD_SIGNIFICANT.sub(r"\\\1", text)


def _audit_sample_markdown(sample: AuditSample) -> str:
    """A human-readable companion listing every sampled item for offline reading."""
    lines = [
        "# Inline-link audit sample",
        "",
        f"- Corpus: `{sample.header.corpus_id}`",
        f"- Items: {len(sample.items)} across {len(sample.strata_counts)} strata",
        f"- Created: {sample.header.created_at}",
        "",
        "## Strata",
        "",
    ]
    lines.extend(f"- `{key}`: {count}" for key, count in sorted(sample.strata_counts.items()))
    lines.append("")
    lines.append("## Items")
    lines.append("")
    for position, item in enumerate(sample.items, start=1):
        lines.extend(
            (
                f"### {position}. `{item.id}`",
                "",
                f"- source: `{item.source_document_id}`",
                f"- target: `{item.target_document_id}`",
                f"- anchor: {_escape_md(item.anchor_text)} ({item.anchor_word_count} word(s))",
                f"- region: `{item.region_kind.value}`  topic: `{item.topic_family}`",
                f"- context: {_escape_md(item.context)}",
                "",
            )
        )
    return "\n".join(lines)


def build_audit_artifacts(
    inputs: InlineInputs, *, size: int = 150, seed: int, out_dir: Path
) -> AuditSample:
    """Phase 1: draw the stratified audit sample and write its artifacts.

    Writes ``audit-sample.json`` (the :class:`AuditSample` contract dict) and
    ``audit-sample.md`` (a human-readable listing of every item — ids,
    anchor, region, context — for offline annotation prep) into ``out_dir``,
    both atomically. Deterministic for a fixed corpus, ``size``, and
    ``seed``.
    """
    sample = build_audit_sample(inputs.corpus, inputs.processed, size=size, seed=seed)
    out = Path(out_dir)
    atomic_write_text(out / "audit-sample.json", canonical_json(sample.to_dict()) + "\n")
    atomic_write_text(out / "audit-sample.md", _audit_sample_markdown(sample) + "\n")
    _LOGGER.info("audit sample: %d items written to %s", len(sample.items), out)
    return sample


def _prepared_dictionary(corpus: Corpus, config: AnchorConfig) -> AnchorDictionary:
    """Build the anchor dictionary and attach corpus occurrence counts."""
    dictionary = build_anchor_dictionary(corpus, config=config)
    dictionary.attach_occurrences(dictionary.occurrence_counts(corpus))
    return dictionary


def _anchor_stats(dictionary: AnchorDictionary) -> dict[str, object]:
    """Summary statistics for ``anchor-stats.json`` (counts and keyphraseness deciles)."""
    mentions = dictionary.mentions()
    synthetic = [m for m in mentions if dictionary.is_title(m) or dictionary.is_alias(m)]
    eligible = [m for m in mentions if dictionary.eligible(m)]
    linked = [m for m in mentions if dictionary.linked_count(m) > 0]
    keyphraseness = sorted(
        dictionary.keyphraseness(mention, dictionary.occurrence_count(mention))
        for mention in linked
    )
    deciles: dict[str, float] = {}
    if keyphraseness:
        values = np.asarray(keyphraseness, dtype=np.float64)
        for decile in range(0, 101, 10):
            deciles[f"p{decile}"] = float(np.percentile(values, decile))
    return {
        "mention_count": len(mentions),
        "linked_mention_count": len(linked),
        "synthetic_mention_count": len(synthetic),
        "eligible_mention_count": len(eligible),
        "keyphraseness_floor": dictionary.config.keyphraseness_floor,
        "keyphraseness_deciles": deciles,
    }


def build_anchor_artifacts(
    inputs: InlineInputs, *, config: AnchorConfig, out_dir: Path
) -> AnchorDictionary:
    """Build the §5 anchor dictionary, attach occurrences, and write artifacts.

    Writes ``anchor-dictionary.json`` (the full dictionary including cached
    occurrence counts, reloadable via ``AnchorDictionary.from_dict``) and
    ``anchor-stats.json`` (mention/synthetic/eligible counts and the
    keyphraseness decile distribution over linked mentions) into ``out_dir``,
    atomically. Deterministic for a fixed corpus and config.
    """
    dictionary = _prepared_dictionary(inputs.corpus, config)
    out = Path(out_dir)
    atomic_write_text(out / "anchor-dictionary.json", canonical_json(dictionary.to_dict()) + "\n")
    stats = _anchor_stats(dictionary)
    atomic_write_text(out / "anchor-stats.json", canonical_json(stats) + "\n")
    _LOGGER.info(
        "anchor dictionary: %s mentions (%s eligible) written to %s",
        stats["mention_count"],
        stats["eligible_mention_count"],
        out,
    )
    return dictionary


def _documents_by_id(inputs: InlineInputs) -> dict[str, SourceDocument]:
    return {document.id: document for document in inputs.corpus.documents}


def _titles(inputs: InlineInputs) -> dict[str, str]:
    return {doc.id: doc.title for doc in inputs.corpus.documents if doc.title}


def _propose_all_spans(
    inputs: InlineInputs,
    dictionary: AnchorDictionary,
    span_config: SpanConfig,
    relationships: RelationshipSet,
) -> dict[str, tuple[SpanCandidate, ...]]:
    """Candidate spans per processed document (docs with no processed entry skipped).

    The processed corpus is the exclusion boundary: excluded documents have
    no processed entry and therefore propose nothing. Only prose/list regions
    yield candidates (the span stage's ``allowed_regions`` policy).
    """
    documents = _documents_by_id(inputs)
    candidates: dict[str, tuple[SpanCandidate, ...]] = {}
    for processed_doc in inputs.processed.documents:
        document = documents.get(processed_doc.document_id)
        if document is None:
            continue
        spans = propose_spans(
            document, processed_doc, relationships, dictionary, config=span_config
        )
        if spans:
            candidates[document.id] = spans
    return candidates


def _document_vectors(inputs: InlineInputs) -> dict[str, NDArray[np.float32]]:
    """One v1 bi-encoder vector per document, from the document-view units.

    Maps each ``view == "document"`` semantic unit to its document; when a
    document somehow has several document-view units the lexically smallest
    unit id wins, deterministically.
    """
    chosen: dict[str, str] = {}
    for processed_doc in inputs.processed.documents:
        for unit in processed_doc.units:
            if unit.view != "document":
                continue
            current = chosen.get(processed_doc.document_id)
            if current is None or unit.id < current:
                chosen[processed_doc.document_id] = unit.id
    return {
        document_id: inputs.vectors.vector_for_unit(unit_id)
        for document_id, unit_id in sorted(chosen.items())
        if unit_id in inputs.vectors
    }


def propose_inline_baseline(
    inputs: InlineInputs,
    *,
    anchor_config: AnchorConfig,
    span_config: SpanConfig,
    baseline_config: BaselineConfig,
    selection_config: SelectionConfig,
    run_id: str = "adhoc",
) -> InlineProposalSet:
    """The full deterministic fallback path (SPEC §12 kill-criterion engine).

    Pipeline: anchor dictionary (with occurrences) -> candidate spans per
    prose document -> draft proposals via :func:`~linkdiscovery.inline.
    baseline.propose_baseline` (target lookup = dictionary, document vectors
    from the v1 document-view embedding index, ``span_vectors=None`` so the
    embedding-cosine term is 0) -> :func:`~linkdiscovery.inline.select.
    select_proposals` for thresholds, per-note budget, and MMR. Self-links
    are excluded by the baseline; overlap with existing links is excluded by
    the span stage. Fully deterministic: no RNG anywhere on this path.
    """
    dictionary = _prepared_dictionary(inputs.corpus, anchor_config)
    candidates = _propose_all_spans(inputs, dictionary, span_config, inputs.relationships)
    drafts = propose_baseline(
        candidates,
        dictionary.lookup,
        _document_vectors(inputs),
        None,
        _titles(inputs),
        config=baseline_config,
        run_id=run_id,
        corpus_id=inputs.corpus.header.corpus_id,
    )
    return select_proposals(
        drafts,
        _documents_by_id(inputs),
        config=selection_config,
        run_id=run_id,
        corpus_id=inputs.corpus.header.corpus_id,
    )


def _display_text_offset(markup: str, anchor_text: str) -> int:
    """Offset of the rendered anchor display text within link markup, or -1.

    Wikilinks place the display text after the last ``|``
    (``[[target|display]]``), and the target path may itself contain the
    display text (``[[caches|cache]]``) — a plain ``find`` would land on the
    target, not the rendered anchor — so when that separator is present the
    search starts after it, falling back to a plain ``find`` for markup
    where the display text does not appear there verbatim. Markdown links
    (``[display](target)``) put the display text first, where a plain
    ``find`` is already correct.
    """
    if markup.startswith("[[") and "|" in markup:
        offset = markup.find(anchor_text, markup.rfind("|") + 1)
        if offset >= 0:
            return offset
    return markup.find(anchor_text)


def _narrow_to_anchor(item: AuditItem, documents: Mapping[str, SourceDocument]) -> AuditItem:
    """Narrow a link-markup span to its anchor display text, when findable.

    Adapters record ``source_span`` over the *whole* link markup (for example
    ``[[target|anchor]]``), but the span generator proposes plain-text spans
    — a candidate can never contain link syntax. The recall gate therefore
    judges coverage of the anchor's display text: the occurrence of
    ``anchor_text`` at its rendered position inside the markup span (see
    :func:`_display_text_offset` — after the last ``|`` for wikilinks, so a
    display text that also appears inside the target path is never
    mislocated). Items whose anchor text cannot be located
    (adapter-humanized anchors that never appear verbatim) keep the
    original span and count as misses, which keeps the gate conservative.
    """
    span = item.source_span
    document = documents.get(item.source_document_id)
    if span is None or document is None or not item.anchor_text:
        return item
    markup = document.content[span.start : span.end]
    offset = _display_text_offset(markup, item.anchor_text)
    if offset < 0:
        return item
    start = span.start + offset
    return replace(item, source_span=Span(start=start, end=start + len(item.anchor_text)))


def check_span_recall(
    inputs: InlineInputs,
    sample: AuditSample,
    *,
    anchor_config: AnchorConfig,
    span_config: SpanConfig,
) -> dict[str, float]:
    """Phase 2: the recall-ceiling gate (SPEC §11 step 2, §12 kill criterion).

    The audited items *are* existing links, and the span stage hard-excludes
    spans overlapping existing links — so for this check the generator runs
    against a relationship set with every span-carrying ``explicit-link``
    removed, letting it (attempt to) rediscover the audited anchors. Each
    item's markup span is first narrowed to its anchor display text (see
    :func:`_narrow_to_anchor`), because candidates are plain-text spans by
    construction. Returns the :func:`~linkdiscovery.inline.spans.span_recall`
    dict (``exact_recall``, ``overlap_recall``, ``n_prose_items``); the §12
    gate is >= ~0.85 overlap recall.
    """
    dictionary = _prepared_dictionary(inputs.corpus, anchor_config)
    visible = replace(
        inputs.relationships,
        relationships=tuple(
            relationship
            for relationship in inputs.relationships.relationships
            if not (
                relationship.kind == _EXPLICIT_LINK_KIND and relationship.source_span is not None
            )
        ),
    )
    candidates = _propose_all_spans(inputs, dictionary, span_config, visible)
    documents = _documents_by_id(inputs)
    narrowed = [_narrow_to_anchor(item, documents) for item in sample.items]
    return span_recall(narrowed, candidates)


# ------------------------------------------------------ learned path helpers


def _hand_features(features: Mapping[str, float]) -> tuple[float, ...]:
    """A candidate's hand features in the fixed :data:`INLINE_FEATURE_NAMES` order."""
    return tuple(float(features.get(name, 0.0)) for name in INLINE_FEATURE_NAMES)


def _audit_item_features(
    item: AuditItem, document: SourceDocument, dictionary: AnchorDictionary, span: Span
) -> dict[str, float]:
    """Hand features for an audited link span, mirroring the span-stage vocabulary.

    Audited spans overlap existing links, so the span stage never emits
    candidates for them; this helper recomputes the same feature vocabulary
    directly. One honest approximation: ``sentence_position`` is the span's
    relative position within the whole document rather than within its
    containing region (the region is not re-derived here).
    """
    text = document.content[span.start : span.end]
    targets = dictionary.lookup(text)
    total = sum(targets.values())
    words = text.split()
    is_titlecase = (
        bool(words)
        and all(word[:1].isupper() for word in words)
        and any(char.islower() for char in text)
    )
    return {
        "keyphraseness": dictionary.keyphraseness(text, dictionary.occurrence_count(text)),
        "commonness_top": max((count / total for count in targets.values()), default=0.0),
        "anchor_count": float(total),
        "target_count": float(len(targets)),
        "word_count": float(len(words)),
        "char_count": float(len(text)),
        "is_title_match": 1.0 if dictionary.is_title(text) else 0.0,
        "is_alias_match": 1.0 if dictionary.is_alias(text) else 0.0,
        "is_acronym": 1.0 if _ACRONYM.fullmatch(text) else 0.0,
        "is_titlecase": 1.0 if is_titlecase else 0.0,
        "is_hyphenated": (
            1.0 if _HYPHENATED.fullmatch(text) and any(c.isalpha() for c in text) else 0.0
        ),
        "sentence_position": min(1.0, span.start / max(1, len(document.content))),
        "region_prose": 1.0 if item.region_kind is LinkRegionKind.PROSE else 0.0,
    }


class _DocumentEncoder:
    """Per-document token states from one frozen encoder, computed once each."""

    def __init__(self, encoder: TokenStateEncoder) -> None:
        self._encoder = encoder
        self._states: dict[str, TokenStates] = {}

    @property
    def encoder(self) -> TokenStateEncoder:
        return self._encoder

    def states_for(self, document: SourceDocument) -> TokenStates:
        states = self._states.get(document.id)
        if states is None:
            states = self._encoder.encode_tokens(document.content)
            self._states[document.id] = states
        return states


def _target_catalog(inputs: InlineInputs, encoder: TokenStateEncoder) -> TargetCatalog:
    """The closed-world target catalog in the *token-encoder* hidden space.

    Each document's vector is the mean of the token states of its
    ``title + description`` text pushed through the same frozen encoder that
    produces span representations — NOT the v1 bi-encoder table, whose
    dimensionality does not match the encoder hidden space (the §6/§9
    ``target_dim == hidden_size`` contract). Documents whose name text
    yields no tokens get a zero vector. Section vectors default to the
    document vectors (section granularity is a later refinement).
    """
    document_ids = sorted(document.id for document in inputs.corpus.documents)
    documents = _documents_by_id(inputs)
    rows = np.zeros((len(document_ids), encoder.hidden_size), dtype=np.float32)
    for row, document_id in enumerate(document_ids):
        document = documents[document_id]
        description = document.metadata.get("description")
        parts = [document.title]
        if isinstance(description, str):
            parts.append(description)
        text = " ".join(part for part in parts if part).strip() or document_id
        states = encoder.encode_tokens(text)
        if states.n_tokens:
            rows[row] = states.states.mean(axis=0)
    return TargetCatalog(document_ids, rows)


def _candidate_reps(
    candidates: Mapping[str, tuple[SpanCandidate, ...]],
    documents: Mapping[str, SourceDocument],
    doc_encoder: _DocumentEncoder,
) -> dict[str, NDArray[np.float32]]:
    """Span representations keyed by candidate id (documents encoded once)."""
    reps: dict[str, NDArray[np.float32]] = {}
    for document_id in sorted(candidates):
        states = doc_encoder.states_for(documents[document_id])
        for candidate in candidates[document_id]:
            reps[candidate.id] = span_representation(
                states, candidate.span, hand_features=_hand_features(candidate.features)
            )
    return reps


def _best_target_scores(
    reps: Mapping[str, NDArray[np.float32]],
    catalog: TargetCatalog,
    hidden_size: int,
) -> dict[str, float]:
    """Each candidate's best target cosine, for confirmed-negative denoising."""
    matrix = catalog.matrix
    norms = np.linalg.norm(matrix, axis=1) + 1e-8
    scores: dict[str, float] = {}
    for key, rep in reps.items():
        interior = rep[2 * hidden_size : 3 * hidden_size]
        interior_norm = float(np.linalg.norm(interior)) + 1e-8
        cosines = (matrix @ interior) / (norms * interior_norm)
        scores[key] = float(cosines.max()) if cosines.size else 0.0
    return scores


def train_inline_heads(  # noqa: PLR0913 -- stage-boundary signature fixed by the task
    inputs: InlineInputs,
    labels_path: Path,
    sample_path: Path,
    *,
    train_config: TrainConfig,
    seed: int,
    out_dir: Path,
    anchor_config: AnchorConfig | None = None,
    span_config: SpanConfig | None = None,
    encoder_factory: Callable[[], TokenStateEncoder] | None = None,
) -> TrainedHeads:
    """Phase 3: assemble representations, route tiers, train, and save the heads.

    ``encoder_factory`` injects the frozen token encoder; the default is the
    dependency-free ``HashingTokenEncoder(hidden_size=64)`` so the whole path
    runs without torch-adjacent model downloads. **The production path is
    Qwen token states**: pass ``lambda: QwenTokenEncoder(model, revision)``
    to train on real frozen-encoder representations. Target catalog vectors
    are re-derived in the encoder's hidden space (see :func:`_target_catalog`
    — title+description through the same encoder, mean-pooled), never taken
    from the 1024-dim v1 bi-encoder table.

    Steps: load the audit sample and labels -> build the anchor dictionary
    and candidate spans (unlabeled candidates become PU pseudo-negatives) ->
    encode span representations for every labeled item and candidate —
    labeled items are first narrowed from their full link-markup span to the
    anchor display text (:func:`_narrow_to_anchor`), matching the plain-text
    spans the heads score at inference ->
    :func:`~linkdiscovery.inline.train.build_training_data` (with best-target
    cosines for confirmed-negative denoising) -> :func:`~linkdiscovery.
    inline.train.train_heads` -> save under ``out_dir``. Deterministic on
    CPU for a fixed ``seed``.
    """
    sample = load_audit_sample(Path(sample_path))
    labels = load_audit_labels(Path(labels_path))
    if not labels:
        raise ContractError(f"no audit labels found at {labels_path}; annotate the sample first")
    encoder = encoder_factory() if encoder_factory is not None else HashingTokenEncoder(64)
    dictionary = _prepared_dictionary(inputs.corpus, anchor_config or AnchorConfig())
    candidates = _propose_all_spans(
        inputs, dictionary, span_config or SpanConfig(), inputs.relationships
    )
    documents = _documents_by_id(inputs)
    doc_encoder = _DocumentEncoder(encoder)
    reps = _candidate_reps(candidates, documents, doc_encoder)
    labeled_ids = {label.item_id for label in labels}
    for item in sample.items:
        if item.id not in labeled_ids or item.source_span is None:
            continue
        document = documents.get(item.source_document_id)
        if document is None:
            continue
        # Train on the anchor DISPLAY text, not the whole `[[target|anchor]]`
        # markup: inference scores plain-text candidate spans, so labeled
        # positives must be encoded (and hand-featurized) over the same kind
        # of span or the heads learn markup artifacts (seam-drift hazard).
        narrowed = _narrow_to_anchor(item, documents)
        span = narrowed.source_span
        assert span is not None  # _narrow_to_anchor never drops the span
        features = _audit_item_features(narrowed, document, dictionary, span)
        reps[item.id] = span_representation(
            doc_encoder.states_for(document),
            span,
            hand_features=_hand_features(features),
        )
    catalog = _target_catalog(inputs, encoder)
    table = SpanRepTable(
        reps,
        hidden_size=encoder.hidden_size,
        encoder_fingerprint=encoder.fingerprint,
        feature_names=INLINE_FEATURE_NAMES,
    )
    best_scores = _best_target_scores(
        {c.id: reps[c.id] for per_doc in candidates.values() for c in per_doc},
        catalog,
        encoder.hidden_size,
    )
    data = build_training_data(
        labels,
        sample,
        candidates,
        reps=table,
        catalog=catalog,
        best_target_scores=best_scores,
    )
    heads = train_heads(data, config=train_config, seed=seed)
    heads.save(Path(out_dir))
    _LOGGER.info(
        "trained heads on %d examples (%d targets); saved to %s",
        len(data.examples),
        len(catalog),
        out_dir,
    )
    return heads


def _placement_validity(candidate: SpanCandidate) -> float:
    """The deterministic placement rule shared with the baseline engine.

    Architecture A as built has no learned placement head (naturalness,
    retrieval, and reranker are the three trained heads), so the learned
    engine scores placement with the same explicit §4 rule as the baseline:
    prose spans decay with sentence position, non-prose spans floor at a
    small constant so a correct edge stays rankable.
    """
    prose = (
        1.0
        if candidate.region_kind is LinkRegionKind.PROSE
        else min(1.0, max(0.0, candidate.features.get("region_prose", 0.0)))
    )
    position = min(1.0, max(0.0, candidate.features.get("sentence_position", 0.0)))
    return max(prose * (1.0 - _PLACEMENT_POSITION_PENALTY * position), _PLACEMENT_NON_PROSE_FLOOR)


def _calibrated(combined: float, temperature: float) -> float:
    """Temperature-scale a combined score through its logit (SPEC §6 Q26).

    The score is clamped strictly inside (0, 1) before the logit so extreme
    values survive the round trip; the resulting probability preserves the
    ordering of the raw scores (temperature scaling never reorders).
    """
    clamped = min(1.0 - _PROBABILITY_EPSILON, max(_PROBABILITY_EPSILON, combined))
    logit = np.asarray([np.log(clamped / (1.0 - clamped))], dtype=np.float64)
    return float(apply_temperature(logit, temperature)[0])


def _learned_draft(  # noqa: PLR0913 -- internal helper threading fixed per-run context
    candidate: SpanCandidate,
    rep: NDArray[np.float32],
    heads: TrainedHeads,
    catalog: TargetCatalog,
    naturalness: float,
    retrieval_row: NDArray[np.float32],
    *,
    combine_weights: Mapping[str, float],
    calibration: float | None,
    run_id: str,
    corpus_id: str,
) -> InlineProposal | None:
    """Shortlist by retrieval probability, rerank, and draft the best target."""
    order = np.argsort(-retrieval_row, kind="stable")
    shortlist = [
        int(index) for index in order if catalog.document_ids[int(index)] != candidate.document_id
    ][:_LEARNED_SHORTLIST]
    if not shortlist:
        return None
    pair_rows = np.stack(
        [
            build_pair_features(
                rep,
                catalog.matrix[index],
                catalog.section_matrix[index],
                hidden_size=heads.hidden_size,
                hand_features=default_pair_hand_features(
                    rep, catalog.matrix[index], hidden_size=heads.hidden_size
                ),
            )
            for index in shortlist
        ]
    ).astype(np.float32)
    rerank = heads.score_pairs(pair_rows)
    best_position = min(
        range(len(shortlist)),
        key=lambda position: (
            -float(rerank[position]),
            -float(retrieval_row[shortlist[position]]),
            catalog.document_ids[shortlist[position]],
        ),
    )
    target_index = shortlist[best_position]
    target_id = catalog.document_ids[target_index]
    target_correctness = float(rerank[best_position])
    placement = _placement_validity(candidate)
    combined = combine_scores(naturalness, target_correctness, placement, combine_weights)
    proposal_id = fingerprint(
        {
            "corpus_id": corpus_id,
            "run_id": run_id,
            "source_document_id": candidate.document_id,
            "span_start": candidate.span.start,
            "span_end": candidate.span.end,
            "target_document_id": target_id,
            "model_version": heads.model_version,
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
        placement_validity=placement,
        combined_score=combined,
        calibrated_probability=(
            _calibrated(combined, calibration) if calibration is not None else None
        ),
        abstained=False,
        features={
            "retrieval_probability": float(retrieval_row[target_index]),
            "rerank_probability": target_correctness,
            "keyphraseness": candidate.features.get("keyphraseness", 0.0),
        },
        model_version=heads.model_version,
    )


def propose_inline_learned(  # noqa: PLR0913 -- stage-boundary signature fixed by the task
    inputs: InlineInputs,
    heads: TrainedHeads,
    *,
    anchor_config: AnchorConfig,
    span_config: SpanConfig,
    selection_config: SelectionConfig,
    calibration: float | None = None,
    run_id: str,
    encoder_factory: Callable[[], TokenStateEncoder] | None = None,
) -> InlineProposalSet:
    """The learned engine: spans -> reps -> three head scores -> selection.

    For every candidate span: the naturalness head scores linkability, the
    retrieval head's full-catalog softmax shortlists the top targets
    (self-link excluded), the reranker head picks the best target
    (``target_correctness``), and placement uses the deterministic §4 rule
    (see :func:`_placement_validity` — Architecture A trains no placement
    head). The combined score is the weighted geometric mean under
    ``selection_config.combine_weights``; ``calibration`` optionally applies
    temperature scaling to the combined score's logit, populating
    ``calibrated_probability``. Drafts then flow through
    :func:`~linkdiscovery.inline.select.select_proposals`.

    ``encoder_factory`` must produce the SAME encoder the heads were trained
    on; the fingerprint recorded at training time is verified and a mismatch
    raises :class:`~linkdiscovery.errors.ContractError`. Default: the
    ``HashingTokenEncoder`` at the heads' hidden size (the Qwen encoder is
    the production path — inject it here for real runs).
    """
    encoder = (
        encoder_factory() if encoder_factory is not None else HashingTokenEncoder(heads.hidden_size)
    )
    if encoder.fingerprint != heads.encoder_fingerprint:
        raise ContractError(
            f"propose_inline_learned: encoder fingerprint {encoder.fingerprint!r} does not "
            f"match the heads' training encoder {heads.encoder_fingerprint!r}; score with "
            "the encoder the heads were trained on"
        )
    if tuple(heads.feature_names) != INLINE_FEATURE_NAMES:
        raise ContractError(
            "propose_inline_learned: heads were trained with hand features "
            f"{heads.feature_names!r} but this workflow produces {INLINE_FEATURE_NAMES!r}"
        )
    dictionary = _prepared_dictionary(inputs.corpus, anchor_config)
    candidates = _propose_all_spans(inputs, dictionary, span_config, inputs.relationships)
    documents = _documents_by_id(inputs)
    doc_encoder = _DocumentEncoder(encoder)
    reps = _candidate_reps(candidates, documents, doc_encoder)
    catalog = _target_catalog(inputs, encoder)

    ordered = [c for doc_id in sorted(candidates) for c in candidates[doc_id]]
    drafts: list[InlineProposal] = []
    if ordered:
        rep_matrix = np.stack([reps[c.id] for c in ordered]).astype(np.float32)
        naturalness = heads.score_naturalness(rep_matrix)
        retrieval = heads.score_targets(rep_matrix, catalog.matrix)
        for row, candidate in enumerate(ordered):
            draft = _learned_draft(
                candidate,
                reps[candidate.id],
                heads,
                catalog,
                float(naturalness[row]),
                retrieval[row],
                combine_weights=selection_config.combine_weights,
                calibration=calibration,
                run_id=run_id,
                corpus_id=inputs.corpus.header.corpus_id,
            )
            if draft is not None:
                drafts.append(draft)
    _LOGGER.info("learned engine: %d drafts from %d candidate spans", len(drafts), len(ordered))
    return select_proposals(
        drafts,
        documents,
        config=selection_config,
        run_id=run_id,
        corpus_id=inputs.corpus.header.corpus_id,
    )
