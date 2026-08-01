"""Shared fixtures and sample-contract factories for the foundation tests.

Factories build small but fully populated contract instances so round-trip
and validation tests exercise every field, including nested types.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from linkdiscovery.artifacts import ArtifactCache, ArtifactStore
from linkdiscovery.contracts import (
    ArtifactHeader,
    ArtifactRef,
    CandidatePair,
    CandidateSet,
    Confidence,
    Corpus,
    DecisionKind,
    DocumentFlags,
    EmbeddingIndex,
    EmbeddingRecord,
    Evidence,
    LinkProposal,
    ProcessedCorpus,
    ProcessedDocument,
    ProposalSet,
    ReasonCode,
    Region,
    RegionKind,
    Relationship,
    RelationshipSet,
    ReportManifest,
    ReviewDecision,
    ReviewHistory,
    ReviewState,
    RunManifest,
    RuntimeReport,
    SemanticUnit,
    SourceDocument,
    Span,
    StageStats,
    UnitMatch,
)


@pytest.fixture
def store(tmp_path: Path) -> ArtifactStore:
    """A fresh artifact store rooted in a temporary directory."""
    return ArtifactStore(tmp_path / "artifacts")


@pytest.fixture
def cache(store: ArtifactStore) -> ArtifactCache:
    """A fresh cache over the temporary store."""
    return ArtifactCache(store)


def make_header(**overrides: object) -> ArtifactHeader:
    """A fully populated artifact header; keyword overrides replace fields."""
    values: dict[str, object] = {
        "schema_version": 1,
        "run_id": "run-0001",
        "corpus_id": "corpus-alpha",
        "created_at": "2026-07-31T12:00:00+00:00",
        "config_fingerprint": "sha256:cfg",
        "producer_version": "linkdiscovery-0.1.0",
    }
    values.update(overrides)
    return ArtifactHeader(**values)  # type: ignore[arg-type]


def make_source_document(doc_id: str = "doc-a") -> SourceDocument:
    """A source document with every field populated."""
    return SourceDocument(
        id=doc_id,
        revision="rev-1",
        media_type="text/markdown",
        content="# Title\n\nSome prose about scheduling fairness.",
        title="Canonical title",
        language="en",
        source_ref=f"adapter://{doc_id}",
        metadata={"tags": ["systems", "scheduling"], "words": 7},
        flags=DocumentFlags(excluded=False, generated=False, archived=True),
    )


def make_relationship() -> Relationship:
    """A directed relationship with a source span and metadata."""
    return Relationship(
        source_id="doc-a",
        target_id="doc-b",
        kind="explicit-link",
        directed=True,
        source_span=Span(start=120, end=148),
        metadata={"anchor": "fairness"},
    )


def make_corpus() -> Corpus:
    """A corpus artifact with two documents and one relationship."""
    return Corpus(
        header=make_header(),
        documents=(make_source_document("doc-a"), make_source_document("doc-b")),
        relationships=RelationshipSet(relationships=(make_relationship(),)),
    )


def make_semantic_unit(doc_id: str = "doc-a", unit_id: str | None = None) -> SemanticUnit:
    """A semantic unit matching the SPEC JSON example shape."""
    return SemanticUnit(
        id=unit_id or f"{doc_id}:section-3:chunk-1",
        document_id=doc_id,
        view="section",
        section_path=("Scheduling", "Fairness"),
        region_kinds=(RegionKind.HEADING, RegionKind.PROSE, RegionKind.EQUATION),
        source_spans=(Span(start=420, end=1080),),
        text="text presented to the embedding model",
        token_count=173,
        content_hash="sha256:unitcontent",
    )


def make_region() -> Region:
    """A typed region with metadata."""
    return Region(
        kind=RegionKind.HEADING,
        span=Span(start=0, end=7),
        text="# Title",
        metadata={"level": 1},
    )


def make_processed_corpus() -> ProcessedCorpus:
    """A processed corpus with one document, one region, and one unit."""
    return ProcessedCorpus(
        header=make_header(),
        preprocessing_fingerprint="sha256:preproc",
        documents=(
            ProcessedDocument(
                document_id="doc-a",
                revision="rev-1",
                regions=(make_region(),),
                units=(make_semantic_unit("doc-a"),),
            ),
        ),
    )


def make_runtime_report() -> RuntimeReport:
    """A runtime report with a fallback event and truncation stats."""
    return RuntimeReport(
        device="mps",
        effective_batch_size=16,
        requested_batch_size="auto",
        fallback_events=("mps->cpu: unsupported operation in warmup",),
        truncation_count=2,
        failed_unit_ids=("doc-z:section-0:chunk-0",),
        warnings=("1 unit skipped",),
        wall_time_seconds=12.5,
        token_throughput=5400.0,
        peak_memory_bytes=2_147_483_648,
    )


def make_embedding_record(unit_id: str = "doc-a:section-3:chunk-1") -> EmbeddingRecord:
    """An embedding record matching the SPEC JSON example shape."""
    return EmbeddingRecord(
        unit_id=unit_id,
        model_fingerprint="sha256:model",
        dimensions=4096,
        normalized=True,
        dtype="float16",
        vector_ref="embeddings/vectors-0001",
    )


def make_embedding_index() -> EmbeddingIndex:
    """An embedding index with two consistent records and a runtime report."""
    return EmbeddingIndex(
        header=make_header(),
        model_fingerprint="sha256:model",
        dimensions=4096,
        normalized=True,
        dtype="float16",
        runtime=make_runtime_report(),
        records=(
            make_embedding_record("doc-a:section-3:chunk-1"),
            make_embedding_record("doc-b:section-1:chunk-0"),
        ),
    )


def make_candidate_set() -> CandidateSet:
    """A candidate set with one pair carrying unit matches and features."""
    return CandidateSet(
        header=make_header(),
        pairs=(
            CandidatePair(
                source_document_id="doc-a",
                target_document_id="doc-b",
                matches=(
                    UnitMatch(
                        source_unit_id="doc-a:section-3:chunk-1",
                        target_unit_id="doc-b:section-1:chunk-0",
                        view="section",
                        similarity=0.93,
                    ),
                ),
                features={"document_similarity": 0.84, "chunk_count_ratio": 1.5},
            ),
        ),
    )


def make_proposal(proposal_id: str = "doc-a--doc-b--rank-v1") -> LinkProposal:
    """A link proposal matching the SPEC JSON example shape."""
    return LinkProposal(
        id=proposal_id,
        source_document_id="doc-a",
        target_document_id="doc-b",
        direction="source-to-target",
        rank=1,
        score=0.91,
        confidence=Confidence.HIGH,
        features={
            "document_similarity": 0.84,
            "best_chunk_similarity": 0.93,
            "support_breadth": 0.71,
            "lexical_similarity": 0.24,
            "hubness_penalty": 0.05,
            "graph_redundancy_penalty": 0.0,
        },
        evidence=(
            Evidence(
                source_unit_id="doc-a:section-3:chunk-1",
                target_unit_id="doc-b:section-1:chunk-0",
                similarity=0.93,
                source_spans=(Span(start=420, end=1080),),
                target_spans=(Span(start=80, end=510),),
            ),
        ),
        existing_relationship=False,
        ranking_version="sha256:ranker",
        review=ReviewState(status="unreviewed", reason=None),
    )


def make_proposal_set() -> ProposalSet:
    """A proposal set with one fully populated proposal."""
    return ProposalSet(header=make_header(), proposals=(make_proposal(),))


def make_review_history() -> ReviewHistory:
    """A review history with an accept and a reject-with-reason decision."""
    return ReviewHistory(
        header=make_header(),
        decisions=(
            ReviewDecision(
                proposal_id="doc-a--doc-b--rank-v1",
                decision=DecisionKind.ACCEPT,
                reason=None,
                note="clear conceptual dependency",
                reviewer="elijah",
                decided_at="2026-07-31T13:00:00+00:00",
            ),
            ReviewDecision(
                proposal_id="doc-a--doc-c--rank-v1",
                decision=DecisionKind.REJECT,
                reason=ReasonCode.TOO_GENERIC,
            ),
        ),
    )


def make_artifact_ref() -> ArtifactRef:
    """An artifact reference into the proposals group."""
    return ArtifactRef(
        group="proposals",
        key="sha256:abc123",
        path="proposals/sha256:abc123",
        fingerprint="sha256:abc123",
        size=2048,
    )


def make_run_manifest() -> RunManifest:
    """A run manifest with config, stage stats, artifacts, seeds, environment."""
    return RunManifest(
        header=make_header(),
        resolved_config={"schema_version": 1, "ranking": {"profile": "weighted-v1"}},
        stages=(
            StageStats(
                stage="embedding",
                wall_time_seconds=12.5,
                cache_hits=90,
                cache_misses=10,
                input_count=100,
                output_count=100,
                warnings=("1 unit truncated",),
                counters={"vectors": 100, "truncated": 1},
            ),
        ),
        artifacts=(make_artifact_ref(),),
        seeds={"hnsw": 42},
        environment={"python": "3.12", "platform": "darwin"},
    )


def make_report_manifest() -> ReportManifest:
    """A report manifest referencing one rendered output."""
    return ReportManifest(
        header=make_header(),
        formats=("jsonl", "markdown"),
        outputs=(make_artifact_ref(),),
    )
