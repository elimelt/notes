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

import io
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import numpy as np

from linkdiscovery.artifacts.cache import ArtifactCache
from linkdiscovery.artifacts.store import ArtifactStore
from linkdiscovery.contracts.units import Span
from linkdiscovery.embed import DefaultEmbedder
from linkdiscovery.embed.runtime import qualify_device
from linkdiscovery.embed.vectors import load_vector_table
from linkdiscovery.errors import ConfigError, ContractError
from linkdiscovery.fingerprint import canonical_json, combine_fingerprints, fingerprint
from linkdiscovery.inline.anchors import AnchorConfig, AnchorDictionary, build_anchor_dictionary
from linkdiscovery.inline.audit.annotate import load_audit_labels
from linkdiscovery.inline.audit.sampler import build_audit_sample
from linkdiscovery.inline.baseline import (
    BaselineConfig,
    levenshtein_ratio,
    propose_baseline,
    score_baseline,
)
from linkdiscovery.inline.benchmark import run_benchmark
from linkdiscovery.inline.calibrate import (
    ConformalAbstainer,
    apply_temperature,
    expected_calibration_error,
    fit_temperature,
    reliability_table,
)
from linkdiscovery.inline.encode import (
    HashingTokenEncoder,
    QwenTokenEncoder,
    TokenStateEncoder,
    TokenStates,
    WindowedTokenEncoder,
    span_representation,
)
from linkdiscovery.inline.evaluate import retrieval_metrics, score_benchmark, three_way_split
from linkdiscovery.inline.heads import build_pair_features
from linkdiscovery.inline.records import (
    REVIEW_ENGINES,
    AuditItem,
    AuditSample,
    Benchmark,
    InlineProposal,
    InlineReviewDecision,
    LinkRegionKind,
    SpanCandidate,
    Tier,
)
from linkdiscovery.inline.select import SelectionConfig, combine_scores, select_proposals
from linkdiscovery.inline.spans import (
    SpanConfig,
    _contains,
    _related_notes_spans,
    propose_spans,
    span_recall,
)
from linkdiscovery.inline.train import (
    SpanRepTable,
    TargetCatalog,
    TrainConfig,
    _consensus_tier,
    build_training_data,
    default_pair_hand_features,
    review_span_key,
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
    from collections.abc import Callable, Iterable, Mapping, Sequence

    from numpy.typing import NDArray

    from linkdiscovery.config import PipelineConfig
    from linkdiscovery.contracts.documents import Corpus, RelationshipSet, SourceDocument
    from linkdiscovery.contracts.embeddings import EmbeddingIndex
    from linkdiscovery.contracts.units import ProcessedCorpus
    from linkdiscovery.embed.vectors import VectorTable
    from linkdiscovery.inline.heads import TrainedHeads
    from linkdiscovery.inline.records import AuditLabel, InlineProposalSet

__all__ = [
    "INLINE_FEATURE_NAMES",
    "QWEN_STRIDE_TOKENS",
    "QWEN_WINDOW_TOKENS",
    "InlineInputs",
    "benchmark_engine",
    "build_anchor_artifacts",
    "build_audit_artifacts",
    "build_qwen_token_encoder",
    "check_span_recall",
    "evaluate_inline_engines",
    "families_from_document_ids",
    "fit_review_calibration",
    "load_audit_sample",
    "load_benchmark",
    "load_inline_inputs",
    "load_review_calibration",
    "load_review_decisions",
    "propose_inline_baseline",
    "propose_inline_learned",
    "train_inline_heads",
    "write_review_calibration",
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

QWEN_WINDOW_TOKENS: Final = 512
"""Token window for the windowed Qwen encoder (matches the v1 embedding budget)."""

QWEN_STRIDE_TOKENS: Final = 384
"""Window stride: every kept token sees >= 128 tokens of left context (SPEC §9)."""

_QWEN_PROBE_TEXT: Final = "A short device-qualification probe sentence for the token encoder."
"""Encoded end-to-end during device qualification — real work, not a framework check."""

_PLACEMENT_POSITION_PENALTY: Final = 0.25
"""Sentence-position penalty of the deterministic placement rule (baseline default)."""

_PLACEMENT_NON_PROSE_FLOOR: Final = 0.05
"""Placement floor for non-prose spans (SPEC §4: graph edges, not anchors)."""

_PROBABILITY_EPSILON: Final = 1e-6
"""Clamp keeping combined scores strictly inside (0, 1) before the logit."""

_REVIEW_CONFORMAL_ALPHA: Final = 0.2
"""Conformal target error rate fitted alongside review-outcome calibration."""

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


def load_review_decisions(path: Path) -> tuple[InlineReviewDecision, ...]:
    """Load a ``decisions.jsonl`` review file (the human-standard review).

    Each non-blank line must be one JSON-encoded review decision in the
    :meth:`~linkdiscovery.inline.records.InlineReviewDecision.from_dict`
    wire format. Order is preserved (the downstream routing and skips are
    deterministic in file order). Raises :class:`~linkdiscovery.errors.
    ContractError` naming the file — and the line, for per-line failures —
    when the file is missing, unreadable, or violates the contract; a review
    file is always passed explicitly, so an absent one is an error rather
    than an empty decision set.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"cannot read review decisions {path}: {exc}") from exc
    decisions: list[InlineReviewDecision] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ContractError(f"{path}: line {line_number} is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ContractError(
                f"{path}: line {line_number} must be a JSON object, got {type(data).__name__}"
            )
        decisions.append(InlineReviewDecision.from_dict(data))
    return tuple(decisions)


def load_benchmark(path: Path) -> Benchmark:
    """Load a frozen expert benchmark (``expert-benchmark-v1.json`` shape).

    Raises :class:`~linkdiscovery.errors.ContractError` when the file is
    missing, unreadable, or violates the :class:`~linkdiscovery.inline.
    records.Benchmark` contract.
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContractError(f"cannot read benchmark {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"benchmark {path} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ContractError(f"benchmark {path} must be a JSON object")
    return Benchmark.from_dict(raw)


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


def families_from_document_ids(document_ids: Iterable[str], *, depth: int = 1) -> dict[str, str]:
    """Topic-family labels derived from hierarchical document ids.

    Convention-based helper for corpora whose document ids are
    ``/``-separated paths (``distributed-systems/sharding``): the family of
    an id containing ``/`` is the ``"/".join`` of its first ``depth`` path
    segments; ids without ``/`` are omitted from the result (unknown
    family, never penalized). The core never assumes document ids are paths
    — callers opt into this convention by building the mapping here and
    passing it to :func:`~linkdiscovery.inline.baseline.propose_baseline`.
    Deterministic: output order follows input order.

    Raises :class:`~linkdiscovery.errors.ConfigError` when ``depth`` < 1.
    """
    if depth < 1:
        raise ConfigError(f"families_from_document_ids: depth must be >= 1, got {depth}")
    families: dict[str, str] = {}
    for document_id in document_ids:
        if "/" not in document_id:
            continue
        families[document_id] = "/".join(document_id.split("/")[:depth])
    return families


def _existing_span_links(
    relationships: RelationshipSet, processed: ProcessedCorpus
) -> dict[str, list[tuple[Span, str]]]:
    """(source_span, target_id) per source document for span-carrying links.

    The ``existing_links`` input of :func:`~linkdiscovery.inline.select.
    select_proposals` (same-target proximity suppression). Every span-
    carrying relationship counts whatever its kind, EXCEPT links whose span
    falls inside a Related-notes zone of the source document (the same
    zones the span stage derives via ``_related_notes_spans``). Rationale
    (audit guideline "Duplication rule"): when a target is linked both in
    prose and in a Related-notes entry, the Related-notes entry is the
    duplicate — prose is the preferred home — so a navigation entry must
    never suppress a nearby prose proposal for the same target. Measured on
    the 160-item human-standard review: the only review-ACCEPTED baseline
    items Rule A removed were blocked solely by Related-notes entries.
    Prose existing links suppress as before. Order within each source
    follows the relationship set's order.
    """
    related_zones = {
        processed_doc.document_id: _related_notes_spans(processed_doc)
        for processed_doc in processed.documents
    }
    links: dict[str, list[tuple[Span, str]]] = {}
    for relationship in relationships.relationships:
        span = relationship.source_span
        if span is None:
            continue
        zones = related_zones.get(relationship.source_id, ())
        if any(_contains(zone, span) for zone in zones):
            continue
        links.setdefault(relationship.source_id, []).append((span, relationship.target_id))
    return links


def _baseline_run(  # noqa: PLR0913 -- internal helper threading fixed per-run context
    inputs: InlineInputs,
    *,
    anchor_config: AnchorConfig,
    span_config: SpanConfig,
    baseline_config: BaselineConfig,
    selection_config: SelectionConfig,
    run_id: str,
    family_depth: int,
    temperature: float | None,
) -> tuple[list[InlineProposal], InlineProposalSet]:
    """The baseline engine's shared body: (pre-selection drafts, selected set).

    Factored out of :func:`propose_inline_baseline` so
    :func:`benchmark_engine` can see BOTH sides of the selection boundary
    without re-running the pipeline. Drafts are returned post-calibration
    (:func:`_calibrate_drafts`) — exactly what selection consumed.
    """
    dictionary = _prepared_dictionary(inputs.corpus, anchor_config)
    candidates = _propose_all_spans(inputs, dictionary, span_config, inputs.relationships)
    families = (
        None
        if family_depth == 0
        else families_from_document_ids(
            (document.id for document in inputs.corpus.documents), depth=family_depth
        )
    )
    drafts = _calibrate_drafts(
        propose_baseline(
            candidates,
            dictionary.lookup,
            _document_vectors(inputs),
            None,
            _titles(inputs),
            config=baseline_config,
            run_id=run_id,
            corpus_id=inputs.corpus.header.corpus_id,
            families=families,
        ),
        temperature,
    )
    selected = select_proposals(
        drafts,
        _documents_by_id(inputs),
        config=selection_config,
        run_id=run_id,
        corpus_id=inputs.corpus.header.corpus_id,
        existing_links=_existing_span_links(inputs.relationships, inputs.processed),
    )
    return drafts, selected


def propose_inline_baseline(  # noqa: PLR0913 -- stage-boundary signature fixed by the task
    inputs: InlineInputs,
    *,
    anchor_config: AnchorConfig,
    span_config: SpanConfig,
    baseline_config: BaselineConfig,
    selection_config: SelectionConfig,
    run_id: str = "adhoc",
    family_depth: int = 1,
    temperature: float | None = None,
) -> InlineProposalSet:
    """The full deterministic fallback path (SPEC §12 kill-criterion engine).

    Pipeline: anchor dictionary (with occurrences) -> candidate spans per
    prose document -> draft proposals via :func:`~linkdiscovery.inline.
    baseline.propose_baseline` (target lookup = dictionary, document vectors
    from the v1 document-view embedding index, ``span_vectors=None`` so the
    embedding-cosine term is 0, topic families from
    :func:`families_from_document_ids` at ``family_depth`` path segments —
    0 disables the cross-family prior) -> :func:`~linkdiscovery.inline.
    select.select_proposals` for thresholds, per-note budget, MMR, and
    same-target proximity suppression against the existing span-carrying
    links of ``inputs.relationships`` — the SAME relationship set the span
    stage sees on this path, so suppression and span exclusion agree —
    minus Related-notes navigation entries (see :func:`_existing_span_links`:
    per the guideline duplication rule they must not suppress prose).
    Self-links are excluded by the baseline; overlap with existing links is
    excluded by the span stage. Fully deterministic: no RNG anywhere on
    this path.

    ``temperature`` optionally applies review-fitted temperature scaling to
    every draft's combined score before selection (:func:`_calibrate_drafts`
    — the same single application point the learned engine uses), populating
    ``calibrated_probability`` so the accept threshold operates on a
    calibrated probability. Fit it with :func:`fit_review_calibration` over
    THIS engine's review decisions; temperatures are engine-specific.
    """
    _, selected = _baseline_run(
        inputs,
        anchor_config=anchor_config,
        span_config=span_config,
        baseline_config=baseline_config,
        selection_config=selection_config,
        run_id=run_id,
        family_depth=family_depth,
        temperature=temperature,
    )
    return selected


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


def _without_span_links(relationships: RelationshipSet) -> RelationshipSet:
    """A relationship set with every span-carrying ``explicit-link`` removed.

    Used wherever the pipeline must (attempt to) *rediscover* existing
    anchors: the span stage hard-excludes spans overlapping visible links,
    so hiding them is what lets audited positives become candidates again.
    """
    return replace(
        relationships,
        relationships=tuple(
            relationship
            for relationship in relationships.relationships
            if not (
                relationship.kind == _EXPLICIT_LINK_KIND and relationship.source_span is not None
            )
        ),
    )


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
    visible = _without_span_links(inputs.relationships)
    candidates = _propose_all_spans(inputs, dictionary, span_config, visible)
    documents = _documents_by_id(inputs)
    narrowed = [_narrow_to_anchor(item, documents) for item in sample.items]
    return span_recall(narrowed, candidates)


# ------------------------------------------------------ learned path helpers


def build_qwen_token_encoder(
    config: PipelineConfig,
    *,
    window_tokens: int = QWEN_WINDOW_TOKENS,
    stride_tokens: int = QWEN_STRIDE_TOKENS,
) -> tuple[TokenStateEncoder, str]:
    """The production token encoder: windowed frozen Qwen on the best device.

    Builds a :class:`~linkdiscovery.inline.encode.QwenTokenEncoder` from the
    config's pinned embedding ``model``/``revision``, wrapped in a
    :class:`~linkdiscovery.inline.encode.WindowedTokenEncoder` so long
    documents get token states end to end. Device selection reuses the
    embedder's qualification discipline (:func:`~linkdiscovery.embed.runtime.
    qualify_device`): each candidate in ``embedding.device_preference`` is
    probed by encoding a real sentence end to end, the first that works wins,
    and failures are logged as fallback events. Returns ``(encoder,
    device)`` — the device is reported to the caller because it is *not*
    part of the encoder fingerprint (same policy as the embedding cache:
    device changes how states are computed, not what they are).
    """
    built: dict[str, TokenStateEncoder] = {}

    def probe(device: str) -> None:
        candidate = WindowedTokenEncoder(
            QwenTokenEncoder(
                config.embedding.model,
                config.embedding.revision,
                device=device,
                max_tokens=window_tokens,
            ),
            window_tokens=window_tokens,
            stride_tokens=stride_tokens,
        )
        candidate.encode_tokens(_QWEN_PROBE_TEXT)
        built[device] = candidate

    device, events = qualify_device(config.embedding.device_preference, probe)
    for event in events:
        _LOGGER.warning("token encoder qualification: %s", event)
    encoder = built[device]
    _LOGGER.info(
        "token encoder: windowed qwen (window=%d, stride=%d) on %s",
        window_tokens,
        stride_tokens,
        device,
    )
    return encoder, device


def _token_states_to_bytes(states: TokenStates) -> bytes:
    """Serialize token states for the artifact-store cache (npz, no pickle)."""
    buffer = io.BytesIO()
    offsets = np.asarray(states.token_offsets, dtype=np.int64).reshape(states.n_tokens, 2)
    np.savez_compressed(buffer, offsets=offsets, states=states.states)
    return buffer.getvalue()


def _token_states_from_bytes(data: bytes, hidden_size: int) -> TokenStates | None:
    """Deserialize cached token states; corrupt or mismatched entries are misses."""
    try:
        with np.load(io.BytesIO(data), allow_pickle=False) as archive:
            offsets = np.asarray(archive["offsets"], dtype=np.int64)
            matrix = np.asarray(archive["states"], dtype=np.float32)
    except (OSError, ValueError, KeyError):
        return None
    if matrix.ndim != 2 or matrix.shape[1] != hidden_size:  # noqa: PLR2004 - 2 means "a matrix"
        return None
    if offsets.shape != (matrix.shape[0], 2):
        return None
    return TokenStates(tuple((int(start), int(end)) for start, end in offsets.tolist()), matrix)


def _hand_features(features: Mapping[str, float]) -> tuple[float, ...]:
    """A candidate's hand features in the fixed :data:`INLINE_FEATURE_NAMES` order."""
    return tuple(float(features.get(name, 0.0)) for name in INLINE_FEATURE_NAMES)


def _span_hand_features(
    document: SourceDocument,
    dictionary: AnchorDictionary,
    span: Span,
    *,
    region_kind: LinkRegionKind,
) -> dict[str, float]:
    """Hand features for a labeled span, mirroring the span-stage vocabulary.

    Audited spans overlap existing links (and reviewed spans belong to past
    engine runs), so the span stage never emits candidates for them; this
    helper recomputes the same feature vocabulary directly. One honest
    approximation: ``sentence_position`` is the span's relative position
    within the whole document rather than within its containing region (the
    region is not re-derived here).
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
        "region_prose": 1.0 if region_kind is LinkRegionKind.PROSE else 0.0,
    }


class _DocumentEncoder:
    """Per-document token states from one frozen encoder, computed once each.

    With an :class:`~linkdiscovery.artifacts.cache.ArtifactCache`, states are
    additionally persisted under the store's ``cache`` group, keyed by the
    encoder fingerprint combined with the document *content* hash (the same
    invalidation discipline as the embedding cache: content or encoder
    changes miss; device and batch shape never enter the key). Token states
    from the real model are expensive — this is what makes re-runs cheap.
    """

    def __init__(self, encoder: TokenStateEncoder, cache: ArtifactCache | None = None) -> None:
        self._encoder = encoder
        self._cache = cache
        self._states: dict[str, TokenStates] = {}

    @property
    def encoder(self) -> TokenStateEncoder:
        return self._encoder

    def _cache_key(self, text: str) -> str:
        return combine_fingerprints(
            self._encoder.fingerprint, fingerprint({"kind": "token-states", "text": text})
        )

    def states_for(self, document: SourceDocument) -> TokenStates:
        states = self._states.get(document.id)
        if states is not None:
            return states
        key = self._cache_key(document.content) if self._cache is not None else None
        if self._cache is not None and key is not None:
            data = self._cache.get_bytes(key)
            if data is not None:
                states = _token_states_from_bytes(data, self._encoder.hidden_size)
        if states is None:
            states = self._encoder.encode_tokens(document.content)
            if self._cache is not None and key is not None:
                self._cache.put_bytes(key, _token_states_to_bytes(states))
        self._states[document.id] = states
        return states


def _target_catalog(
    inputs: InlineInputs, encoder: TokenStateEncoder, cache: ArtifactCache | None = None
) -> TargetCatalog:
    """The closed-world target catalog in the *token-encoder* hidden space.

    Each document's vector is the mean of the token states of its
    ``title + description`` text pushed through the same frozen encoder that
    produces span representations — NOT the v1 bi-encoder table, whose
    dimensionality does not match the encoder hidden space (the §6/§9
    ``target_dim == hidden_size`` contract). Documents whose name text
    yields no tokens get a zero vector. Section vectors default to the
    document vectors (section granularity is a later refinement). With a
    ``cache``, each mean vector is persisted keyed by encoder fingerprint +
    name text, mirroring the token-state cache discipline.
    """
    document_ids = sorted(document.id for document in inputs.corpus.documents)
    documents = _documents_by_id(inputs)
    hidden = encoder.hidden_size
    expected_bytes = hidden * np.dtype(np.float32).itemsize
    rows = np.zeros((len(document_ids), hidden), dtype=np.float32)
    for row, document_id in enumerate(document_ids):
        document = documents[document_id]
        description = document.metadata.get("description")
        parts = [document.title]
        if isinstance(description, str):
            parts.append(description)
        text = " ".join(part for part in parts if part).strip() or document_id
        key = None
        if cache is not None:
            key = combine_fingerprints(
                encoder.fingerprint, fingerprint({"kind": "target-mean", "text": text})
            )
            data = cache.get_bytes(key)
            if data is not None and len(data) == expected_bytes:
                rows[row] = np.frombuffer(data, dtype=np.float32)
                continue
        states = encoder.encode_tokens(text)
        if states.n_tokens:
            rows[row] = states.states.mean(axis=0)
        if cache is not None and key is not None:
            cache.put_bytes(key, np.ascontiguousarray(rows[row], dtype=np.float32).tobytes())
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


def _labeled_item_reps(
    sample: AuditSample,
    labeled_ids: set[str],
    documents: Mapping[str, SourceDocument],
    dictionary: AnchorDictionary,
    doc_encoder: _DocumentEncoder,
) -> dict[str, NDArray[np.float32]]:
    """Span representations for labeled audit items, keyed by item id.

    Each item is encoded over the anchor DISPLAY text, not the whole
    ``[[target|anchor]]`` markup: inference scores plain-text candidate
    spans, so labeled positives must be encoded (and hand-featurized) over
    the same kind of span or the heads learn markup artifacts (seam-drift
    hazard). Items without a span or with an unknown source document are
    skipped.
    """
    reps: dict[str, NDArray[np.float32]] = {}
    for item in sample.items:
        if item.id not in labeled_ids or item.source_span is None:
            continue
        document = documents.get(item.source_document_id)
        if document is None:
            continue
        narrowed = _narrow_to_anchor(item, documents)
        span = narrowed.source_span
        assert span is not None  # _narrow_to_anchor never drops the span
        features = _span_hand_features(document, dictionary, span, region_kind=narrowed.region_kind)
        reps[item.id] = span_representation(
            doc_encoder.states_for(document),
            span,
            hand_features=_hand_features(features),
        )
    return reps


def _review_item_reps(
    decisions: Sequence[InlineReviewDecision],
    documents: Mapping[str, SourceDocument],
    dictionary: AnchorDictionary,
    doc_encoder: _DocumentEncoder,
) -> dict[str, NDArray[np.float32]]:
    """Span representations for review decisions, keyed by ``review_span_key``.

    Mirrors :func:`_labeled_item_reps` with one deliberate difference:
    review spans are NOT narrowed. A decision's span came from an engine
    proposal — a plain-text anchor span in the same raw document content the
    audit items index — so there is no link markup to strip, and narrowing
    would corrupt the coordinates. Hand features use the same
    :func:`_span_hand_features` vocabulary; the region is not re-derived
    (proposals only ever come from prose/list candidate spans), so
    ``region_kind`` is the honest prose approximation. Decisions whose
    reason is ``broken_span`` (untrustworthy coordinates) or whose source
    document is unknown are skipped — the same decisions the routing in
    :func:`~linkdiscovery.inline.train.review_training_examples` skips or
    cannot reach.
    """
    reps: dict[str, NDArray[np.float32]] = {}
    for decision in decisions:
        if decision.reason == "broken_span":
            continue
        document = documents.get(decision.source_document_id)
        if document is None:
            continue
        features = _span_hand_features(
            document, dictionary, decision.span, region_kind=LinkRegionKind.PROSE
        )
        reps[review_span_key(decision)] = span_representation(
            doc_encoder.states_for(document),
            decision.span,
            hand_features=_hand_features(features),
        )
    return reps


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
    token_state_cache: ArtifactCache | None = None,
    reviews: Sequence[InlineReviewDecision] = (),
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
    CPU for a fixed ``seed``. ``token_state_cache`` optionally persists
    per-document token states and catalog vectors across runs (keyed by
    encoder fingerprint + content hash — see :class:`_DocumentEncoder`).

    ``reviews`` optionally adds human-standard review decisions as
    per-head-labeled examples: each decision's span is encoded exactly like
    an audit item's (same encoder, same hand-feature vocabulary) but WITHOUT
    anchor narrowing — review spans are already plain-text anchor spans (see
    :func:`_review_item_reps`) — and routed per head by
    :func:`~linkdiscovery.inline.train.review_training_examples`.
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
    doc_encoder = _DocumentEncoder(encoder, cache=token_state_cache)
    reps = _candidate_reps(candidates, documents, doc_encoder)
    labeled_ids = {label.item_id for label in labels}
    reps.update(_labeled_item_reps(sample, labeled_ids, documents, dictionary, doc_encoder))
    reps.update(_review_item_reps(reviews, documents, dictionary, doc_encoder))
    catalog = _target_catalog(inputs, encoder, cache=token_state_cache)
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
        reviews=reviews,
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


def _calibrate_drafts(
    drafts: Sequence[InlineProposal], temperature: float | None
) -> list[InlineProposal]:
    """The single temperature-application point shared by BOTH engines.

    With a temperature, every draft's ``calibrated_probability`` becomes
    ``_calibrated(combined_score, T)`` before selection (selection prefers
    the calibrated probability via its ``_effective_score``); with ``None``
    drafts pass through untouched. Applying here — once, between drafting
    and selection — is what keeps the learned path from double-applying: no
    draft constructor sets ``calibrated_probability`` itself.
    """
    if temperature is None:
        return list(drafts)
    return [
        replace(draft, calibrated_probability=_calibrated(draft.combined_score, temperature))
        for draft in drafts
    ]


def fit_review_calibration(
    decisions: Sequence[InlineReviewDecision], *, engine: str
) -> dict[str, Any]:
    """Fit temperature scaling (and a conformal abstainer) from review outcomes.

    The human-standard review is exactly the held-out judgment set spec §6
    Q26 asks for: ``verdict == "accept"`` is the binary label, and the
    engine's ``combined_score`` — clamped strictly inside (0, 1) and pushed
    through its logit — is the raw confidence. :func:`~linkdiscovery.inline.
    calibrate.fit_temperature` fits T on the engine's decisions only (score
    scales are not comparable across engines), and the report carries the
    before/after :func:`~linkdiscovery.inline.calibrate.
    expected_calibration_error` plus the full :func:`~linkdiscovery.inline.
    calibrate.reliability_table` so the improvement is inspectable, not just
    asserted. A :class:`~linkdiscovery.inline.calibrate.ConformalAbstainer`
    is additionally fitted on the calibrated probabilities at
    ``target_error =`` :data:`_REVIEW_CONFORMAL_ALPHA` and serialized under
    ``"conformal"`` (threshold, target error, calibration counts) for the
    spec's stronger reject option.

    Returns a JSON-safe dict: ``{"engine", "n", "positives", "temperature",
    "ece_before", "ece_after", "reliability", "conformal"}``. Raises
    :class:`~linkdiscovery.errors.ConfigError` for an unknown engine and
    :class:`~linkdiscovery.errors.ContractError` when the engine has no
    decisions or its labels are degenerate (all one class — calibration
    needs both accepted and rejected examples).
    """
    if engine not in REVIEW_ENGINES:
        expected = ", ".join(sorted(REVIEW_ENGINES))
        raise ConfigError(
            f"fit_review_calibration: unknown engine {engine!r}; expected one of: {expected}"
        )
    subset = [decision for decision in decisions if decision.engine == engine]
    if not subset:
        raise ContractError(
            f"fit_review_calibration: no review decisions for engine {engine!r}; "
            "review that engine's proposals first"
        )
    scores = np.asarray([decision.combined_score for decision in subset], dtype=np.float64)
    clipped = np.clip(scores, _PROBABILITY_EPSILON, 1.0 - _PROBABILITY_EPSILON)
    logits = np.log(clipped / (1.0 - clipped))
    labels = np.asarray([decision.verdict == "accept" for decision in subset], dtype=np.bool_)
    try:
        temperature = fit_temperature(logits, labels)
        calibrated = apply_temperature(logits, temperature)
        abstainer = ConformalAbstainer().fit(
            calibrated, labels, target_error=_REVIEW_CONFORMAL_ALPHA
        )
    except ValueError as exc:
        raise ContractError(f"fit_review_calibration: engine {engine!r}: {exc}") from exc
    return {
        "engine": engine,
        "n": len(subset),
        "positives": int(labels.sum()),
        "temperature": float(temperature),
        "ece_before": expected_calibration_error(clipped, labels),
        "ece_after": expected_calibration_error(calibrated, labels),
        "reliability": reliability_table(calibrated, labels),
        "conformal": abstainer.to_dict(),
    }


def write_review_calibration(path: Path, results: Mapping[str, Mapping[str, Any]]) -> None:
    """Write review-calibration results as JSON, one entry per engine.

    ``results`` maps engine name to the :func:`fit_review_calibration` dict
    for that engine. Written atomically as canonical JSON, reloadable via
    :func:`load_review_calibration`. Raises :class:`~linkdiscovery.errors.
    ConfigError` for unknown engine keys.
    """
    unknown = sorted(set(results) - REVIEW_ENGINES)
    if unknown:
        expected = ", ".join(sorted(REVIEW_ENGINES))
        raise ConfigError(
            f"write_review_calibration: unknown engine key(s) {unknown}; expected only: {expected}"
        )
    payload = {engine: dict(result) for engine, result in results.items()}
    atomic_write_text(Path(path), canonical_json(payload) + "\n")


def load_review_calibration(path: Path) -> dict[str, dict[str, Any]]:
    """Load a review-calibration file written by :func:`write_review_calibration`.

    Validates the shape a caller depends on — a JSON object keyed by known
    engine names, each entry carrying a finite positive ``temperature`` —
    and raises :class:`~linkdiscovery.errors.ContractError` otherwise (the
    remaining report fields are informational and pass through untouched).
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContractError(f"cannot read review calibration {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"review calibration {path} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ContractError(f"review calibration {path} must be a JSON object")
    result: dict[str, dict[str, Any]] = {}
    for engine, entry in raw.items():
        if engine not in REVIEW_ENGINES:
            expected = ", ".join(sorted(REVIEW_ENGINES))
            raise ContractError(
                f"review calibration {path}: unknown engine {engine!r}; expected one of: {expected}"
            )
        if not isinstance(entry, dict):
            raise ContractError(
                f"review calibration {path}: entry for {engine!r} must be a JSON object"
            )
        temperature = entry.get("temperature")
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, int | float)
            or not np.isfinite(temperature)
            or temperature <= 0.0
        ):
            raise ContractError(
                f"review calibration {path}: entry for {engine!r} must carry a finite "
                f"positive 'temperature', got {temperature!r}"
            )
        result[engine] = entry
    return result


def _learned_draft(  # noqa: PLR0913 -- internal helper threading fixed per-run context
    candidate: SpanCandidate,
    rep: NDArray[np.float32],
    heads: TrainedHeads,
    catalog: TargetCatalog,
    naturalness: float,
    retrieval_row: NDArray[np.float32],
    *,
    combine_weights: Mapping[str, float],
    run_id: str,
    corpus_id: str,
) -> InlineProposal | None:
    """Shortlist by retrieval probability, rerank, and draft the best target.

    Drafts always carry ``calibrated_probability=None``: temperature scaling
    is applied in one shared post-draft pass (:func:`_calibrate_drafts`) so
    the baseline and learned engines cannot diverge — or double-apply.
    """
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
        calibrated_probability=None,
        abstained=False,
        features={
            "retrieval_probability": float(retrieval_row[target_index]),
            "rerank_probability": target_correctness,
            "keyphraseness": candidate.features.get("keyphraseness", 0.0),
        },
        model_version=heads.model_version,
    )


