"""Validation tests for contract construction and deserialization."""

from __future__ import annotations

from typing import Any

import pytest

from linkdiscovery.contracts import (
    ArtifactHeader,
    ArtifactRef,
    CandidatePair,
    Corpus,
    EmbeddingIndex,
    LinkProposal,
    ProcessedDocument,
    ProposalSet,
    RegionKind,
    ReviewDecision,
    ReviewState,
    RuntimeReport,
    SemanticUnit,
    Span,
)
from linkdiscovery.errors import ContractError
from tests.conftest import (
    make_corpus,
    make_embedding_index,
    make_embedding_record,
    make_header,
    make_proposal,
    make_proposal_set,
    make_semantic_unit,
    make_source_document,
)


class TestArtifactHeader:
    def test_missing_field_raises_with_field_name(self) -> None:
        data = make_header().to_dict()
        del data["corpus_id"]
        with pytest.raises(ContractError, match="missing required field 'corpus_id'"):
            ArtifactHeader.from_dict(data)

    def test_wrong_type_raises_with_field_name(self) -> None:
        data = make_header().to_dict()
        data["run_id"] = 7
        with pytest.raises(ContractError, match="'run_id' must be a string"):
            ArtifactHeader.from_dict(data)

    def test_non_object_input_raises(self) -> None:
        with pytest.raises(ContractError, match="expected a JSON object"):
            ArtifactHeader.from_dict(["not", "an", "object"])  # type: ignore[arg-type]


class TestSchemaVersion:
    @pytest.mark.parametrize(
        "artifact",
        [make_corpus(), make_embedding_index(), make_proposal_set()],
        ids=lambda artifact: type(artifact).__name__,
    )
    def test_unknown_schema_version_rejected(self, artifact: Any) -> None:
        data = artifact.to_dict()
        data["header"]["schema_version"] = 99
        with pytest.raises(ContractError, match="unknown schema_version 99"):
            type(artifact).from_dict(data)


class TestSpan:
    def test_negative_start_rejected(self) -> None:
        with pytest.raises(ContractError, match="start must be >= 0"):
            Span(start=-1, end=4)

    def test_end_before_start_rejected(self) -> None:
        with pytest.raises(ContractError, match="invalid range"):
            Span(start=10, end=3)

    def test_empty_span_allowed(self) -> None:
        assert Span(start=5, end=5).to_dict() == {"start": 5, "end": 5}


class TestRegions:
    def test_unknown_region_kind_rejected_on_deserialization(self) -> None:
        data = make_semantic_unit().to_dict()
        data["region_kinds"] = ["prose", "hologram"]
        with pytest.raises(ContractError, match="unknown region kind 'hologram'"):
            SemanticUnit.from_dict(data)

    def test_region_kind_is_str_enum(self) -> None:
        assert RegionKind.PROSE == "prose"
        assert RegionKind("other") is RegionKind.OTHER


class TestSemanticUnit:
    def test_negative_token_count_rejected(self) -> None:
        with pytest.raises(ContractError, match="token_count must be >= 0"):
            SemanticUnit(
                id="u",
                document_id="d",
                view="section",
                section_path=(),
                region_kinds=(),
                source_spans=(),
                text="",
                token_count=-1,
                content_hash="sha256:x",
            )


class TestCorpus:
    def test_duplicate_document_ids_rejected(self) -> None:
        with pytest.raises(ContractError, match="duplicate document id 'doc-a'"):
            Corpus(
                header=make_header(),
                documents=(make_source_document("doc-a"), make_source_document("doc-a")),
            )

    def test_missing_flags_default_to_false(self) -> None:
        data = make_source_document().to_dict()
        del data["flags"]
        document = type(make_source_document()).from_dict(data)
        assert not document.flags.excluded
        assert not document.flags.generated
        assert not document.flags.archived


class TestProcessedDocument:
    def test_foreign_unit_rejected(self) -> None:
        with pytest.raises(ContractError, match="belongs to document 'doc-b'"):
            ProcessedDocument(
                document_id="doc-a",
                revision="rev-1",
                units=(make_semantic_unit("doc-b"),),
            )


