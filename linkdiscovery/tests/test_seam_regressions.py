"""Cross-stage regression tests from the adversarial integration review.

Each test pins a defect found at a seam between independently built stages:

1. Alias classes whose canonical (lexicographically smallest) member is not a
   processed document produced candidate pairs the ranker silently dropped.
2. The corpus fingerprint ignored eligibility flags, so runs differing only in
   adapter flag policy collided on processed-corpus/embeddings artifact keys.
3. The proposals artifact key ignored review feedback, so runs with different
   review histories stored different payloads under the same key.
4. Self-relationships (a document linking to itself) counted as held-out
   recovery targets that can never be recovered, deflating recall metrics.
5. The generator discarded the hnsw construction parameters instead of
   surfacing them for the run manifest (SPEC: index parameters are recorded).
6. ``ranking.top_r_sections`` was accepted and fingerprinted but never read
   by any stage (the top-r constant lives in the candidate generator); a
   silently ignored field violates the strict-configuration contract.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from linkdiscovery.candidates import DefaultCandidateGenerator
from linkdiscovery.config import CandidateConfig, RankingConfig, config_from_dict
from linkdiscovery.contracts.base import ArtifactHeader
from linkdiscovery.contracts.documents import (
    Corpus,
    DocumentFlags,
    Relationship,
    RelationshipSet,
    SourceDocument,
)
from linkdiscovery.contracts.proposals import ProposalSet
from linkdiscovery.contracts.reviews import DecisionKind, ReviewDecision, ReviewHistory
from linkdiscovery.errors import ConfigError
from linkdiscovery.evaluate import recovery_metrics
from linkdiscovery.pipeline import Pipeline, _corpus_fingerprint
from linkdiscovery.ranking import WeightedRanker
from linkdiscovery.report import save_review_history
from tests.test_candidates_generator import UnitSpec, build_inputs, fixture_header, rel
from tests.test_pipeline_run import make_config

if TYPE_CHECKING:
    from pathlib import Path

    from linkdiscovery.artifacts import ArtifactStore
    from linkdiscovery.contracts.manifests import RunManifest


def _empty_proposals() -> ProposalSet:
    return ProposalSet(header=fixture_header(), proposals=())


# --------------------------------------------------------------- 1. aliases


def test_alias_pair_with_absent_canonical_survives_ranking(store: ArtifactStore) -> None:
    """A pair whose alias class canonicalizes to an absent document must rank.

    ``doc-zz`` is aliased to ``doc-aa`` (a redirect stub that never reached
    the processed corpus). The generator must canonicalize onto a document the
    downstream stages can resolve, or the ranker's corpus lookups silently
    drop every pair the alias class touches.
    """
    specs = [
        UnitSpec("doc-zz", "section", (1.0, 0.0, 0.0, 0.0), "alpha subsystem deep dive"),
        UnitSpec("doc-mm", "section", (0.95, 0.31, 0.0, 0.0), "alpha subsystem internals"),
    ]
    corpus, index = build_inputs(store, specs)
    relationships = RelationshipSet((rel("doc-zz", "doc-aa", "alias"),))
    generator = DefaultCandidateGenerator(store, run_id="run-test")
    candidates = generator.generate(corpus, index, relationships, CandidateConfig())
    assert len(candidates.pairs) == 1
    pair = candidates.pairs[0]
    # Both endpoints must be resolvable documents of the processed corpus.
    corpus_ids = {document.document_id for document in corpus.documents}
    assert {pair.source_document_id, pair.target_document_id} <= corpus_ids
    proposals = WeightedRanker(corpus, run_id="run-test").rank(candidates, RankingConfig(), None)
    assert len(proposals.proposals) == 1


def test_alias_canonical_prefers_smallest_present_member(store: ArtifactStore) -> None:
    """Among alias members present in the corpus, the smallest ID still wins."""
    specs = [
        UnitSpec("doc-aa", "section", (0.99, 0.05, 0.0, 0.0), "alpha canonical text"),
        UnitSpec("doc-zz", "section", (1.0, 0.0, 0.0, 0.0), "alpha stub text"),
        UnitSpec("doc-mm", "section", (0.95, 0.31, 0.0, 0.0), "alpha related text"),
    ]
    corpus, index = build_inputs(store, specs)
    relationships = RelationshipSet((rel("doc-zz", "doc-aa", "alias"),))
    generator = DefaultCandidateGenerator(store, run_id="run-test")
    candidates = generator.generate(corpus, index, relationships, CandidateConfig())
    assert [(pair.source_document_id, pair.target_document_id) for pair in candidates.pairs] == [
        ("doc-aa", "doc-mm")
    ]


# ------------------------------------------------- 2. corpus fingerprint


def _corpus_with_flags(flags: DocumentFlags) -> Corpus:
    header = ArtifactHeader(
        schema_version=1,
        run_id="run-x",
        corpus_id="corpus-x",
        created_at="2026-07-31T00:00:00+00:00",
        config_fingerprint="sha256:cfg",
        producer_version="test/1",
    )
    document = SourceDocument(
        id="doc-a",
        revision="rev-1",
        media_type="text/plain",
        content="body",
        flags=flags,
    )
    return Corpus(header=header, documents=(document,))


def test_corpus_fingerprint_covers_eligibility_flags() -> None:
    """Flag-only changes must change the corpus fingerprint.

    Eligibility flags decide which documents reach the processed corpus, and
    the processed-corpus and embeddings artifact keys are derived from the
    corpus fingerprint — identical keys for different eligible sets would
    silently collide.
    """
    plain = _corpus_with_flags(DocumentFlags())
    archived = _corpus_with_flags(DocumentFlags(archived=True))
    assert _corpus_fingerprint(plain) != _corpus_fingerprint(archived)
    # Unchanged corpora still fingerprint identically.
    assert _corpus_fingerprint(plain) == _corpus_fingerprint(_corpus_with_flags(DocumentFlags()))


# ---------------------------------------------- 3. proposals artifact key


def _proposals_ref_key(manifest: RunManifest) -> str:
    keys = [ref.key for ref in manifest.artifacts if ref.group == "proposals"]
    assert len(keys) == 1
    return keys[0]


def test_review_feedback_changes_proposals_artifact_key(tmp_path: Path) -> None:
    """Runs with different review feedback must not share a proposals key.

    Review feedback changes the stored proposal payload (review states and
    calibration), so a content-addressed key that ignores it stores different
    payloads under one key across runs.
    """
    config = make_config()
    base = Pipeline().run(config, artifacts_root=tmp_path / "a", run_id="base")
    assert base.proposals.proposals
    top = base.proposals.proposals[0]
    history = ReviewHistory(
        header=replace(base.proposals.header, run_id="review"),
        decisions=(ReviewDecision(proposal_id=top.id, decision=DecisionKind.ACCEPT),),
    )
    reviews_path = tmp_path / "reviews.json"
    save_review_history(history, reviews_path)
    reviewed = Pipeline().run(
        config, artifacts_root=tmp_path / "b", reviews_path=reviews_path, run_id="reviewed"
    )
    assert reviewed.proposals.proposals[0].review.status == "accepted"
    assert _proposals_ref_key(base.manifest) != _proposals_ref_key(reviewed.manifest)


# -------------------------------------------------- 4. self-relationships


def test_recovery_metrics_ignore_self_relationships() -> None:
    """A document's link to itself is never a recoverable holdout target."""
    self_link = Relationship(source_id="doc-a", target_id="doc-a", kind="explicit-link")
    metrics = recovery_metrics(_empty_proposals(), RelationshipSet((self_link,)))
    assert metrics["holdout_count"] == 0.0
    real = Relationship(source_id="doc-a", target_id="doc-b", kind="explicit-link")
    metrics = recovery_metrics(_empty_proposals(), RelationshipSet((self_link, real)))
    assert metrics["holdout_count"] == 1.0


# ------------------------------------------------ 5. hnsw index parameters


def test_hnsw_index_parameters_recorded_in_manifest(tmp_path: Path) -> None:
    """The approximate backend's construction parameters reach the manifest."""
    pytest.importorskip("hnswlib")
    config = make_config(candidates={"backend": "hnsw"})
    result = Pipeline().run(config, artifacts_root=tmp_path / "artifacts", run_id="hnsw-run")
    recorded = result.manifest.environment.get("index_parameters", "")
    assert '"backend":"hnsw"' in recorded
    assert '"seed":42' in recorded


# ------------------------------------------- 6. dead configuration fields


def test_top_r_sections_is_rejected_not_silently_ignored() -> None:
    """A ranking field no stage reads must be a loud error, not a no-op knob."""
    data = {
        "schema_version": 1,
        "source": {"adapter": "pkg.mod:Adapter"},
        "preprocess": {"parser": "pkg.mod:Parser"},
        "embedding": {"model": "m", "revision": "r", "dimensions": 8},
        "ranking": {"top_r_sections": 5},
    }
    with pytest.raises(ConfigError, match="top_r_sections"):
        config_from_dict(data)
