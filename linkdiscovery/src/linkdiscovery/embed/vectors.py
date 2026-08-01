"""Vector-table storage shared by the embedding and candidate stages.

The embedding stage persists one dense matrix per run (or per reused artifact)
through :func:`save_vector_table`; each :class:`EmbeddingRecord` then points at
its row with a ``vector_ref`` of the form ``"<artifact-key>#<row>"``. The
candidate stage resolves an :class:`EmbeddingIndex` back into an in-memory
:class:`VectorTable` with :func:`load_vector_table`, without either stage
knowing the other's internals. This is the only module that interprets
``vector_ref``; every other consumer treats it as opaque.

Serialization uses NumPy's ``.npz`` container (``allow_pickle=False``) written
through the atomic :class:`~linkdiscovery.artifacts.store.ArtifactStore`, so a
partial vector artifact can never appear complete.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Final

import numpy as np

from linkdiscovery.errors import ArtifactError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from linkdiscovery.artifacts.store import ArtifactStore
    from linkdiscovery.contracts.embeddings import EmbeddingIndex
    from linkdiscovery.contracts.manifests import ArtifactRef

__all__ = [
    "VECTOR_GROUP",
    "VectorTable",
    "load_vector_table",
    "make_vector_ref",
    "parse_vector_ref",
    "save_vector_table",
]

VECTOR_GROUP: Final = "embeddings"
"""Artifact group under which vector tables are stored."""

_REF_SEPARATOR: Final = "#"

_MATRIX_NDIM: Final = 2


def make_vector_ref(artifact_key: str, row: int) -> str:
    """Build the ``vector_ref`` for one row of a stored vector table.

    ``artifact_key`` must be a valid artifact-store key (which never contains
    ``#``), so the reference parses unambiguously. Raises ``ArtifactError`` on
    a negative row or a key containing the separator.
    """
    if _REF_SEPARATOR in artifact_key:
        raise ArtifactError(f"vector artifact key {artifact_key!r} must not contain '#'")
    if row < 0:
        raise ArtifactError(f"vector row must be >= 0, got {row}")
    return f"{artifact_key}{_REF_SEPARATOR}{row}"


def parse_vector_ref(vector_ref: str) -> tuple[str, int]:
    """Split a ``vector_ref`` into ``(artifact_key, row)``.

    Raises ``ArtifactError`` when the reference does not have the
    ``"<artifact-key>#<row>"`` shape produced by :func:`make_vector_ref`.
    """
    key, separator, row_text = vector_ref.rpartition(_REF_SEPARATOR)
    if not separator or not key or not row_text.isdigit():
        raise ArtifactError(f"malformed vector_ref {vector_ref!r}; expected '<artifact-key>#<row>'")
    return key, int(row_text)


class VectorTable:
    """An in-memory ``(unit_ids, matrix)`` pair with aligned rows.

    Invariants (enforced at construction): the matrix is two-dimensional,
    ``float32``, C-contiguous, has exactly one row per unit ID, and unit IDs
    are unique. Rows are addressable by unit through :meth:`row_for_unit`.
    Instances are read-only views over the embedding artifact; mutating the
    matrix is a programming error.
    """

    __slots__ = ("_matrix", "_row_by_unit", "_unit_ids")

    def __init__(self, unit_ids: Sequence[str], matrix: NDArray[np.float32]) -> None:
        """Validate alignment and index rows by unit ID.

        Raises ``ArtifactError`` on shape/ID mismatches or duplicate IDs.
        """
        if matrix.ndim != _MATRIX_NDIM:
            raise ArtifactError(f"vector matrix must be 2-D, got {matrix.ndim}-D")
        if len(unit_ids) != matrix.shape[0]:
            raise ArtifactError(
                f"vector table misaligned: {len(unit_ids)} unit ids for "
                f"{matrix.shape[0]} matrix rows"
            )
        prepared = np.ascontiguousarray(matrix, dtype=np.float32)
        prepared.setflags(write=False)
        self._unit_ids: tuple[str, ...] = tuple(unit_ids)
        self._matrix = prepared
        self._row_by_unit = {unit_id: row for row, unit_id in enumerate(self._unit_ids)}
        if len(self._row_by_unit) != len(self._unit_ids):
            raise ArtifactError("vector table contains duplicate unit ids")

    @property
    def unit_ids(self) -> tuple[str, ...]:
        """Unit IDs in row order."""
        return self._unit_ids

    @property
    def matrix(self) -> NDArray[np.float32]:
        """The read-only ``(n_units, dimensions)`` float32 matrix."""
        return self._matrix

    @property
    def dimensions(self) -> int:
        """Vector dimensionality (number of matrix columns)."""
        return int(self._matrix.shape[1])

    def __len__(self) -> int:
        """Number of stored vectors."""
        return len(self._unit_ids)

    def __contains__(self, unit_id: object) -> bool:
        """Whether a vector exists for ``unit_id``."""
        return unit_id in self._row_by_unit

    def row_for_unit(self, unit_id: str) -> int:
        """Return the matrix row holding ``unit_id``'s vector.

        Raises ``ArtifactError`` for an unknown unit, which indicates an
        index/table mismatch upstream.
        """
        row = self._row_by_unit.get(unit_id)
        if row is None:
            raise ArtifactError(f"vector table has no row for unit {unit_id!r}")
        return row

    def vector_for_unit(self, unit_id: str) -> NDArray[np.float32]:
        """Return the (read-only) vector for ``unit_id``.

        Raises ``ArtifactError`` for an unknown unit.
        """
        vector: NDArray[np.float32] = self._matrix[self.row_for_unit(unit_id)]
        return vector

    def select(self, unit_ids: Sequence[str]) -> VectorTable:
        """Return a new table restricted to ``unit_ids``, in the given order.

        Used by per-view retrieval to slice one view's units out of the full
        index. Raises ``ArtifactError`` when any unit is missing.
        """
        rows = [self.row_for_unit(unit_id) for unit_id in unit_ids]
        return VectorTable(tuple(unit_ids), self._matrix[rows])


def save_vector_table(
    store: ArtifactStore,
    key: str,
    unit_ids: Sequence[str],
    matrix: NDArray[np.floating],
    *,
    dtype: str = "float32",
) -> ArtifactRef:
    """Atomically persist a vector table under ``embeddings/<key>``.

    ``dtype`` controls the stored precision (``"float16"`` or ``"float32"``);
    loading always widens back to float32 for computation. The caller derives
    ``key`` from content fingerprints so identical logical tables share one
    artifact. Raises ``ArtifactError`` on misaligned inputs or an unsupported
    dtype.
    """
    if len(unit_ids) != matrix.shape[0]:
        raise ArtifactError(
            f"cannot save vector table: {len(unit_ids)} unit ids for {matrix.shape[0]} matrix rows"
        )
    if dtype not in ("float16", "float32"):
        raise ArtifactError(f"unsupported vector storage dtype {dtype!r}")
    buffer = io.BytesIO()
    np.savez(
        buffer,
        unit_ids=np.asarray(tuple(unit_ids), dtype=np.str_),
        matrix=np.ascontiguousarray(matrix, dtype=np.dtype(dtype)),
    )
    return store.put_bytes(VECTOR_GROUP, key, buffer.getvalue())


def _load_raw_table(store: ArtifactStore, key: str) -> tuple[tuple[str, ...], NDArray[np.float32]]:
    """Load one stored ``.npz`` table, widening to float32."""
    data = store.get_bytes(VECTOR_GROUP, key)
    try:
        with np.load(io.BytesIO(data), allow_pickle=False) as archive:
            unit_ids = tuple(str(unit_id) for unit_id in archive["unit_ids"])
            matrix = archive["matrix"].astype(np.float32)
    except (KeyError, ValueError, OSError) as exc:
        raise ArtifactError(f"vector artifact {VECTOR_GROUP}/{key} is corrupt: {exc}") from exc
    if matrix.ndim != _MATRIX_NDIM or len(unit_ids) != matrix.shape[0]:
        raise ArtifactError(f"vector artifact {VECTOR_GROUP}/{key} is corrupt: misaligned table")
    return unit_ids, matrix


def load_vector_table(store: ArtifactStore, index: EmbeddingIndex) -> VectorTable:
    """Resolve an :class:`EmbeddingIndex` into an in-memory :class:`VectorTable`.

    The returned table holds one row per index record, in record order, so
    ``table.unit_ids`` mirrors the index. Records may reference multiple
    stored artifacts (incremental runs reuse prior tables); each artifact is
    loaded once. Raises ``ArtifactError`` on malformed references, missing
    artifacts, dimension mismatches with the index, or a reference whose
    stored unit ID disagrees with its record.
    """
    parsed = [parse_vector_ref(record.vector_ref) for record in index.records]
    tables: dict[str, tuple[tuple[str, ...], NDArray[np.float32]]] = {}
    for key, _ in parsed:
        if key not in tables:
            tables[key] = _load_raw_table(store, key)
    if index.records:
        widths = {matrix.shape[1] for _, matrix in tables.values()}
        if widths != {index.dimensions}:
            raise ArtifactError(
                f"vector artifacts have dimensions {sorted(widths)} but the embedding "
                f"index declares {index.dimensions}"
            )
    rows = np.empty((len(index.records), index.dimensions), dtype=np.float32)
    unit_ids: list[str] = []
    for position, (record, (key, row)) in enumerate(zip(index.records, parsed, strict=True)):
        stored_ids, matrix = tables[key]
        if row >= len(stored_ids):
            raise ArtifactError(
                f"vector_ref {record.vector_ref!r} points past the end of "
                f"{VECTOR_GROUP}/{key} ({len(stored_ids)} rows)"
            )
        if stored_ids[row] != record.unit_id:
            raise ArtifactError(
                f"vector_ref {record.vector_ref!r} resolves to unit {stored_ids[row]!r}, "
                f"but the record is for unit {record.unit_id!r}; the index and vector "
                f"artifact are out of sync"
            )
        rows[position] = matrix[row]
        unit_ids.append(record.unit_id)
    return VectorTable(unit_ids, rows)
