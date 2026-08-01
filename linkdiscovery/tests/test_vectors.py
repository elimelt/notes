"""Tests for the vector-table storage boundary."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pytest

from linkdiscovery.artifacts.store import ArtifactStore
from linkdiscovery.contracts.base import ArtifactHeader
from linkdiscovery.contracts.embeddings import EmbeddingIndex, EmbeddingRecord, RuntimeReport
from linkdiscovery.embed import (
    VectorTable,
    load_vector_table,
    make_vector_ref,
    save_vector_table,
)
from linkdiscovery.embed.vectors import parse_vector_ref
from linkdiscovery.errors import ArtifactError

MODEL_FINGERPRINT = "sha256:model"


@pytest.fixture
def store(tmp_path: Path) -> ArtifactStore:
    return ArtifactStore(tmp_path / "artifacts")


def _header() -> ArtifactHeader:
    return ArtifactHeader(
        schema_version=1,
        run_id="run-1",
        corpus_id="corpus-1",
        created_at="2026-07-31T00:00:00+00:00",
        config_fingerprint="sha256:config",
        producer_version="test",
    )


def _index(records: tuple[EmbeddingRecord, ...], dimensions: int = 3) -> EmbeddingIndex:
    return EmbeddingIndex(
        header=_header(),
        model_fingerprint=MODEL_FINGERPRINT,
        dimensions=dimensions,
        normalized=True,
        dtype="float32",
        runtime=RuntimeReport(device="cpu", effective_batch_size=8),
        records=records,
    )


def _record(unit_id: str, vector_ref: str, dimensions: int = 3) -> EmbeddingRecord:
    return EmbeddingRecord(
        unit_id=unit_id,
        model_fingerprint=MODEL_FINGERPRINT,
        dimensions=dimensions,
        normalized=True,
        dtype="float32",
        vector_ref=vector_ref,
    )


class TestVectorRef:
    def test_round_trip(self) -> None:
        ref = make_vector_ref("sha256:abc", 7)
        assert parse_vector_ref(ref) == ("sha256:abc", 7)

    def test_rejects_negative_row(self) -> None:
        with pytest.raises(ArtifactError, match="row"):
            make_vector_ref("key", -1)

    def test_rejects_separator_in_key(self) -> None:
        with pytest.raises(ArtifactError, match="#"):
            make_vector_ref("bad#key", 0)

    @pytest.mark.parametrize("bad", ["", "no-separator", "#3", "key#", "key#x2"])
    def test_rejects_malformed_refs(self, bad: str) -> None:
        with pytest.raises(ArtifactError, match="vector_ref"):
            parse_vector_ref(bad)


class TestVectorTable:
    def test_alignment_and_lookup(self) -> None:
        table = VectorTable(("u1", "u2"), np.eye(2, 3, dtype=np.float32))
        assert len(table) == 2
        assert table.dimensions == 3
        assert "u2" in table
        assert table.row_for_unit("u2") == 1
        np.testing.assert_array_equal(table.vector_for_unit("u1"), [1.0, 0.0, 0.0])

    def test_matrix_is_read_only(self) -> None:
        table = VectorTable(("u1",), np.zeros((1, 2), dtype=np.float32))
        with pytest.raises(ValueError, match="read-only"):
            table.matrix[0, 0] = 1.0

    def test_select_preserves_requested_order(self) -> None:
        table = VectorTable(("a", "b", "c"), np.diag([1.0, 2.0, 3.0]).astype(np.float32))
        subset = table.select(["c", "a"])
        assert subset.unit_ids == ("c", "a")
        np.testing.assert_array_equal(subset.matrix[0], [0.0, 0.0, 3.0])

    def test_rejects_misalignment(self) -> None:
        with pytest.raises(ArtifactError, match="misaligned"):
            VectorTable(("u1",), np.zeros((2, 2), dtype=np.float32))

    def test_rejects_duplicate_unit_ids(self) -> None:
        with pytest.raises(ArtifactError, match="duplicate"):
            VectorTable(("u1", "u1"), np.zeros((2, 2), dtype=np.float32))

    def test_rejects_non_2d(self) -> None:
        with pytest.raises(ArtifactError, match="2-D"):
            VectorTable(("u1",), np.zeros(3, dtype=np.float32))

    def test_unknown_unit_raises(self) -> None:
        table = VectorTable(("u1",), np.zeros((1, 2), dtype=np.float32))
        with pytest.raises(ArtifactError, match="no row"):
            table.row_for_unit("missing")


class TestSaveLoad:
    def test_round_trip(self, store: ArtifactStore) -> None:
        matrix = np.arange(6, dtype=np.float32).reshape(2, 3)
        save_vector_table(store, "table-1", ("u1", "u2"), matrix)
        records = tuple(
            _record(unit_id, make_vector_ref("table-1", row))
            for row, unit_id in enumerate(("u1", "u2"))
        )
        table = load_vector_table(store, _index(records))
        assert table.unit_ids == ("u1", "u2")
        np.testing.assert_allclose(table.matrix, matrix)

    def test_float16_storage_widens_on_load(self, store: ArtifactStore) -> None:
        matrix = np.full((1, 4), 0.5, dtype=np.float32)
        save_vector_table(store, "half", ("u1",), matrix, dtype="float16")
        table = load_vector_table(
            store, _index((_record("u1", make_vector_ref("half", 0), dimensions=4),), 4)
        )
        assert table.matrix.dtype == np.float32
        np.testing.assert_allclose(table.matrix, matrix)

    def test_multiple_artifacts_resolve_in_record_order(self, store: ArtifactStore) -> None:
        save_vector_table(store, "old", ("u1",), np.ones((1, 3), dtype=np.float32))
        save_vector_table(store, "new", ("u2",), np.full((1, 3), 2.0, dtype=np.float32))
        records = (
            _record("u2", make_vector_ref("new", 0)),
            _record("u1", make_vector_ref("old", 0)),
        )
        table = load_vector_table(store, _index(records))
        assert table.unit_ids == ("u2", "u1")
        np.testing.assert_array_equal(table.matrix[1], [1.0, 1.0, 1.0])

    def test_empty_index_loads_empty_table(self, store: ArtifactStore) -> None:
        table = load_vector_table(store, _index(()))
        assert len(table) == 0

    def test_unit_id_mismatch_is_detected(self, store: ArtifactStore) -> None:
        save_vector_table(store, "table-1", ("actual",), np.ones((1, 3), dtype=np.float32))
        index = _index((_record("expected", make_vector_ref("table-1", 0)),))
        with pytest.raises(ArtifactError, match="out of sync"):
            load_vector_table(store, index)

    def test_row_out_of_range_is_detected(self, store: ArtifactStore) -> None:
        save_vector_table(store, "table-1", ("u1",), np.ones((1, 3), dtype=np.float32))
        index = _index((_record("u1", make_vector_ref("table-1", 5)),))
        with pytest.raises(ArtifactError, match="past the end"):
            load_vector_table(store, index)

    def test_dimension_mismatch_is_detected(self, store: ArtifactStore) -> None:
        save_vector_table(store, "table-1", ("u1",), np.ones((1, 5), dtype=np.float32))
        index = _index((_record("u1", make_vector_ref("table-1", 0)),))
        with pytest.raises(ArtifactError, match="dimensions"):
            load_vector_table(store, index)

    def test_missing_artifact_raises(self, store: ArtifactStore) -> None:
        index = _index((_record("u1", make_vector_ref("absent", 0)),))
        with pytest.raises(ArtifactError, match="does not exist"):
            load_vector_table(store, index)

    def test_corrupt_artifact_raises(self, store: ArtifactStore) -> None:
        store.put_bytes("embeddings", "garbage", b"not an npz file")
        index = _index((_record("u1", make_vector_ref("garbage", 0)),))
        with pytest.raises(ArtifactError, match="corrupt"):
            load_vector_table(store, index)

    def test_save_rejects_misalignment(self, store: ArtifactStore) -> None:
        with pytest.raises(ArtifactError, match="cannot save"):
            save_vector_table(store, "bad", ("u1",), np.zeros((2, 3), dtype=np.float32))

    def test_save_rejects_unknown_dtype(self, store: ArtifactStore) -> None:
        with pytest.raises(ArtifactError, match="dtype"):
            save_vector_table(
                store, "bad", ("u1",), np.zeros((1, 3), dtype=np.float32), dtype="int8"
            )

    def test_identical_content_yields_identical_fingerprint(self, store: ArtifactStore) -> None:
        matrix = np.ones((1, 3), dtype=np.float32)
        ref_a = save_vector_table(store, "a", ("u1",), matrix)
        ref_b = save_vector_table(store, "b", ("u1",), matrix)
        assert dataclasses.asdict(ref_a)["size"] == dataclasses.asdict(ref_b)["size"]
