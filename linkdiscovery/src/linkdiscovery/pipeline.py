"""Pipeline orchestration: run every stage end to end against one configuration.

:class:`Pipeline` composes the default stage implementations behind the SPEC's
public interfaces::

    adapter.load -> preprocess -> embed -> generate candidates -> rank -> report

and persists each stage output in an :class:`~linkdiscovery.artifacts.store.
ArtifactStore` under the SPEC's logical artifact groups (``corpus-manifest``,
``processed-corpus``, ``embeddings``, ``candidates``, ``proposals``, ``runs``).
Artifact keys are content-addressed along the invalidation chain: the
processed corpus is keyed by corpus + preprocessing fingerprints, embeddings
add the model fingerprint, candidates and proposals extend the chain with
their own stage-config fingerprints. The run manifest is written **last** —
under its payload fingerprint and under a ``run-<run_id>`` alias — so a run
whose manifest exists is complete; any stage failure propagates its typed
:class:`~linkdiscovery.errors.LinkDiscoveryError` and no manifest is written
(SPEC: a partial run cannot appear complete).

Policies owned by the orchestrator (not by any single stage):

- **Token counting.** Chunk token accounting must use the real model
  tokenizer (SPEC "Chunking": word-count approximations are not valid for
  reproducible model input). The ``sentence-transformers`` provider therefore
  gets a :class:`~linkdiscovery.preprocess.HuggingFaceTokenCounter` pinned to
  the configured model and revision; the ``hashing`` baseline provider counts
  whitespace tokens, so it gets the matching dependency-free
  :class:`~linkdiscovery.preprocess.SimpleTokenCounter`.
- **Eligibility.** Documents flagged ``generated`` or ``archived`` are marked
  ``excluded`` before preprocessing (SPEC "Phase 1": exclude archived,
  private, generated, and adapter-excluded documents). The processed corpus
  is the exclusion boundary the candidate generator relies on.
- **Report placement.** A relative ``report.output_dir`` is resolved against
  ``artifacts_root`` so one directory holds everything a run produced.
- **Seeds.** The v1 batch flow draws no random numbers (retrieval is exact
  and every stage is deterministic), so ``RunManifest.seeds`` is empty by
  construction. Evaluation records its holdout seed in its own artifact.
"""

from __future__ import annotations

import logging
import platform
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from linkdiscovery.artifacts.cache import ArtifactCache
from linkdiscovery.artifacts.store import ArtifactStore
from linkdiscovery.candidates import DefaultCandidateGenerator
from linkdiscovery.contracts.base import ArtifactHeader, utc_now_iso
from linkdiscovery.contracts.manifests import (
    SCHEMA_VERSION,
    ArtifactRef,
    RunManifest,
    StageStats,
)
from linkdiscovery.embed import DefaultEmbedder
from linkdiscovery.embed.vectors import VECTOR_GROUP, parse_vector_ref
from linkdiscovery.errors import ConfigError
from linkdiscovery.evaluate import recovery_by_degree, recovery_metrics, split_relationships
from linkdiscovery.fingerprint import (
    canonical_json,
    combine_fingerprints,
    fingerprint,
    fingerprint_bytes,
)
from linkdiscovery.interfaces import RegionParser, SourceAdapter, TokenCounter
from linkdiscovery.plugins import instantiate_plugin
from linkdiscovery.preprocess import (
    DefaultPreprocessor,
    HuggingFaceTokenCounter,
    SimpleTokenCounter,
)
from linkdiscovery.ranking import WeightedRanker
from linkdiscovery.report import DefaultReporter, apply_reviews, load_review_history

if TYPE_CHECKING:
    from collections.abc import Sequence

    from linkdiscovery.config import EmbeddingConfig, PipelineConfig
    from linkdiscovery.contracts.candidates import CandidateSet
    from linkdiscovery.contracts.documents import Corpus, RelationshipSet
    from linkdiscovery.contracts.embeddings import EmbeddingIndex
    from linkdiscovery.contracts.manifests import ReportManifest
    from linkdiscovery.contracts.proposals import ProposalSet
    from linkdiscovery.contracts.reviews import ReviewHistory
    from linkdiscovery.contracts.units import ProcessedCorpus