def _learned_drafts(  # noqa: PLR0913 -- internal helper threading fixed per-run context
    candidates: Mapping[str, tuple[SpanCandidate, ...]],
    documents: Mapping[str, SourceDocument],
    doc_encoder: _DocumentEncoder,
    heads: TrainedHeads,
    catalog: TargetCatalog,
    *,
    combine_weights: Mapping[str, float],
    run_id: str,
    corpus_id: str,
) -> list[InlineProposal]:
    """Draft one learned proposal per scoreable candidate span (no selection)."""
    reps = _candidate_reps(candidates, documents, doc_encoder)
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
                combine_weights=combine_weights,
                run_id=run_id,
                corpus_id=corpus_id,
            )
            if draft is not None:
                drafts.append(draft)
    _LOGGER.info("learned engine: %d drafts from %d candidate spans", len(drafts), len(ordered))
    return drafts


def _learned_run(  # noqa: PLR0913 -- internal helper threading fixed per-run context
    inputs: InlineInputs,
    heads: TrainedHeads,
    *,
    anchor_config: AnchorConfig,
    span_config: SpanConfig,
    selection_config: SelectionConfig,
    temperature: float | None,
    run_id: str,
    encoder_factory: Callable[[], TokenStateEncoder] | None,
    token_state_cache: ArtifactCache | None,
) -> tuple[list[InlineProposal], InlineProposalSet]:
    """The learned engine's shared body: (pre-selection drafts, selected set).

    Factored out of :func:`propose_inline_learned` so
    :func:`benchmark_engine` can see BOTH sides of the selection boundary
    without re-running the pipeline. Drafts are returned post-calibration
    (:func:`_calibrate_drafts`) — exactly what selection consumed.
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
    doc_encoder = _DocumentEncoder(encoder, cache=token_state_cache)
    catalog = _target_catalog(inputs, encoder, cache=token_state_cache)
    drafts = _calibrate_drafts(
        _learned_drafts(
            candidates,
            documents,
            doc_encoder,
            heads,
            catalog,
            combine_weights=selection_config.combine_weights,
            run_id=run_id,
            corpus_id=inputs.corpus.header.corpus_id,
        ),
        temperature,
    )
    selected = select_proposals(
        drafts,
        documents,
        config=selection_config,
        run_id=run_id,
        corpus_id=inputs.corpus.header.corpus_id,
        existing_links=_existing_span_links(inputs.relationships, inputs.processed),
    )
    return drafts, selected


def propose_inline_learned(  # noqa: PLR0913 -- stage-boundary signature fixed by the task
    inputs: InlineInputs,
    heads: TrainedHeads,
    *,
    anchor_config: AnchorConfig,
    span_config: SpanConfig,
    selection_config: SelectionConfig,
    calibration: float | None = None,
    temperature: float | None = None,
    run_id: str,
    encoder_factory: Callable[[], TokenStateEncoder] | None = None,
    token_state_cache: ArtifactCache | None = None,
) -> InlineProposalSet:
    """The learned engine: spans -> reps -> three head scores -> selection.

    For every candidate span: the naturalness head scores linkability, the
    retrieval head's full-catalog softmax shortlists the top targets
    (self-link excluded), the reranker head picks the best target
    (``target_correctness``), and placement uses the deterministic §4 rule
    (see :func:`_placement_validity` — Architecture A trains no placement
    head). The combined score is the weighted geometric mean under
    ``selection_config.combine_weights``. Drafts then flow through
    :func:`~linkdiscovery.inline.select.select_proposals`, with same-target
    proximity suppression against the existing span-carrying links of
    ``inputs.relationships`` — the SAME relationship set the span stage sees
    on this path — minus Related-notes navigation entries (see
    :func:`_existing_span_links`). (The topic-family prior is baseline-only;
    the learned reranker is expected to learn that signal from data.)

    Temperature scaling: ``temperature`` and ``calibration`` are the SAME
    knob. ``calibration`` is this function's original parameter name;
    ``temperature`` is the engine-neutral name shared with
    :func:`propose_inline_baseline` since review-fitted calibration
    (:func:`fit_review_calibration`) landed. Both apply one post-draft
    temperature-scaling pass (:func:`_calibrate_drafts`) — drafts themselves
    never set ``calibrated_probability``, so the value is applied exactly
    once. Passing both raises :class:`~linkdiscovery.errors.ConfigError`
    (ambiguous, even when equal).

    ``encoder_factory`` must produce the SAME encoder the heads were trained
    on; the fingerprint recorded at training time is verified and a mismatch
    raises :class:`~linkdiscovery.errors.ContractError`. Default: the
    ``HashingTokenEncoder`` at the heads' hidden size (the Qwen encoder is
    the production path — inject it here for real runs).
    ``token_state_cache`` optionally persists per-document token states and
    catalog vectors across runs (see :class:`_DocumentEncoder`).
    """
    if calibration is not None and temperature is not None:
        raise ConfigError(
            "propose_inline_learned: pass either 'temperature' or the legacy 'calibration' "
            "alias, not both; they are the same temperature-scaling knob"
        )
    _, selected = _learned_run(
        inputs,
        heads,
        anchor_config=anchor_config,
        span_config=span_config,
        selection_config=selection_config,
        temperature=temperature if temperature is not None else calibration,
        run_id=run_id,
        encoder_factory=encoder_factory,
        token_state_cache=token_state_cache,
    )
    return selected


def benchmark_engine(  # noqa: PLR0913 -- stage-boundary signature fixed by the task
    inputs: InlineInputs,
    benchmark: Benchmark,
    *,
    engine: str,
    heads: TrainedHeads | None = None,
    anchor_config: AnchorConfig | None = None,
    span_config: SpanConfig | None = None,
    selection_config: SelectionConfig | None = None,
    baseline_config: BaselineConfig | None = None,
    family_depth: int = 1,
    temperature: float | None = None,
    run_id: str = "benchmark",
    encoder_factory: Callable[[], TokenStateEncoder] | None = None,
    token_state_cache: ArtifactCache | None = None,
) -> dict[str, Any]:
    """Run one engine over the real corpus and score the frozen benchmark.

    Reuses the exact draft-then-select bodies of the propose functions
    (:func:`_baseline_run` / :func:`_learned_run` — same configs, same
    calibration point, same suppression inputs), so the benchmark judges
    the engine precisely as it ships, then hands both sides of the
    selection boundary to :func:`~linkdiscovery.inline.benchmark.
    run_benchmark`: pre-selection drafts feed the head-quality kinds,
    the accepted post-selection proposals feed the commitment kinds (see
    that function for the per-kind semantics). ``temperature`` applies the
    engine's review-fitted temperature (:func:`fit_review_calibration`)
    exactly as ``inline propose`` would.

    Returns ``{"outcomes": {case_id: bool}, "scores":
    score_benchmark(benchmark, outcomes)}`` — cases whose source document
    is missing or whose span cannot be located are omitted from
    ``outcomes`` and reported as unevaluated by the scores. Raises
    :class:`~linkdiscovery.errors.ConfigError` for an unknown ``engine`` or
    a learned run without ``heads``.
    """
    resolved_selection = selection_config if selection_config is not None else SelectionConfig()
    if engine == "baseline":
        drafts, selected = _baseline_run(
            inputs,
            anchor_config=anchor_config or AnchorConfig(),
            span_config=span_config or SpanConfig(),
            baseline_config=baseline_config or BaselineConfig(),
            selection_config=resolved_selection,
            run_id=run_id,
            family_depth=family_depth,
            temperature=temperature,
        )
    elif engine == "learned":
        if heads is None:
            raise ConfigError("benchmark_engine: heads are required with engine 'learned'")
        drafts, selected = _learned_run(
            inputs,
            heads,
            anchor_config=anchor_config or AnchorConfig(),
            span_config=span_config or SpanConfig(),
            selection_config=resolved_selection,
            temperature=temperature,
            run_id=run_id,
            encoder_factory=encoder_factory,
            token_state_cache=token_state_cache,
        )
    else:
        raise ConfigError(
            f"benchmark_engine: unknown engine {engine!r}; expected 'baseline' or 'learned'"
        )
    outcomes = run_benchmark(
        benchmark, drafts=drafts, selected=selected, documents=_documents_by_id(inputs)
    )
    _LOGGER.info(
        "benchmark (%s engine): %d of %d cases evaluated",
        engine,
        len(outcomes),
        len(benchmark.cases),
    )
    return {"outcomes": outcomes, "scores": score_benchmark(benchmark, outcomes)}


# ------------------------------------------------------------- evaluation


_EVAL_SHORTLIST: Final = 10
"""Retrieval shortlist reranked during evaluation (recall@k reported to k=10)."""

_EVAL_RANKING_THRESHOLD: Final = 0.05
"""Near-zero accept threshold producing full ranked accepted lists for
matched-budget comparison (budgets/MMR/no-overlap constraints still apply)."""

_EVAL_BUDGETS: Final = (25, 50, 100, 200, 400)
"""Matched acceptance counts at which held-out recovery is compared."""

_RETRIEVAL_K_VALUES: Final = (1, 3, 5, 10)
_POSITIVE_TIERS: Final = frozenset({Tier.A, Tier.B})


def _consensus_by_item(
    labels: Sequence[AuditLabel], sample: AuditSample
) -> tuple[list[str], dict[str, Tier], dict[str, bool]]:
    """(labeled item ids, consensus tier, consensus anchor-naturalness) per item.

    Tier consensus is the trainer's pessimistic majority rule
    (:func:`~linkdiscovery.inline.train._consensus_tier`); anchor naturalness
    is a strict majority of the annotators' ``anchor_natural`` votes (ties
    resolve to *not natural* — the same pessimism).
    """
    items_by_id = {item.id: item for item in sample.items}
    by_item: dict[str, dict[str, AuditLabel]] = {}
    for label in labels:
        if label.item_id in items_by_id:
            by_item.setdefault(label.item_id, {})[label.annotator] = label
    labeled_ids = sorted(by_item)
    tiers = {item_id: _consensus_tier(tuple(by_item[item_id].values())) for item_id in labeled_ids}
    natural: dict[str, bool] = {}
    for item_id in labeled_ids:
        votes = [label.anchor_natural for label in by_item[item_id].values()]
        natural[item_id] = sum(votes) * 2 > len(votes)
    return labeled_ids, tiers, natural


@dataclass(frozen=True, eq=False)
class _EvalItem:
    """One labeled test-split item, narrowed and encoded for scoring."""

    item: AuditItem
    candidate: SpanCandidate
    rep: NDArray[np.float32]


def _eval_test_items(
    sample: AuditSample,
    test_ids: Sequence[str],
    documents: Mapping[str, SourceDocument],
    dictionary: AnchorDictionary,
    doc_encoder: _DocumentEncoder,
) -> list[_EvalItem]:
    """Narrow, featurize, and encode every scoreable test-split item.

    Mirrors the training path exactly (display-text spans, the same hand
    features), and additionally builds a synthetic ``SpanCandidate`` over the
    same span so the deterministic baseline can score the *same* anchors.
    """
    wanted = set(test_ids)
    out: list[_EvalItem] = []
    for item in sample.items:
        if item.id not in wanted or item.source_span is None:
            continue
        document = documents.get(item.source_document_id)
        if document is None:
            continue
        narrowed = _narrow_to_anchor(item, documents)
        span = narrowed.source_span
        assert span is not None  # _narrow_to_anchor never drops the span
        features = _span_hand_features(document, dictionary, span, region_kind=narrowed.region_kind)
        rep = span_representation(
            doc_encoder.states_for(document), span, hand_features=_hand_features(features)
        )
        text = document.content[span.start : span.end]
        candidate = SpanCandidate(
            id=f"eval-{item.id}",
            document_id=item.source_document_id,
            unit_id=None,
            span=span,
            text=text,
            region_kind=item.region_kind,
            word_count=len(text.split()),
            features=features,
        )
        out.append(_EvalItem(item=narrowed, candidate=candidate, rep=rep))
    return out


def _baseline_target_ranking(
    candidate: SpanCandidate,
    dictionary: AnchorDictionary,
    titles: Mapping[str, str],
    config: BaselineConfig,
) -> list[str]:
    """The baseline engine's full target ranking for one span.

    Same target pool and scoring as :func:`~linkdiscovery.inline.baseline.
    propose_baseline` (dictionary lookup union exact title matches, minus the
    source; embedding cosine 0.0 exactly as the production baseline runs with
    ``span_vectors=None``), ranked by target correctness. Spans outside the
    dictionary rank nothing — the baseline's honest recall ceiling.
    """
    counts = dict(dictionary.lookup(candidate.text))
    normalized = " ".join(candidate.text.split()).casefold()
    title_matches = {
        target_id
        for target_id, title in titles.items()
        if " ".join(title.split()).casefold() == normalized
    }
    targets = (set(counts) | title_matches) - {candidate.document_id}
    if not targets:
        return []
    ambiguity = len(targets)
    total = sum(counts.values())
    scored: list[tuple[float, str]] = []
    for target_id in sorted(targets):
        commonness = counts.get(target_id, 0) / total if total else 0.0
        levenshtein_title = levenshtein_ratio(
            candidate.text.casefold(), titles.get(target_id, "").casefold()
        )
        _, correctness, _ = score_baseline(
            candidate,
            target_id,
            commonness=commonness,
            target_vector_sim=0.0,
            ambiguity=ambiguity,
            levenshtein_title=levenshtein_title,
            config=config,
        )
        scored.append((-correctness, target_id))
    scored.sort()
    return [target_id for _, target_id in scored]


def _eval_retrieval(
    positives: Sequence[_EvalItem],
    heads: TrainedHeads,
    catalog: TargetCatalog,
    dictionary: AnchorDictionary,
    titles: Mapping[str, str],
    baseline_config: BaselineConfig,
) -> dict[str, Any]:
    """Recall@k + MRR for learned retrieval, retrieval+rerank, and baseline."""
    if not positives:
        empty = retrieval_metrics([], [], k_values=_RETRIEVAL_K_VALUES)
        return {
            "learned_retrieval": dict(empty),
            "learned_reranked": dict(empty),
            "baseline": dict(empty),
        }
    gold = [entry.item.target_document_id for entry in positives]
    rows = np.stack([entry.rep for entry in positives]).astype(np.float32)
    retrieval = heads.score_targets(rows, catalog.matrix)
    learned_ranked: list[list[str]] = []
    reranked_ranked: list[list[str]] = []
    for row, entry in enumerate(positives):
        order = [
            int(index)
            for index in np.argsort(-retrieval[row], kind="stable")
            if catalog.document_ids[int(index)] != entry.item.source_document_id
        ]
        ids = [catalog.document_ids[index] for index in order]
        learned_ranked.append(ids)
        shortlist = order[:_EVAL_SHORTLIST]
        pair_rows = np.stack(
            [
                build_pair_features(
                    entry.rep,
                    catalog.matrix[index],
                    catalog.section_matrix[index],
                    hidden_size=heads.hidden_size,
                    hand_features=default_pair_hand_features(
                        entry.rep, catalog.matrix[index], hidden_size=heads.hidden_size
                    ),
                )
                for index in shortlist
            ]
        ).astype(np.float32)
        rerank = heads.score_pairs(pair_rows)
        rerank_order = sorted(
            range(len(shortlist)),
            key=lambda position: (
                -float(rerank[position]),
                -float(retrieval[row, shortlist[position]]),
                catalog.document_ids[shortlist[position]],
            ),
        )
        reranked_ranked.append(
            [catalog.document_ids[shortlist[position]] for position in rerank_order]
            + ids[len(shortlist) :]
        )
    baseline_ranked = [
        _baseline_target_ranking(entry.candidate, dictionary, titles, baseline_config)
        for entry in positives
    ]
    return {
        "learned_retrieval": retrieval_metrics(learned_ranked, gold, k_values=_RETRIEVAL_K_VALUES),
        "learned_reranked": retrieval_metrics(reranked_ranked, gold, k_values=_RETRIEVAL_K_VALUES),
        "baseline": retrieval_metrics(baseline_ranked, gold, k_values=_RETRIEVAL_K_VALUES),
    }


def _eval_naturalness(
    test_items: Sequence[_EvalItem], natural: Mapping[str, bool], heads: TrainedHeads
) -> dict[str, Any]:
    """Naturalness-head separation on the test split: means and pairwise AUC."""
    scored = [
        (natural[entry.item.id], entry.rep) for entry in test_items if entry.item.id in natural
    ]
    if not scored:
        return {
            "n_natural": 0,
            "n_not_natural": 0,
            "mean_natural": 0.0,
            "mean_not_natural": 0.0,
            "auc": 0.0,
        }
    rows = np.stack([rep for _, rep in scored]).astype(np.float32)
    scores = heads.score_naturalness(rows)
    positives = [float(score) for (flag, _), score in zip(scored, scores, strict=True) if flag]
    negatives = [float(score) for (flag, _), score in zip(scored, scores, strict=True) if not flag]
    auc = 0.0
    if positives and negatives:
        wins = sum(
            1.0 if pos > neg else 0.5 if pos == neg else 0.0
            for pos in positives
            for neg in negatives
        )
        auc = wins / (len(positives) * len(negatives))
    return {
        "n_natural": len(positives),
        "n_not_natural": len(negatives),
        "mean_natural": sum(positives) / len(positives) if positives else 0.0,
        "mean_not_natural": sum(negatives) / len(negatives) if negatives else 0.0,
        "auc": auc,
    }


def _accepted(proposal_set: InlineProposalSet) -> list[InlineProposal]:
    """Accepted proposals in global selection-rank order."""
    return [proposal for proposal in proposal_set.proposals if not proposal.abstained]


def _recovered_count(accepted: Sequence[InlineProposal], positives: Sequence[_EvalItem]) -> int:
    """How many audited positives an accepted set recovers.

    A positive is recovered when some accepted proposal shares its source
    document and target and its span overlaps the (narrowed) audited span.
    """
    count = 0
    for entry in positives:
        span = entry.item.source_span
        if span is None:
            continue
        for proposal in accepted:
            if (
                proposal.source_document_id == entry.item.source_document_id
                and proposal.target_document_id == entry.item.target_document_id
                and proposal.span.start < span.end
                and span.start < proposal.span.end
            ):
                count += 1
                break
    return count


def _proposal_summary(proposal: InlineProposal) -> dict[str, Any]:
    """A compact JSON-safe view of one proposal for eyeball comparison."""
    return {
        "source": proposal.source_document_id,
        "anchor": proposal.anchor_text,
        "target": proposal.target_document_id,
        "combined": round(proposal.combined_score, 4),
        "naturalness": round(proposal.naturalness, 4),
        "target_correctness": round(proposal.target_correctness, 4),
    }


@dataclass(frozen=True, eq=False)
class _EngineContext:
    """Shared, already-encoded state for running both engines during eval."""

    inputs: InlineInputs
    heads: TrainedHeads
    dictionary: AnchorDictionary
    documents: dict[str, SourceDocument]
    doc_encoder: _DocumentEncoder
    catalog: TargetCatalog
    span_config: SpanConfig
    selection_config: SelectionConfig
    baseline_config: BaselineConfig
    baseline_selection: SelectionConfig

    def drafts_for(
        self, relationships: RelationshipSet, run_id: str
    ) -> tuple[list[InlineProposal], tuple[InlineProposal, ...]]:
        """(learned drafts, baseline drafts) over one candidate-span pool."""
        candidates = _propose_all_spans(
            self.inputs, self.dictionary, self.span_config, relationships
        )
        corpus_id = self.inputs.corpus.header.corpus_id
        learned = _learned_drafts(
            candidates,
            self.documents,
            self.doc_encoder,
            self.heads,
            self.catalog,
            combine_weights=self.selection_config.combine_weights,
            run_id=f"{run_id}-learned",
            corpus_id=corpus_id,
        )
        baseline = propose_baseline(
            candidates,
            self.dictionary.lookup,
            _document_vectors(self.inputs),
            None,
            _titles(self.inputs),
            config=self.baseline_config,
            run_id=f"{run_id}-baseline",
            corpus_id=corpus_id,
        )
        return learned, baseline

    def select(
        self,
        drafts: Sequence[InlineProposal],
        config: SelectionConfig,
        run_id: str,
        *,
        existing_links: Mapping[str, Sequence[tuple[Span, str]]] | None = None,
    ) -> list[InlineProposal]:
        """Accepted proposals (rank order) after global selection of ``drafts``.

        INVARIANT (same-target proximity suppression): ``existing_links``
        must be derived from the SAME relationship set the caller passed to
        :meth:`drafts_for` — the eval-recovery path hides held-out links
        from the span stage, and deriving suppression from the full set
        there would wrongly suppress recovery of the hidden positives.
        """
        return _accepted(
            select_proposals(
                drafts,
                self.documents,
                config=config,
                run_id=run_id,
                corpus_id=self.inputs.corpus.header.corpus_id,
                existing_links=existing_links,
            )
        )


def _eval_recovery(context: _EngineContext, positives: Sequence[_EvalItem]) -> dict[str, Any]:
    """Matched-budget recovery of held-out audited positives (links hidden).

    Both engines run over the SAME candidate pool with span-carrying explicit
    links hidden (the audited positives are existing links, which the span
    stage would otherwise exclude). Selection runs at a near-zero threshold
    so both ranked accepted lists are as long as budgets allow, then recovery
    is compared at *matched acceptance counts* — the honest comparison the
    spec asks for, since threshold scales are not comparable across engines.
    Honesty note: the anchor dictionary is still built from the full corpus
    (hiding links would collapse keyphraseness); both engines see the same
    dictionary, so the comparison stays fair. Same-target proximity
    suppression is likewise driven by the STRIPPED relationship set (the
    same one the span stage sees here): the hidden positives being recovered
    ARE existing links, and suppressing near the full set would wrongly
    reject exactly the recoveries this evaluation measures.
    """
    visible = _without_span_links(context.inputs.relationships)
    existing = _existing_span_links(visible, context.inputs.processed)
    learned_drafts, baseline_drafts = context.drafts_for(visible, "eval-recovery")
    ranking_config = replace(context.selection_config, accept_threshold=_EVAL_RANKING_THRESHOLD)
    learned_ranked = context.select(
        learned_drafts, ranking_config, "eval-recovery-learned", existing_links=existing
    )
    baseline_ranked = context.select(
        baseline_drafts, ranking_config, "eval-recovery-baseline", existing_links=existing
    )
    budgets = sorted(
        {
            *(_EVAL_BUDGETS),
            min(len(learned_ranked), len(baseline_ranked)),
        }
    )
    n_positives = len(positives)
    at_budget: list[dict[str, float]] = []
    for budget in budgets:
        if budget < 1:
            continue
        learned_recovered = _recovered_count(learned_ranked[:budget], positives)
        baseline_recovered = _recovered_count(baseline_ranked[:budget], positives)
        at_budget.append(
            {
                "budget": float(budget),
                "learned_recovered": float(learned_recovered),
                "baseline_recovered": float(baseline_recovered),
                "learned_fraction": learned_recovered / n_positives if n_positives else 0.0,
                "baseline_fraction": baseline_recovered / n_positives if n_positives else 0.0,
            }
        )
    return {
        "n_test_positives": n_positives,
        "learned_ranked_total": len(learned_ranked),
        "baseline_ranked_total": len(baseline_ranked),
        "at_budget": at_budget,
    }


def _eval_corpus(
    context: _EngineContext, sweep_thresholds: Sequence[float], top_n: int
) -> dict[str, Any]:
    """Full-corpus comparison with existing links visible (production shape).

    Both spans and same-target proximity suppression run against the FULL
    relationship set (``context.inputs.relationships``) — the production
    shape, where suppressing proposals that duplicate an author's nearby
    link is exactly the intended behavior.
    """
    existing = _existing_span_links(context.inputs.relationships, context.inputs.processed)
    learned_drafts, baseline_drafts = context.drafts_for(
        context.inputs.relationships, "eval-corpus"
    )
    learned_accepted = context.select(
        learned_drafts, context.selection_config, "eval-corpus-learned", existing_links=existing
    )
    baseline_accepted = context.select(
        baseline_drafts, context.baseline_selection, "eval-corpus-baseline", existing_links=existing
    )
    pairs_learned = {
        (p.source_document_id, p.span.start, p.span.end, p.target_document_id)
        for p in learned_accepted
    }
    pairs_baseline = {
        (p.source_document_id, p.span.start, p.span.end, p.target_document_id)
        for p in baseline_accepted
    }
    edges_learned = {(p.source_document_id, p.target_document_id) for p in learned_accepted}
    edges_baseline = {(p.source_document_id, p.target_document_id) for p in baseline_accepted}
    sweep = [
        {
            "threshold": float(threshold),
            "learned_accepted": float(
                len(
                    context.select(
                        learned_drafts,
                        replace(context.selection_config, accept_threshold=threshold),
                        "eval-sweep-learned",
                        existing_links=existing,
                    )
                )
            ),
            "baseline_accepted": float(
                len(
                    context.select(
                        baseline_drafts,
                        replace(context.selection_config, accept_threshold=threshold),
                        "eval-sweep-baseline",
                        existing_links=existing,
                    )
                )
            ),
        }
        for threshold in sweep_thresholds
    ]
    return {
        "learned_accepted": len(learned_accepted),
        "baseline_accepted": len(baseline_accepted),
        "learned_threshold": context.selection_config.accept_threshold,
        "baseline_threshold": context.baseline_selection.accept_threshold,
        "accepted_overlap_span_target": len(pairs_learned & pairs_baseline),
        "accepted_overlap_source_target": len(edges_learned & edges_baseline),
        "learned_top": [_proposal_summary(p) for p in learned_accepted[:top_n]],
        "baseline_top": [_proposal_summary(p) for p in baseline_accepted[:top_n]],
        "threshold_sweep": sweep,
    }


def evaluate_inline_engines(  # noqa: PLR0913 -- stage-boundary signature fixed by the task
    inputs: InlineInputs,
    heads: TrainedHeads,
    labels_path: Path,
    sample_path: Path,
    *,
    anchor_config: AnchorConfig | None = None,
    span_config: SpanConfig | None = None,
    selection_config: SelectionConfig | None = None,
    baseline_config: BaselineConfig | None = None,
    baseline_accept_threshold: float | None = None,
    encoder_factory: Callable[[], TokenStateEncoder] | None = None,
    token_state_cache: ArtifactCache | None = None,
    seed: int = 0,
    test_fraction: float = 0.2,
    val_fraction: float = 0.2,
    sweep_thresholds: Sequence[float] = (0.3, 0.4, 0.5, 0.6, 0.65, 0.7, 0.8, 0.9),
    top_n: int = 10,
) -> dict[str, Any]:
    """Honest learned-vs-baseline evaluation on the audited labels (SPEC §7).

    Sections of the returned JSON-safe dict:

    - ``split``: the document+anchor+target grouped three-way split of the
      labeled audit items (:func:`~linkdiscovery.inline.evaluate.
      three_way_split`, seed reported), with the *achieved* fractions —
      never hidden when linkage forces deviations — and the test-split tier
      distribution.
    - ``retrieval``: recall@{1,3,5,10} + MRR over test-split Tier A/B
      positives for the learned retrieval head, retrieval + reranker, and
      the deterministic baseline ranking the SAME anchors.
    - ``naturalness``: mean naturalness-head score on consensus-natural vs
      not-natural test anchors, plus the pairwise AUC.
    - ``recovery``: matched-budget recovery of test-split positives with
      existing links hidden (see :func:`_eval_recovery`).
    - ``corpus``: both engines over the full corpus (links visible) at their
      configured thresholds — accepted counts, accepted-set overlap at the
      (span, target) and (source, target) levels, top proposals, and an
      accepted-count threshold sweep.

    ``encoder_factory`` must produce the encoder the heads were trained on
    (fingerprint-verified). ``baseline_accept_threshold`` lets the baseline
    engine run at its own operating point (default: the learned threshold).
    The function trains nothing and never touches the labels' train split
    except through the split bookkeeping.
    """
    sample = load_audit_sample(Path(sample_path))
    labels = load_audit_labels(Path(labels_path))
    if not labels:
        raise ContractError(f"no audit labels found at {labels_path}; annotate the sample first")
    encoder = (
        encoder_factory() if encoder_factory is not None else HashingTokenEncoder(heads.hidden_size)
    )
    if encoder.fingerprint != heads.encoder_fingerprint:
        raise ContractError(
            f"evaluate_inline_engines: encoder fingerprint {encoder.fingerprint!r} does not "
            f"match the heads' training encoder {heads.encoder_fingerprint!r}; evaluate with "
            "the encoder the heads were trained on"
        )
    resolved_selection = selection_config if selection_config is not None else SelectionConfig()
    resolved_baseline_selection = (
        replace(resolved_selection, accept_threshold=baseline_accept_threshold)
        if baseline_accept_threshold is not None
        else resolved_selection
    )
    dictionary = _prepared_dictionary(inputs.corpus, anchor_config or AnchorConfig())
    documents = _documents_by_id(inputs)
    doc_encoder = _DocumentEncoder(encoder, cache=token_state_cache)
    catalog = _target_catalog(inputs, encoder, cache=token_state_cache)

    labeled_ids, tiers, natural = _consensus_by_item(labels, sample)
    items_by_id = {item.id: item for item in sample.items}
    triples = [
        (
            items_by_id[item_id].source_document_id,
            items_by_id[item_id].anchor_text,
            items_by_id[item_id].target_document_id,
        )
        for item_id in labeled_ids
    ]
    split = three_way_split(
        triples, seed=seed, test_fraction=test_fraction, val_fraction=val_fraction
    )
    test_ids = [labeled_ids[index] for index in split.indices_for("test")]
    test_items = _eval_test_items(sample, test_ids, documents, dictionary, doc_encoder)
    positives = [entry for entry in test_items if tiers.get(entry.item.id) in _POSITIVE_TIERS]

    context = _EngineContext(
        inputs=inputs,
        heads=heads,
        dictionary=dictionary,
        documents=documents,
        doc_encoder=doc_encoder,
        catalog=catalog,
        span_config=span_config or SpanConfig(),
        selection_config=resolved_selection,
        baseline_config=baseline_config or BaselineConfig(),
        baseline_selection=resolved_baseline_selection,
    )
    titles = _titles(inputs)
    tier_counts = Counter(tiers[item_id].value for item_id in test_ids)
    result: dict[str, Any] = {
        "encoder_fingerprint": encoder.fingerprint,
        "model_version": heads.model_version,
        "split": {
            "seed": seed,
            "requested": {"test": test_fraction, "val": val_fraction},
            "achieved_fractions": dict(split.achieved_fractions),
            "group_count": split.group_count,
            "counts": {name: len(split.indices_for(name)) for name in ("train", "val", "test")},
            "test_tier_counts": dict(sorted(tier_counts.items())),
            "test_positives": len(positives),
        },
        "retrieval": _eval_retrieval(
            positives, heads, catalog, dictionary, titles, context.baseline_config
        ),
        "naturalness": _eval_naturalness(test_items, natural, heads),
        "recovery": _eval_recovery(context, positives),
        "corpus": _eval_corpus(context, sweep_thresholds, top_n),
    }
    return result