class TestEmbeddingIndex:
    def test_dimension_mismatch_rejected(self) -> None:
        index = make_embedding_index()
        bad_record = make_embedding_record("doc-c:section-0:chunk-0")
        bad_record = type(bad_record)(
            unit_id=bad_record.unit_id,
            model_fingerprint=bad_record.model_fingerprint,
            dimensions=1024,
            normalized=bad_record.normalized,
            dtype=bad_record.dtype,
            vector_ref=bad_record.vector_ref,
        )
        with pytest.raises(ContractError, match="does not match the index"):
            EmbeddingIndex(
                header=index.header,
                model_fingerprint=index.model_fingerprint,
                dimensions=index.dimensions,
                normalized=index.normalized,
                dtype=index.dtype,
                runtime=index.runtime,
                records=(*index.records, bad_record),
            )

    def test_duplicate_unit_ids_rejected(self) -> None:
        index = make_embedding_index()
        with pytest.raises(ContractError, match="duplicate embedding record"):
            EmbeddingIndex(
                header=index.header,
                model_fingerprint=index.model_fingerprint,
                dimensions=index.dimensions,
                normalized=index.normalized,
                dtype=index.dtype,
                runtime=index.runtime,
                records=(index.records[0], index.records[0]),
            )

    def test_zero_dimensions_rejected(self) -> None:
        data = make_embedding_record().to_dict()
        data["dimensions"] = 0
        with pytest.raises(ContractError, match="dimensions must be > 0"):
            type(make_embedding_record()).from_dict(data)


class TestRuntimeReport:
    def test_invalid_requested_batch_size_rejected(self) -> None:
        data = RuntimeReport(device="cpu", effective_batch_size=8).to_dict()
        data["requested_batch_size"] = "huge"
        with pytest.raises(ContractError, match="positive integer or 'auto'"):
            RuntimeReport.from_dict(data)

    def test_integer_requested_batch_size_accepted(self) -> None:
        data = RuntimeReport(device="cpu", effective_batch_size=8).to_dict()
        data["requested_batch_size"] = 32
        assert RuntimeReport.from_dict(data).requested_batch_size == 32


class TestCandidatePair:
    def test_self_pair_rejected(self) -> None:
        with pytest.raises(ContractError, match="self-pair"):
            CandidatePair(source_document_id="doc-a", target_document_id="doc-a")


class TestProposals:
    def test_unknown_direction_rejected(self) -> None:
        data = make_proposal().to_dict()
        data["direction"] = "sideways"
        with pytest.raises(ContractError, match="unknown direction 'sideways'"):
            LinkProposal.from_dict(data)

    def test_rank_below_one_rejected(self) -> None:
        data = make_proposal().to_dict()
        data["rank"] = 0
        with pytest.raises(ContractError, match="rank must be >= 1"):
            LinkProposal.from_dict(data)

    def test_unknown_confidence_rejected(self) -> None:
        data = make_proposal().to_dict()
        data["confidence"] = "certain"
        with pytest.raises(ContractError, match="unknown confidence 'certain'"):
            LinkProposal.from_dict(data)

    def test_non_numeric_feature_rejected(self) -> None:
        data = make_proposal().to_dict()
        data["features"]["lexical_similarity"] = "high"
        with pytest.raises(ContractError, match="must be a number"):
            LinkProposal.from_dict(data)

    def test_unknown_review_status_rejected(self) -> None:
        with pytest.raises(ContractError, match="unknown status 'maybe'"):
            ReviewState(status="maybe")

    def test_duplicate_proposal_ids_rejected(self) -> None:
        with pytest.raises(ContractError, match="duplicate proposal id"):
            ProposalSet(header=make_header(), proposals=(make_proposal(), make_proposal()))


class TestReviewDecision:
    def test_unknown_decision_rejected(self) -> None:
        data = {"proposal_id": "p", "decision": "maybe"}
        with pytest.raises(ContractError, match="unknown decision 'maybe'"):
            ReviewDecision.from_dict(data)

    def test_unknown_reason_code_rejected(self) -> None:
        data = {"proposal_id": "p", "decision": "reject", "reason": "vibes"}
        with pytest.raises(ContractError, match="unknown reason code 'vibes'"):
            ReviewDecision.from_dict(data)

    def test_all_spec_reason_codes_accepted(self) -> None:
        for reason in (
            "already_related",
            "useful_bridge",
            "too_generic",
            "duplicate",
            "weak_evidence",
            "wrong_direction",
            "bad_placement",
        ):
            decision = ReviewDecision.from_dict(
                {"proposal_id": "p", "decision": "reject", "reason": reason}
            )
            assert decision.reason is not None
            assert decision.reason.value == reason


class TestArtifactRef:
    def test_negative_size_rejected(self) -> None:
        with pytest.raises(ContractError, match="size must be >= 0"):
            ArtifactRef(group="runs", key="k", path="runs/k", fingerprint="sha256:x", size=-1)