__all__ = ["PRODUCER_VERSION", "Pipeline", "RunResult"]

_LOGGER = logging.getLogger(__name__)

PRODUCER_VERSION = "linkdiscovery/0.1.0"
"""Producer version stamped into every artifact header this orchestrator writes."""


@dataclass(frozen=True, slots=True)
class RunResult:
    """Everything one completed run produced, plus where it lives on disk.

    ``manifest`` is the reproducibility record (written last, so holding a
    ``RunResult`` proves the run completed); ``proposals`` is the final
    proposal set with any review decisions applied; ``report`` references the
    rendered review files; ``artifacts_root`` is the store root and
    ``report_dir`` the resolved report output directory.
    """

    run_id: str
    manifest: RunManifest
    proposals: ProposalSet
    report: ReportManifest
    artifacts_root: Path
    report_dir: Path


@dataclass(frozen=True, slots=True)
class _RunContext:
    """Per-run wiring shared by the stage helpers.

    ``corpus_fp`` and ``relationship_fp`` are empty for evaluation runs,
    which skip artifact persistence and therefore never key on them.
    """

    config: PipelineConfig
    store: ArtifactStore
    run_id: str
    corpus_fp: str = ""
    relationship_fp: str = ""


@dataclass(frozen=True, slots=True)
class _Discovery:
    """Output of the shared discovery stages (preprocess, embed, candidates).

    ``stats`` carries one :class:`StageStats` per stage in execution order;
    ``refs`` the persisted artifacts and ``candidates_key`` the candidate
    set's content-addressed store key (both empty when persistence was
    skipped, as in evaluation runs).
    """

    processed: ProcessedCorpus
    index: EmbeddingIndex
    candidates: CandidateSet
    stats: tuple[StageStats, ...]
    refs: tuple[ArtifactRef, ...]
    candidates_key: str
    index_params: dict[str, dict[str, int | str]]
    """Approximate-index construction parameters per retrieval view (empty for
    exact search); recorded in the run manifest per the SPEC."""


def _derive_run_id(config: PipelineConfig, corpus_fingerprint: str) -> str:
    """Default run id: ``run-<compact UTC timestamp>-<8 hex of config+corpus>``.

    Unique and sortable by start time, and deterministic given the time: the
    suffix is the first eight hex digits of the combined configuration and
    corpus fingerprints, so two runs of the same inputs share a recognizable
    suffix. Tests override ``run_id`` for full determinism.
    """
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    digest = combine_fingerprints(config.fingerprint(), corpus_fingerprint)
    return f"run-{stamp}-{digest.partition(':')[2][:8]}"


def _select_token_counter(config: EmbeddingConfig) -> TokenCounter:
    """The token counter matching the configured embedding provider.

    Per the SPEC, chunk sizes are measured with the selected model's
    tokenizer: ``sentence-transformers`` uses the pinned Hugging Face
    tokenizer of ``config.model`` at ``config.revision``; the ``hashing``
    baseline truncates on whitespace tokens, so the dependency-free counter
    is its exact tokenizer. An unknown provider is a configuration error.
    """
    if config.provider == "sentence-transformers":
        return HuggingFaceTokenCounter(config.model, config.revision)
    if config.provider == "hashing":
        return SimpleTokenCounter()
    raise ConfigError(
        f"embedding: no token counter for provider {config.provider!r}; "
        "expected one of: 'hashing', 'sentence-transformers'"
    )


def _instantiate_plugins(config: PipelineConfig) -> tuple[SourceAdapter, RegionParser]:
    """Resolve and validate the adapter and parser plugin specs."""
    adapter: SourceAdapter = instantiate_plugin(config.source.adapter, SourceAdapter)
    parser: RegionParser = instantiate_plugin(config.preprocess.parser, RegionParser)
    return adapter, parser


