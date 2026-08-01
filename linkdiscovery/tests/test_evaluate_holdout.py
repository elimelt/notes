"""Tests for stratified holdout splitting of existing relationships."""

from __future__ import annotations

import pytest

from linkdiscovery.contracts import Relationship, RelationshipSet
from linkdiscovery.evaluate import degree_bucket, split_relationships


def rel(source: str, target: str, kind: str = "explicit-link") -> Relationship:
    return Relationship(source_id=source, target_id=target, kind=kind)


def stratified_relationships() -> RelationshipSet:
    """doc-a has out-degree 1, doc-b 4, doc-c 6 (all explicit links)."""
    relationships = [rel("doc-a", "t-a1")]
    relationships += [rel("doc-b", f"t-b{i}") for i in range(4)]
    relationships += [rel("doc-c", f"t-c{i}") for i in range(6)]
    relationships.append(rel("doc-a", "tagged", kind="tag"))
    return RelationshipSet(relationships=tuple(relationships))


class TestValidation:
    @pytest.mark.parametrize("fraction", [0.0, 1.0, -0.1, 1.5])
    def test_fraction_must_be_in_open_interval(self, fraction: float) -> None:
        with pytest.raises(ValueError, match=r"holdout_fraction must be in the open interval"):
            split_relationships(stratified_relationships(), holdout_fraction=fraction, seed=1)


class TestSplit:
    def test_partition_is_complete_and_disjoint(self) -> None:
        original = stratified_relationships()
        visible, held_out = split_relationships(original, holdout_fraction=0.5, seed=3)
        assert len(visible.relationships) + len(held_out.relationships) == len(
            original.relationships
        )
        visible_keys = {(r.source_id, r.target_id) for r in visible.relationships}
        held_keys = {(r.source_id, r.target_id) for r in held_out.relationships}
        assert visible_keys.isdisjoint(held_keys)

    def test_only_configured_kinds_are_held_out(self) -> None:
        _, held_out = split_relationships(stratified_relationships(), holdout_fraction=0.5, seed=3)
        assert all(r.kind == "explicit-link" for r in held_out.relationships)

    def test_other_kinds_always_visible(self) -> None:
        visible, _ = split_relationships(stratified_relationships(), holdout_fraction=0.9, seed=3)
        assert any(r.kind == "tag" for r in visible.relationships)

    def test_stratified_counts_per_degree_bucket(self) -> None:
        # Bucket sizes: "1" has 1 member (doc-a), "2-4" has 4 (doc-b),
        # "5+" has 6 (doc-c). With fraction 0.5, round() hides 0, 2, and 3.
        _, held_out = split_relationships(stratified_relationships(), holdout_fraction=0.5, seed=11)
        by_source = {
            doc: sum(1 for r in held_out.relationships if r.source_id == doc)
            for doc in ("doc-a", "doc-b", "doc-c")
        }
        assert by_source == {"doc-a": 0, "doc-b": 2, "doc-c": 3}

    def test_deterministic_for_a_seed(self) -> None:
        first = split_relationships(stratified_relationships(), holdout_fraction=0.5, seed=5)
        second = split_relationships(stratified_relationships(), holdout_fraction=0.5, seed=5)
        assert first == second

    def test_input_order_preserved(self) -> None:
        original = stratified_relationships()
        visible, held_out = split_relationships(original, holdout_fraction=0.5, seed=2)
        positions = {(r.source_id, r.target_id): i for i, r in enumerate(original.relationships)}
        for subset in (visible, held_out):
            indexes = [positions[(r.source_id, r.target_id)] for r in subset.relationships]
            assert indexes == sorted(indexes)

    def test_empty_relationships(self) -> None:
        visible, held_out = split_relationships(RelationshipSet(), holdout_fraction=0.5, seed=1)
        assert visible == RelationshipSet()
        assert held_out == RelationshipSet()

    def test_custom_kinds(self) -> None:
        relationships = RelationshipSet(
            relationships=tuple(rel("doc-a", f"t{i}", kind="see-also") for i in range(4))
        )
        _, held_out = split_relationships(
            relationships, holdout_fraction=0.5, seed=1, kinds=("see-also",)
        )
        assert len(held_out.relationships) == 2


class TestDegreeBucket:
    @pytest.mark.parametrize(
        ("degree", "bucket"),
        [(0, "1"), (1, "1"), (2, "2-4"), (4, "2-4"), (5, "5+"), (100, "5+")],
    )
    def test_boundaries(self, degree: int, bucket: str) -> None:
        assert degree_bucket(degree) == bucket
