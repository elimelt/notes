"""Round-trip serialization tests for every contract type.

Each contract must survive ``to_dict -> json -> from_dict`` unchanged,
including nested types, and its serialized form must be canonical-JSON-safe.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest

from linkdiscovery.fingerprint import canonical_json
from tests.conftest import (
    make_artifact_ref,
    make_candidate_set,
    make_corpus,
    make_embedding_index,
    make_embedding_record,
    make_header,
    make_processed_corpus,
    make_proposal,
    make_proposal_set,
    make_region,
    make_relationship,
    make_report_manifest,
    make_review_history,
    make_run_manifest,
    make_runtime_report,
    make_semantic_unit,
)

CASES: list[tuple[str, Callable[[], Any]]] = [
    ("ArtifactHeader", make_header),
    ("SourceDocument", lambda: make_corpus().documents[0]),
    ("DocumentFlags", lambda: make_corpus().documents[0].flags),
    ("Relationship", make_relationship),
    ("RelationshipSet", lambda: make_corpus().relationships),
    ("Corpus", make_corpus),
    ("Span", lambda: make_relationship().source_span),
    ("Region", make_region),
    ("SemanticUnit", make_semantic_unit),
    ("ProcessedDocument", lambda: make_processed_corpus().documents[0]),
    ("ProcessedCorpus", make_processed_corpus),
    ("EmbeddingRecord", make_embedding_record),
    ("RuntimeReport", make_runtime_report),
    ("EmbeddingIndex", make_embedding_index),
    ("UnitMatch", lambda: make_candidate_set().pairs[0].matches[0]),
    ("CandidatePair", lambda: make_candidate_set().pairs[0]),
    ("CandidateSet", make_candidate_set),
    ("Evidence", lambda: make_proposal().evidence[0]),
    ("ReviewState", lambda: make_proposal().review),
    ("LinkProposal", make_proposal),
    ("ProposalSet", make_proposal_set),
    ("ReviewDecision", lambda: make_review_history().decisions[1]),
    ("ReviewHistory", make_review_history),
    ("ArtifactRef", make_artifact_ref),
    ("StageStats", lambda: make_run_manifest().stages[0]),
    ("RunManifest", make_run_manifest),
    ("ReportManifest", make_report_manifest),
]


@pytest.mark.parametrize(("name", "factory"), CASES, ids=[name for name, _ in CASES])
def test_round_trip(name: str, factory: Callable[[], Any]) -> None:
    original = factory()
    serialized = original.to_dict()
    # The serialized form must be JSON-safe and survive a real JSON round trip.
    reloaded_data = json.loads(json.dumps(serialized))
    restored = type(original).from_dict(reloaded_data)
    assert restored == original
    assert restored.to_dict() == serialized


@pytest.mark.parametrize(("name", "factory"), CASES, ids=[name for name, _ in CASES])
def test_serialized_form_is_canonical_json_safe(name: str, factory: Callable[[], Any]) -> None:
    canonical_json(factory().to_dict())


def test_proposal_matches_spec_json_shape() -> None:
    """LinkProposal field names must match the SPEC 'LinkProposal' example exactly."""
    data = make_proposal().to_dict()
    assert set(data) == {
        "id",
        "source_document_id",
        "target_document_id",
        "direction",
        "rank",
        "score",
        "confidence",
        "features",
        "evidence",
        "existing_relationship",
        "ranking_version",
        "review",
    }
    assert data["review"] == {"status": "unreviewed", "reason": None}
    assert set(data["evidence"][0]) == {
        "source_unit_id",
        "target_unit_id",
        "similarity",
        "source_spans",
        "target_spans",
    }


def test_source_document_matches_spec_json_shape() -> None:
    data = make_corpus().documents[0].to_dict()
    assert set(data) == {
        "id",
        "revision",
        "media_type",
        "content",
        "title",
        "language",
        "source_ref",
        "metadata",
        "flags",
    }
    assert set(data["flags"]) == {"excluded", "generated", "archived"}


def test_semantic_unit_matches_spec_json_shape() -> None:
    data = make_semantic_unit().to_dict()
    assert set(data) == {
        "id",
        "document_id",
        "view",
        "section_path",
        "region_kinds",
        "source_spans",
        "text",
        "token_count",
        "content_hash",
    }
    assert data["source_spans"] == [{"start": 420, "end": 1080}]


def test_embedding_record_matches_spec_json_shape() -> None:
    data = make_embedding_record().to_dict()
    assert set(data) == {
        "unit_id",
        "model_fingerprint",
        "dimensions",
        "normalized",
        "dtype",
        "vector_ref",
    }


def test_relationship_matches_spec_json_shape() -> None:
    data = make_relationship().to_dict()
    assert set(data) == {
        "source_id",
        "target_id",
        "kind",
        "directed",
        "source_span",
        "metadata",
    }
    assert data["source_span"] == {"start": 120, "end": 148}