def _corpus_fingerprint(corpus: Corpus) -> str:
    """Content fingerprint of the corpus: every document id, revision, and flags.

    Eligibility flags are included because they decide which documents reach
    the processed corpus: adapter options can change flags without changing
    any revision, and the processed-corpus/embeddings artifact keys derived
    from this fingerprint must not collide across different eligible sets.
    """
    return fingerprint([[doc.id, doc.revision, doc.flags.to_dict()] for doc in corpus.documents])


def _exclude_ineligible(corpus: Corpus) -> tuple[Corpus, int]:
    """Mark ``generated`` and ``archived`` documents ``excluded``.

    The SPEC's candidate phase excludes archived, private, generated, and
    adapter-excluded documents; the default generator relies on the processed
    corpus as the exclusion boundary, and the preprocessor skips exactly the
    ``excluded`` flag — so the orchestrator folds the other flags into it.
    Returns the (possibly unchanged) corpus and the number of newly flagged
    documents.
    """
    flagged = 0
    documents = []
    for document in corpus.documents:
        if (document.flags.generated or document.flags.archived) and not (document.flags.excluded):
            flagged += 1
            documents.append(replace(document, flags=replace(document.flags, excluded=True)))
        else:
            documents.append(document)
    if not flagged:
        return corpus, 0
    return replace(corpus, documents=tuple(documents)), flagged


def _corpus_manifest_payload(corpus: Corpus, run_id: str) -> dict[str, Any]:
    """The corpus-manifest artifact: documents without content, plus relationships.

    Full raw content stays out of the manifest (it can be sensitive and is
    already fingerprinted by each document's ``revision``); identity,
    eligibility flags, and the complete relationship set are what downstream
    stages and audits need.
    """
    header = replace(corpus.header, run_id=run_id)
    return {
        "header": header.to_dict(),
        "documents": [
            {
                "id": document.id,
                "revision": document.revision,
                "title": document.title,
                "source_ref": document.source_ref,
                "flags": document.flags.to_dict(),
            }
            for document in corpus.documents
        ],
        "relationships": corpus.relationships.to_dict(),
    }


def _source_stats(corpus: Corpus, auto_excluded: int, seconds: float) -> StageStats:
    """Observability for the source stage, including unresolved-target warnings.

    Adapters report unresolvable links as relationships whose kind names the
    condition (the Markdown adapter uses ``unresolved-link``); the SPEC
    requires unresolved relationship targets to be detected and reported, so
    they surface as run-manifest warnings rather than disappearing.
    """
    unresolved: dict[str, int] = {}
    for relationship in corpus.relationships.relationships:
        if "unresolved" in relationship.kind:
            unresolved[relationship.kind] = unresolved.get(relationship.kind, 0) + 1
    warnings = [
        f"{count} relationship(s) of kind {kind!r} reference unresolved targets"
        for kind, count in sorted(unresolved.items())
    ]
    if auto_excluded:
        warnings.append(
            f"{auto_excluded} generated/archived document(s) marked excluded before preprocessing"
        )
    return StageStats(
        stage="source",
        wall_time_seconds=seconds,
        input_count=len(corpus.documents),
        output_count=len(corpus.documents),
        warnings=tuple(warnings),
        counters={
            "documents": len(corpus.documents),
            "relationships": len(corpus.relationships.relationships),
            "excluded_by_adapter": sum(1 for doc in corpus.documents if doc.flags.excluded),
            "excluded_generated_or_archived": auto_excluded,
        },
    )


