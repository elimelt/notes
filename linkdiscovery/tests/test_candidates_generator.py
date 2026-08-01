"""Generator tests: retrieval wiring, alias/exclusion policy, bounds, features.

Also exports the synthetic corpus/index builders reused by the ranking tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import pytest

from linkdiscovery.artifacts import ArtifactStore
from linkdiscovery.candidates import DefaultCandidateGenerator
from linkdiscovery.config import CandidateConfig
from linkdiscovery.contracts.base import ArtifactHeader
from linkdiscovery.contracts.candidates import CandidatePair, CandidateSet
from linkdiscovery.contracts.documents import Relationship, RelationshipSet
from linkdiscovery.contracts.embeddings import EmbeddingIndex, EmbeddingRecord, RuntimeReport
from linkdiscovery.contracts.units import (
    ProcessedCorpus,
    ProcessedDocument,
    RegionKind,
    SemanticUnit,
    Span,
)
from linkdiscovery.embed.vectors import make_vector_ref, save_vector_table
from linkdiscovery.errors import CandidateError
from linkdiscovery.fingerprint import canonical_json

if TYPE_CHECKING:
    from collections.abc import Sequence

BINDING_FEATURE_KEYS = frozenset(
    {
        "document_similarity",
        "title_similarity",
        "best_chunk_similarity",
        "top_r_mean_similarity",
        "support_breadth",
        "source_chunk_count",
        "target_chunk_count",
        "source_token_count",
        "target_token_count",
        "lexical_similarity",
        "graph_distance",
        "common_neighbor_count",
        "hubness_source",
        "hubness_target",
        "csls_similarity",
        "csls_best_chunk_similarity",
        "near_duplicate_probability",
        "directional_similarity_source_to_target",
        "directional_similarity_target_to_source",
    }
)


@dataclass(frozen=True)
class UnitSpec:
    """One synthetic semantic unit with its (unnormalized) embedding vector."""

    doc: str
    view: str
    vector: tuple[float, ...]
    text: str = "generic prose text about a topic"
    tokens: int = 50


def fixture_header(corpus_id: str = "corpus-test") -> ArtifactHeader:
    return ArtifactHeader(
        schema_version=1,
        run_id="run-fixture",
        corpus_id=corpus_id,
        created_at="2026-07-31T00:00:00+00:00",
        config_fingerprint="sha256:fixture",
        producer_version="test/1",
    )


def build_inputs(
    store: ArtifactStore,
    specs: Sequence[UnitSpec],
    *,
    extra_index_units: Sequence[tuple[str, tuple[float, ...]]] = (),
    corpus_id: str = "corpus-test",
) -> tuple[ProcessedCorpus, EmbeddingIndex]:
    """Build a ProcessedCorpus and a matching EmbeddingIndex over ``store``.

    Vectors are L2-normalized (matching the upstream embedding contract).
    ``extra_index_units`` inject index records with no corpus counterpart, for
    mismatch tests.
    """
    counters: dict[tuple[str, str], int] = {}
    unit_ids: list[str] = []
    vectors: list[np.ndarray] = []
    units_by_doc: dict[str, list[SemanticUnit]] = {}
    for spec in specs:
        position = counters.get((spec.doc, spec.view), 0)
        counters[(spec.doc, spec.view)] = position + 1
        unit_id = f"{spec.doc}:{spec.view}:{position}"
        units_by_doc.setdefault(spec.doc, []).append(
            SemanticUnit(
                id=unit_id,
                document_id=spec.doc,
                view=spec.view,
                section_path=("Body",),
                region_kinds=(RegionKind.PROSE,),
                source_spans=(Span(start=position * 100, end=position * 100 + 90),),
                text=spec.text,
                token_count=spec.tokens,
                content_hash=f"sha256:{unit_id}",
            )
        )
        unit_ids.append(unit_id)
        vector = np.asarray(spec.vector, dtype=np.float64)
        vectors.append(vector / np.linalg.norm(vector))
    for ghost_id, ghost_vector in extra_index_units:
        unit_ids.append(ghost_id)
        vector = np.asarray(ghost_vector, dtype=np.float64)
        vectors.append(vector / np.linalg.norm(vector))
    matrix = np.stack(vectors).astype(np.float32)
    save_vector_table(store, "vectors-fixture", unit_ids, matrix)
    header = fixture_header(corpus_id)
    index = EmbeddingIndex(
        header=header,
        model_fingerprint="sha256:model",
        dimensions=int(matrix.shape[1]),
        normalized=True,
        dtype="float32",
        runtime=RuntimeReport(device="cpu", effective_batch_size=8),
        records=tuple(
            EmbeddingRecord(
                unit_id=unit_id,
                model_fingerprint="sha256:model",
                dimensions=int(matrix.shape[1]),
                normalized=True,
                dtype="float32",
                vector_ref=make_vector_ref("vectors-fixture", row),
            )
            for row, unit_id in enumerate(unit_ids)
        ),
    )
    corpus = ProcessedCorpus(
        header=header,
        preprocessing_fingerprint="sha256:pre",
        documents=tuple(
            ProcessedDocument(document_id=doc, revision="rev-1", units=tuple(units))
            for doc, units in sorted(units_by_doc.items())
        ),
    )
    return corpus, index


def rel(source: str, target: str, kind: str) -> Relationship:
    return Relationship(source_id=source, target_id=target, kind=kind, directed=False)


def run_generator(
    store: ArtifactStore,
    specs: Sequence[UnitSpec],
    *,
    relationships: Sequence[Relationship] = (),
    config: CandidateConfig | None = None,
    extra_index_units: Sequence[tuple[str, tuple[float, ...]]] = (),
) -> CandidateSet:
    corpus, index = build_inputs(store, specs, extra_index_units=extra_index_units)
    generator = DefaultCandidateGenerator(store, run_id="run-test")
    return generator.generate(
        corpus, index, RelationshipSet(tuple(relationships)), config or CandidateConfig()
    )


def pair_keys(candidates: CandidateSet) -> list[tuple[str, str]]:
    return [(pair.source_document_id, pair.target_document_id) for pair in candidates.pairs]


def find_pair(candidates: CandidateSet, source: str, target: str) -> CandidatePair:
    for pair in candidates.pairs:
        if (pair.source_document_id, pair.target_document_id) == (source, target):
            return pair
    raise AssertionError(f"pair ({source!r}, {target!r}) not in candidate set")


@dataclass(frozen=True)
class HubFixture:
    """Planted hub geometry shared with the ranking tests (acceptance criterion 7)."""

    specs: tuple[UnitSpec, ...] = field(
        default=(
            UnitSpec("filler-0", "document", (1.0, 0.00, 0.0, 0.0), "filler zero common topic"),
            UnitSpec("filler-1", "document", (1.0, 0.02, 0.0, 0.0), "filler one common topic"),
            UnitSpec("filler-2", "document", (1.0, 0.04, 0.0, 0.0), "filler two common topic"),
            UnitSpec("filler-3", "document", (1.0, 0.06, 0.0, 0.0), "filler three common topic"),
            UnitSpec("filler-4", "document", (1.0, 0.08, 0.0, 0.0), "filler four common topic"),
            UnitSpec("filler-5", "document", (1.0, 0.10, 0.0, 0.0), "filler five common topic"),
            UnitSpec("hub", "document", (0.8, 0.0, 0.6, 0.0), "hub survey of everything common"),
            UnitSpec("src", "document", (0.6, 0.0, 0.8, 0.0), "source note on special subsystem"),
            UnitSpec(
                "tgt", "document", (0.6, 0.0, 0.7, 0.39), "target note special subsystem internals"
            ),
        )
    )


def test_planted_nearest_neighbors_found(store: ArtifactStore) -> None:
    specs = [
        UnitSpec("doc-a", "section", (1.0, 0.0, 0.0, 0.0)),
        UnitSpec("doc-b", "section", (0.98, 0.2, 0.0, 0.0)),
        UnitSpec("doc-c", "section", (0.0, 0.0, 1.0, 0.0)),
    ]
    candidates = run_generator(store, specs)
    pair = find_pair(candidates, "doc-a", "doc-b")
    assert pair.matches[0].source_unit_id == "doc-a:section:0"
    assert pair.matches[0].target_unit_id == "doc-b:section:0"
    assert pair.matches[0].view == "section"
    assert pair.matches[0].similarity > 0.95
    # The strongest pair sorts first.
    assert pair_keys(candidates)[0] == ("doc-a", "doc-b")


def test_no_self_alias_existing_or_excluded_pairs(store: ArtifactStore) -> None:
    vector = (1.0, 0.1, 0.0, 0.0)
    specs = [
        UnitSpec("doc-a", "section", vector),
        UnitSpec("doc-b", "section", vector),  # alias of doc-a
        UnitSpec("doc-c", "section", vector),  # existing direct link to doc-a
        UnitSpec("doc-d", "section", vector),  # exclusion relationship with doc-a
        UnitSpec("doc-e", "section", vector),
    ]
    relationships = [
        rel("doc-b", "doc-a", "alias"),
        rel("doc-a", "doc-c", "explicit-link"),
        rel("doc-a", "doc-d", "exclusion"),
    ]
    candidates = run_generator(store, specs, relationships=relationships)
    keys = pair_keys(candidates)
    assert keys, "expected surviving candidate pairs"
    for source, target in keys:
        assert source != target
        assert source < target
        assert not {source, target} <= {"doc-a", "doc-b"}  # alias class is a self-pair
        assert "doc-b" not in (source, target)  # alias resolves to canonical doc-a
    assert ("doc-a", "doc-c") not in keys  # existing direct link
    assert ("doc-a", "doc-d") not in keys  # adapter-declared exclusion
    assert ("doc-a", "doc-e") in keys


def test_reciprocal_matches_collapse_to_one_pair(store: ArtifactStore) -> None:
    specs = [
        UnitSpec("doc-x", "section", (1.0, 0.05, 0.0, 0.0)),
        UnitSpec("doc-y", "section", (1.0, 0.00, 0.0, 0.0)),
    ]
    candidates = run_generator(store, specs)
    assert pair_keys(candidates) == [("doc-x", "doc-y")]
    pair = candidates.pairs[0]
    assert len(pair.matches) == 1  # x->y and y->x collapse into one oriented match
    assert pair.matches[0].source_unit_id == "doc-x:section:0"


def test_max_pairs_per_document_bound_with_tie_breaks(store: ArtifactStore) -> None:
    specs = [
        UnitSpec("doc-s", "section", (1.0, 0.0, 0.0, 0.0)),
        UnitSpec("doc-t1", "section", (0.95, 0.312, 0.0, 0.0)),
        UnitSpec("doc-t2", "section", (0.90, 0.0, 0.436, 0.0)),
        UnitSpec("doc-t3", "section", (0.85, 0.0, 0.0, 0.527)),
    ]
    candidates = run_generator(store, specs, config=CandidateConfig(max_pairs_per_document=2))
    keys = pair_keys(candidates)
    assert ("doc-s", "doc-t3") not in keys  # weakest pair for doc-s is dropped
    assert ("doc-s", "doc-t1") in keys
    assert ("doc-s", "doc-t2") in keys
    counts: dict[str, int] = {}
    for source, target in keys:
        counts[source] = counts.get(source, 0) + 1
        counts[target] = counts.get(target, 0) + 1
    assert all(count <= 2 for count in counts.values())


def test_bound_tie_break_prefers_lexicographic_pair(store: ArtifactStore) -> None:
    vector = (1.0, 0.0, 0.0, 0.0)
    specs = [
        UnitSpec("doc-m", "section", vector),
        UnitSpec("doc-q", "section", vector),
        UnitSpec("doc-z", "section", vector),
    ]
    candidates = run_generator(store, specs, config=CandidateConfig(max_pairs_per_document=1))
    # All similarities are exactly 1.0; the lexicographically smallest pair wins.
    assert pair_keys(candidates) == [("doc-m", "doc-q")]


def test_max_total_pairs_bound(store: ArtifactStore) -> None:
    specs = [
        UnitSpec("doc-a", "section", (1.0, 0.0, 0.0, 0.0)),
        UnitSpec("doc-b", "section", (0.99, 0.14, 0.0, 0.0)),
        UnitSpec("doc-c", "section", (0.5, 0.86, 0.0, 0.0)),
    ]
    candidates = run_generator(store, specs, config=CandidateConfig(max_total_pairs=1))
    assert pair_keys(candidates) == [("doc-a", "doc-b")]


def test_index_corpus_mismatch_raises(store: ArtifactStore) -> None:
    specs = [
        UnitSpec("doc-a", "section", (1.0, 0.0, 0.0, 0.0)),
        UnitSpec("doc-b", "section", (0.9, 0.44, 0.0, 0.0)),
    ]
    with pytest.raises(CandidateError, match="mismatch"):
        run_generator(
            store,
            specs,
            extra_index_units=(("ghost:section:0", (0.0, 1.0, 0.0, 0.0)),),
        )


def test_matches_bounded_per_pair(store: ArtifactStore) -> None:
    specs = [
        *(UnitSpec("doc-a", "section", (1.0, 0.01 * i, 0.0, 0.0)) for i in range(4)),
        *(UnitSpec("doc-b", "section", (1.0, 0.0, 0.01 * i, 0.0)) for i in range(4)),
    ]
    candidates = run_generator(store, specs)
    pair = find_pair(candidates, "doc-a", "doc-b")
    assert len(pair.matches) == 8  # 16 raw section matches, bounded to the strongest 8
    sims = [match.similarity for match in pair.matches]
    assert sims == sorted(sims, reverse=True)


def test_graph_distance_and_common_neighbors(store: ArtifactStore) -> None:
    specs = [
        UnitSpec("doc-a", "section", (1.0, 0.00, 0.0, 0.0)),
        UnitSpec("doc-b", "section", (1.0, 0.01, 0.0, 0.0)),
        UnitSpec("doc-c", "section", (1.0, 0.02, 0.0, 0.0)),
        UnitSpec("doc-d", "section", (1.0, 0.03, 0.0, 0.0)),
        UnitSpec("doc-e", "section", (1.0, 0.04, 0.0, 0.0)),
    ]
    # "reference" is a weaker graph signal: not an alias and not an existing
    # direct-link kind, so these pairs stay candidates but carry graph features.
    relationships = [
        rel("doc-a", "doc-b", "reference"),
        rel("doc-b", "doc-c", "reference"),
        rel("doc-c", "doc-d", "reference"),
    ]
    candidates = run_generator(store, specs, relationships=relationships)
    direct = find_pair(candidates, "doc-a", "doc-b").features
    assert direct["graph_distance"] == 1.0
    two_hops = find_pair(candidates, "doc-a", "doc-c").features
    assert two_hops["graph_distance"] == 2.0
    assert two_hops["common_neighbor_count"] == 1.0  # doc-b
    three_hops = find_pair(candidates, "doc-a", "doc-d").features
    assert three_hops["graph_distance"] == 3.0
    assert three_hops["common_neighbor_count"] == 0.0
    unreachable = find_pair(candidates, "doc-a", "doc-e").features
    assert unreachable["graph_distance"] == 6.0


def test_binding_feature_vocabulary_present(store: ArtifactStore) -> None:
    specs = [
        UnitSpec("doc-a", "document", (1.0, 0.0, 0.0, 0.0)),
        UnitSpec("doc-a", "section", (0.9, 0.44, 0.0, 0.0)),
        UnitSpec("doc-a", "title", (0.8, 0.6, 0.0, 0.0)),
        UnitSpec("doc-b", "document", (0.95, 0.31, 0.0, 0.0)),
        UnitSpec("doc-b", "section", (0.9, 0.4, 0.17, 0.0)),
        UnitSpec("doc-b", "title", (0.8, 0.55, 0.23, 0.0)),
    ]
    candidates = run_generator(store, specs)
    pair = find_pair(candidates, "doc-a", "doc-b")
    assert set(pair.features) >= BINDING_FEATURE_KEYS
    assert pair.features["document_similarity"] > 0.9
    assert pair.features["title_similarity"] > 0.9
    assert pair.features["best_chunk_similarity"] > 0.9
    assert pair.features["source_chunk_count"] == 1.0
    assert pair.features["source_token_count"] == 50.0


def test_document_similarity_zero_when_view_missing(store: ArtifactStore) -> None:
    specs = [
        UnitSpec("doc-a", "section", (1.0, 0.0, 0.0, 0.0)),
        UnitSpec("doc-b", "section", (0.95, 0.31, 0.0, 0.0)),
    ]
    candidates = run_generator(store, specs)
    features = find_pair(candidates, "doc-a", "doc-b").features
    assert features["document_similarity"] == 0.0
    assert features["title_similarity"] == 0.0
    assert features["best_chunk_similarity"] > 0.9


def test_support_breadth_saturates(store: ArtifactStore) -> None:
    specs = [
        *(UnitSpec("doc-a", "section", (1.0, 0.01 * i, 0.0, 0.0)) for i in range(3)),
        *(UnitSpec("doc-b", "section", (1.0, 0.0, 0.01 * i, 0.0)) for i in range(3)),
    ]
    candidates = run_generator(store, specs)
    features = find_pair(candidates, "doc-a", "doc-b").features
    # 8 kept matches involve up to 3 + 3 = 6 distinct sections -> saturated.
    assert features["support_breadth"] == 1.0


def test_near_duplicate_probability_extremes(store: ArtifactStore) -> None:
    duplicate_text = "identical wording of the same note body"
    specs = [
        UnitSpec("doc-a", "document", (1.0, 0.0, 0.0, 0.0), duplicate_text, tokens=40),
        UnitSpec("doc-b", "document", (1.0, 0.0, 0.0, 0.0), duplicate_text, tokens=40),
        UnitSpec("doc-c", "document", (0.7, 0.71, 0.0, 0.0), "an unrelated note", tokens=10),
    ]
    candidates = run_generator(store, specs)
    duplicate = find_pair(candidates, "doc-a", "doc-b").features
    assert duplicate["near_duplicate_probability"] == pytest.approx(1.0, abs=1e-5)
    distinct = find_pair(candidates, "doc-a", "doc-c").features
    assert distinct["near_duplicate_probability"] == 0.0


def test_hubness_correction_demotes_planted_hub(store: ArtifactStore) -> None:
    """Acceptance criterion 7: the hub outranks the specific match on raw
    similarity but loses after CSLS local scaling."""
    candidates = run_generator(store, list(HubFixture().specs))
    hub_pair = find_pair(candidates, "hub", "src").features
    specific_pair = find_pair(candidates, "src", "tgt").features
    assert hub_pair["document_similarity"] > specific_pair["document_similarity"]
    assert hub_pair["hubness_source"] > specific_pair["hubness_target"]
    assert specific_pair["csls_similarity"] > hub_pair["csls_similarity"]


def test_alias_canonical_id_used_for_pairs(store: ArtifactStore) -> None:
    specs = [
        UnitSpec("doc-aa", "title", (0.0, 0.0, 0.0, 1.0), "alias canonical title"),
        UnitSpec("doc-zz", "section", (1.0, 0.0, 0.0, 0.0)),  # alias of doc-aa
        UnitSpec("doc-mm", "section", (0.95, 0.31, 0.0, 0.0)),
    ]
    candidates = run_generator(store, specs, relationships=[rel("doc-zz", "doc-aa", "alias")])
    # The pair carries the canonical (lexicographically smallest present) alias id.
    assert pair_keys(candidates) == [("doc-aa", "doc-mm")]
    pair = candidates.pairs[0]
    assert pair.matches[0].source_unit_id == "doc-zz:section:0"


def test_generation_is_deterministic_and_byte_identical(
    store: ArtifactStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "linkdiscovery.candidates.generator.utc_now_iso",
        lambda: "2026-07-31T12:00:00+00:00",
    )
    specs = [
        *HubFixture().specs,
        UnitSpec("src", "section", (0.6, 0.0, 0.79, 0.1), "special subsystem deep dive"),
        UnitSpec("tgt", "section", (0.62, 0.0, 0.77, 0.12), "subsystem internals continued"),
    ]
    corpus, index = build_inputs(store, specs)
    relationships = RelationshipSet((rel("filler-0", "filler-1", "reference"),))
    config = CandidateConfig()
    generator = DefaultCandidateGenerator(store, run_id="run-test")
    first = generator.generate(corpus, index, relationships, config)
    second = generator.generate(corpus, index, relationships, config)
    assert canonical_json(first.to_dict()) == canonical_json(second.to_dict())
    assert first.pairs  # the comparison is not vacuous


def test_header_provenance(store: ArtifactStore) -> None:
    specs = [
        UnitSpec("doc-a", "section", (1.0, 0.0, 0.0, 0.0)),
        UnitSpec("doc-b", "section", (0.9, 0.44, 0.0, 0.0)),
    ]
    config = CandidateConfig(neighbors_per_unit=5)
    corpus, index = build_inputs(store, specs)
    generator = DefaultCandidateGenerator(store, run_id="run-42", producer_version="test/9")
    candidates = generator.generate(corpus, index, RelationshipSet(), config)
    assert candidates.header.run_id == "run-42"
    assert candidates.header.corpus_id == "corpus-test"
    assert candidates.header.config_fingerprint == config.fingerprint()
    assert candidates.header.producer_version == "test/9"
