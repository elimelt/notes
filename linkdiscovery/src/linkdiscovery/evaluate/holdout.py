"""Weak supervision from existing links: stratified holdout splitting.

Existing links provide useful but biased positive examples (SPEC design
principle 5). The evaluation harness hides a stratified sample of them, runs
discovery as if those links were absent, and measures how well the pipeline
rediscovers current linking behavior. Stratification is by source-document
out-degree so hub documents are neither over- nor under-sampled.
"""

from __future__ import annotations

import random
from collections import Counter
from typing import TYPE_CHECKING

from linkdiscovery.contracts.documents import RelationshipSet

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["DEGREE_BUCKETS", "degree_bucket", "split_relationships"]

DEGREE_BUCKETS = ("1", "2-4", "5+")
"""Out-degree bucket names, ordered from sparse to hub."""


def degree_bucket(degree: int) -> str:
    """Bucket a source document's out-degree: ``"1"`` (<= 1), ``"2-4"``, ``"5+"``.

    Degree zero maps to ``"1"``: a document whose only links were all hidden
    still belongs with the sparse documents.
    """
    if degree <= 1:
        return "1"
    if degree <= 4:  # noqa: PLR2004 - bucket boundary from the SPEC breakdown
        return "2-4"
    return "5+"


def split_relationships(
    relationships: RelationshipSet,
    *,
    holdout_fraction: float,
    seed: int,
    kinds: Sequence[str] = ("explicit-link",),
) -> tuple[RelationshipSet, RelationshipSet]:
    """Split relationships into ``(visible, held_out)`` sets, deterministically.

    Only relationships whose ``kind`` is in ``kinds`` are eligible for
    holdout; every other kind always stays visible (they are weaker graph
    signals, not link-recovery targets). Eligible relationships are
    stratified by their source document's out-degree (counted over eligible
    relationships) into the :data:`DEGREE_BUCKETS`, and
    ``round(holdout_fraction * len(bucket))`` members of each bucket are
    hidden using ``random.Random(seed)``, so the same inputs and seed always
    produce the same split. Relative input order is preserved in both
    outputs.

    Raises ``ValueError`` unless ``0 < holdout_fraction < 1``: holding out
    nothing or everything makes recovery metrics meaningless.
    """
    if not 0.0 < holdout_fraction < 1.0:
        raise ValueError(
            f"holdout_fraction must be in the open interval (0, 1), got {holdout_fraction}"
        )
    items = relationships.relationships
    kind_set = frozenset(kinds)
    eligible = [index for index, rel in enumerate(items) if rel.kind in kind_set]
    out_degree = Counter(items[index].source_id for index in eligible)
    buckets: dict[str, list[int]] = {name: [] for name in DEGREE_BUCKETS}
    for index in eligible:
        buckets[degree_bucket(out_degree[items[index].source_id])].append(index)

    rng = random.Random(seed)
    held: set[int] = set()
    for name in DEGREE_BUCKETS:
        members = buckets[name]
        count = round(holdout_fraction * len(members))
        if count > 0:
            held.update(rng.sample(members, min(count, len(members))))

    visible = tuple(rel for index, rel in enumerate(items) if index not in held)
    held_out = tuple(rel for index, rel in enumerate(items) if index in held)
    return RelationshipSet(relationships=visible), RelationshipSet(relationships=held_out)