def _vector_table_refs(store: ArtifactStore, index: EmbeddingIndex) -> list[ArtifactRef]:
    """Refs for the vector table artifact(s) the embedder published.

    The table keys come from :func:`~linkdiscovery.embed.vectors.
    parse_vector_ref` — the one module allowed to interpret ``vector_ref`` —
    and each table's stored bytes are re-fingerprinted so the manifest can
    detect later corruption.
    """
    table_keys = sorted({parse_vector_ref(record.vector_ref)[0] for record in index.records})
    refs: list[ArtifactRef] = []
    for key in table_keys:
        data = store.get_bytes(VECTOR_GROUP, key)
        refs.append(
            ArtifactRef(
                group=VECTOR_GROUP,
                key=key,
                path=f"{VECTOR_GROUP}/{key}",
                fingerprint=fingerprint_bytes(data),
                size=len(data),
            )
        )
    return refs


class Pipeline:
    """The batch orchestrator: one call runs adapter through report.

    Stateless and reusable; every run gets fresh stage instances stamped with
    its ``run_id``. See the module docstring for the policies the
    orchestrator owns (token counting, eligibility, report placement, seeds)
    and for the artifact-key scheme.
    """

    def __init__(self, *, producer_version: str = PRODUCER_VERSION) -> None:
        """``producer_version`` is recorded in every artifact header and manifest."""
        self._producer_version = producer_version

    def run(
        self,
        config: PipelineConfig,
        *,
        artifacts_root: Path,
        reviews_path: Path | None = None,
        run_id: str | None = None,
    ) -> RunResult:
        """Execute a full batch run and return its complete outputs.

        Contract: every stage artifact is persisted as it is produced; the
        run manifest is written last, so its existence marks completion. Any
        stage failure propagates the stage's typed
        :class:`~linkdiscovery.errors.LinkDiscoveryError` and writes nothing
        further — in particular, no manifest. When ``reviews_path`` names a
        review history saved by
        :func:`~linkdiscovery.report.save_review_history`, its decisions
        feed ranker calibration and are projected onto the returned
        proposals. ``run_id`` defaults to a timestamped id (see
        :func:`_derive_run_id`); pass one explicitly for reproducible tests.
        """
        store = ArtifactStore(Path(artifacts_root))
        adapter, parser = _instantiate_plugins(config)

        stage_start = time.perf_counter()
        corpus = adapter.load(config.source)
        source_seconds = time.perf_counter() - stage_start
        corpus_fp = _corpus_fingerprint(corpus)
        relationship_fp = fingerprint(corpus.relationships.to_dict())
        if run_id is None:
            run_id = _derive_run_id(config, corpus_fp)
        _LOGGER.info(
            "run %s: loaded %d documents, %d relationships",
            run_id,
            len(corpus.documents),
            len(corpus.relationships.relationships),
        )
        refs: list[ArtifactRef] = []
        corpus_key = combine_fingerprints(corpus_fp, relationship_fp)
        refs.append(
            store.put_json("corpus-manifest", corpus_key, _corpus_manifest_payload(corpus, run_id))
        )
        effective_corpus, auto_excluded = _exclude_ineligible(corpus)
        stages: list[StageStats] = [_source_stats(corpus, auto_excluded, source_seconds)]

        context = _RunContext(
            config=config,
            store=store,
            run_id=run_id,
            corpus_fp=corpus_fp,
            relationship_fp=relationship_fp,
        )
        discovery = self._run_discovery(
            context, effective_corpus, corpus.relationships, parser, persist=True
        )
        stages.extend(discovery.stats)
        refs.extend(discovery.refs)

        history: ReviewHistory | None = None
        if reviews_path is not None:
            history = load_review_history(Path(reviews_path))
        proposals, rank_stats = self._rank(config, discovery, run_id, history=history)
        stages.append(rank_stats)
        # Review feedback changes the stored payload (review states and
        # calibration), so it must be part of the content-addressed key.
        proposals_key = combine_fingerprints(discovery.candidates_key, config.ranking.fingerprint())
        if history is not None:
            proposals_key = combine_fingerprints(proposals_key, fingerprint(history.to_dict()))
        refs.append(store.put_json("proposals", proposals_key, proposals.to_dict()))

        report, report_dir, report_stats = self._report(
            config, corpus, discovery.processed, proposals, Path(artifacts_root), run_id
        )
        stages.append(report_stats)
        refs.extend(report.outputs)

        manifest = self._publish_manifest(
            context, corpus, discovery, stages=tuple(stages), refs=tuple(refs)
        )
        return RunResult(
            run_id=run_id,
            manifest=manifest,
            proposals=proposals,
            report=report,
            artifacts_root=store.root,
            report_dir=report_dir,
        )

    def evaluate_holdout(
        self,
        config: PipelineConfig,
        *,
        artifacts_root: Path,
        holdout_fraction: float,
        seed: int,
        k_values: Sequence[int] = (1, 5, 10, 25),
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Measure held-out link recovery (SPEC "Weak supervision from existing links").

        Hides a stratified ``holdout_fraction`` of the relationships whose
        kind is in ``config.candidates.existing_relationship_kinds`` (using
        ``seed``), runs the discovery stages with only the visible set (so
        hidden links are eligible candidates again), ranks without feedback,
        and reports :func:`~linkdiscovery.evaluate.recovery_metrics` at each
        ``k`` plus :func:`~linkdiscovery.evaluate.recovery_by_degree`. No
        report is rendered and no run manifest is written; the metrics dict
        is returned and stored under ``runs/eval-<run_id>``. Raises
        :class:`~linkdiscovery.errors.ConfigError` unless
        ``0 < holdout_fraction < 1``.
        """
        if not 0.0 < holdout_fraction < 1.0:
            raise ConfigError(
                "evaluate: holdout_fraction must be in the open interval (0, 1), "
                f"got {holdout_fraction}"
            )
        store = ArtifactStore(Path(artifacts_root))
        adapter, parser = _instantiate_plugins(config)
        corpus = adapter.load(config.source)
        if run_id is None:
            run_id = _derive_run_id(config, _corpus_fingerprint(corpus))
        visible, held_out = split_relationships(
            corpus.relationships,
            holdout_fraction=holdout_fraction,
            seed=seed,
            kinds=config.candidates.existing_relationship_kinds,
        )
        _LOGGER.info(
            "eval %s: %d relationships visible, %d held out",
            run_id,
            len(visible.relationships),
            len(held_out.relationships),
        )
        eval_corpus, _ = _exclude_ineligible(replace(corpus, relationships=visible))
        context = _RunContext(config=config, store=store, run_id=run_id)
        discovery = self._run_discovery(context, eval_corpus, visible, parser, persist=False)
        ranker = WeightedRanker(
            discovery.processed, run_id=run_id, producer_version=self._producer_version
        )
        proposals = ranker.rank(discovery.candidates, config.ranking, None)
        metrics = recovery_metrics(proposals, held_out, k_values=tuple(k_values))
        result: dict[str, Any] = {
            "run_id": run_id,
            "holdout_fraction": holdout_fraction,
            "seed": seed,
            "k_values": list(k_values),
            "visible_count": len(visible.relationships),
            "proposal_count": len(proposals.proposals),
            **metrics,
            "recovery_by_degree": recovery_by_degree(proposals, held_out, visible),
        }
        store.put_json("runs", f"eval-{run_id}", result)
        return result

    # ------------------------------------------------------------- stages

    def _run_discovery(
        self,
        context: _RunContext,
        corpus: Corpus,
        relationships: RelationshipSet,
        parser: RegionParser,
        *,
        persist: bool,
    ) -> _Discovery:
        """Preprocess, embed, and generate candidates for ``corpus``.

        ``relationships`` is the set the candidate generator excludes and
        signals from (a holdout evaluation passes the visible subset).
        When ``persist`` is true the processed corpus, embedding index, and
        candidate set are stored under their content-addressed keys.
        """
        config, store, run_id = context.config, context.store, context.run_id
        stage_start = time.perf_counter()
        token_counter = _select_token_counter(config.embedding)
        preprocessor = DefaultPreprocessor(
            parser, token_counter, run_id=run_id, producer_version=self._producer_version
        )
        processed = preprocessor.process(corpus, config.preprocess)
        preprocess_seconds = time.perf_counter() - stage_start
        unit_count = sum(len(document.units) for document in processed.documents)
        preprocess_warnings: tuple[str, ...] = ()
        if preprocessor.skipped_excluded_count:
            preprocess_warnings = (
                f"{preprocessor.skipped_excluded_count} excluded document(s) skipped "
                "(adapter flags plus generated/archived policy)",
            )
        preprocess_stats = StageStats(
            stage="preprocess",
            wall_time_seconds=preprocess_seconds,
            input_count=len(corpus.documents),
            output_count=unit_count,
            warnings=preprocess_warnings,
            counters={
                "documents": len(processed.documents),
                "regions": sum(len(document.regions) for document in processed.documents),
                "units": unit_count,
                "skipped_excluded": preprocessor.skipped_excluded_count,
            },
        )
        _LOGGER.info("run %s: preprocessed %d units", run_id, unit_count)

        stage_start = time.perf_counter()
        cache = ArtifactCache(store)
        embedder = DefaultEmbedder(store, run_id=run_id, producer_version=self._producer_version)
        index = embedder.embed(processed, config.embedding, cache)
        embed_seconds = time.perf_counter() - stage_start
        cache_stats = cache.stats()
        embed_stats = StageStats(
            stage="embed",
            wall_time_seconds=embed_seconds,
            cache_hits=cache_stats.hits,
            cache_misses=cache_stats.misses,
            input_count=unit_count,
            output_count=len(index.records),
            warnings=index.runtime.fallback_events + index.runtime.warnings,
            counters={
                "vectors": len(index.records),
                "truncated_units": index.runtime.truncation_count,
                "failed_units": len(index.runtime.failed_unit_ids),
                "effective_batch_size": index.runtime.effective_batch_size,
            },
        )
        _LOGGER.info(
            "run %s: embedded %d vectors on %s (%d cache hits, %d misses)",
            run_id,
            len(index.records),
            index.runtime.device,
            cache_stats.hits,
            cache_stats.misses,
        )

        stage_start = time.perf_counter()
        generator = DefaultCandidateGenerator(
            store, run_id=run_id, producer_version=self._producer_version
        )
        candidates = generator.generate(processed, index, relationships, config.candidates)
        candidate_stats = StageStats(
            stage="candidates",
            wall_time_seconds=time.perf_counter() - stage_start,
            input_count=len(index.records),
            output_count=len(candidates.pairs),
            counters={"pairs": len(candidates.pairs)},
        )
        _LOGGER.info("run %s: %d candidate pairs", run_id, len(candidates.pairs))

        refs: list[ArtifactRef] = []
        candidates_key = ""
        if persist:
            processed_key = combine_fingerprints(
                context.corpus_fp, processed.preprocessing_fingerprint
            )
            refs.append(store.put_json("processed-corpus", processed_key, processed.to_dict()))
            embeddings_key = combine_fingerprints(
                context.corpus_fp, processed.preprocessing_fingerprint, index.model_fingerprint
            )
            refs.append(store.put_json("embeddings", embeddings_key, index.to_dict()))
            refs.extend(_vector_table_refs(store, index))
            candidates_key = combine_fingerprints(embeddings_key, config.candidates.fingerprint())
            refs.append(store.put_json("candidates", candidates_key, candidates.to_dict()))
        return _Discovery(
            processed=processed,
            index=index,
            candidates=candidates,
            stats=(preprocess_stats, embed_stats, candidate_stats),
            refs=tuple(refs),
            candidates_key=candidates_key,
            index_params=dict(generator.last_index_params),
        )

    def _rank(
        self,
        config: PipelineConfig,
        discovery: _Discovery,
        run_id: str,
        *,
        history: ReviewHistory | None,
    ) -> tuple[ProposalSet, StageStats]:
        """Rank candidates with optional durable review feedback applied."""
        stage_start = time.perf_counter()
        ranker = WeightedRanker(
            discovery.processed, run_id=run_id, producer_version=self._producer_version
        )
        proposals = ranker.rank(discovery.candidates, config.ranking, history)
        if history is not None:
            proposals = apply_reviews(proposals, history)
        reviewed = sum(1 for p in proposals.proposals if p.review.status != "unreviewed")
        stats = StageStats(
            stage="rank",
            wall_time_seconds=time.perf_counter() - stage_start,
            input_count=len(discovery.candidates.pairs),
            output_count=len(proposals.proposals),
            counters={
                "proposals": len(proposals.proposals),
                "reviewed": reviewed,
                "review_decisions": len(history.decisions) if history else 0,
            },
        )
        _LOGGER.info("run %s: %d proposals", run_id, len(proposals.proposals))
        return proposals, stats

    def _report(
        self,
        config: PipelineConfig,
        corpus: Corpus,
        processed: ProcessedCorpus,
        proposals: ProposalSet,
        artifacts_root: Path,
        run_id: str,
    ) -> tuple[ReportManifest, Path, StageStats]:
        """Render review reports; a relative output dir lands under the store root."""
        stage_start = time.perf_counter()
        report_dir = Path(config.report.output_dir)
        if not report_dir.is_absolute():
            report_dir = artifacts_root / report_dir
        report_config = replace(config.report, output_dir=str(report_dir))
        reporter = DefaultReporter(
            corpus, processed, run_id=run_id, producer_version=self._producer_version
        )
        report = reporter.write(proposals, report_config)
        stats = StageStats(
            stage="report",
            wall_time_seconds=time.perf_counter() - stage_start,
            input_count=len(proposals.proposals),
            output_count=len(report.outputs),
            counters={"outputs": len(report.outputs)},
        )
        _LOGGER.info("run %s: reports written to %s", run_id, report_dir)
        return report, report_dir, stats

    def _publish_manifest(
        self,
        context: _RunContext,
        corpus: Corpus,
        discovery: _Discovery,
        *,
        stages: tuple[StageStats, ...],
        refs: tuple[ArtifactRef, ...],
    ) -> RunManifest:
        """Assemble and atomically publish the run manifest — the final write."""
        config, store, run_id = context.config, context.store, context.run_id
        environment = {
            "linkdiscovery": PRODUCER_VERSION.partition("/")[2],
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "device": discovery.index.runtime.device,
            "corpus_fingerprint": context.corpus_fp,
            "relationship_fingerprint": context.relationship_fp,
            "model_fingerprint": discovery.index.model_fingerprint,
            "preprocessing_fingerprint": discovery.processed.preprocessing_fingerprint,
        }
        if discovery.index_params:
            # SPEC "Reproducibility and observability": approximate-index
            # construction parameters are recorded in the run manifest.
            environment["index_parameters"] = canonical_json(
                {view: dict(params) for view, params in sorted(discovery.index_params.items())}
            )
        manifest = RunManifest(
            header=ArtifactHeader(
                schema_version=SCHEMA_VERSION,
                run_id=run_id,
                corpus_id=corpus.header.corpus_id,
                created_at=utc_now_iso(),
                config_fingerprint=config.fingerprint(),
                producer_version=self._producer_version,
            ),
            resolved_config=config.resolved_dict(),
            stages=stages,
            artifacts=refs,
            seeds={},  # the v1 batch flow is fully deterministic; no RNG is used
            environment=environment,
        )
        payload = manifest.to_dict()
        store.put_json("runs", fingerprint(payload), payload)
        alias_key = run_id if run_id.startswith("run-") else f"run-{run_id}"
        store.put_json("runs", alias_key, payload)
        _LOGGER.info("run %s: manifest published under runs/%s", run_id, alias_key)
        return manifest
