"""Training data assembly, PU discipline, losses, and loops (Architecture A).

Implements SPEC-INLINE-LINKING §5 (Q15-16), §6, and §10 on top of the frozen
encoder of :mod:`linkdiscovery.inline.encode` and the heads of
:mod:`linkdiscovery.inline.heads`.

Supervision routing (audit tiers, §4/§5):

- **Tier A** -> positive for *all* heads.
- **Tier B** -> positive for retrieval and reranker only.
- **Tier C** -> positive for retrieval ONLY (graph supervision; never fed to
  the naturalness head).
- **Tier D** -> negative: a naturalness negative and an explicit reranker
  negative pair (span with the wrong target); never a retrieval positive.
- **Unlinked candidate spans are UNLABELED, not negative** (the PU hazard of
  §5 Q16). They enter the naturalness head as pseudo-negatives weighted by
  the class prior ``pi`` (option (a), config default 0.05), and
  :func:`confirmed_negative_mask` implements option (b): a pseudo-negative
  keeps *full* weight only when its precomputed best-target score falls
  below a low threshold (a confidently-unrelated span).

Losses (§6):

- Naturalness (Q21): weighted per-span BCE plus a listwise softmax auxiliary
  over the candidate spans of each group (region/document).
- Retrieval (Q22): full-catalog cross-entropy — the InfoNCE degenerate case
  where the softmax runs over every target each step — with mined hard
  negatives upweighted inside the softmax.
- Reranker: listwise cross-entropy over each retrieved candidate list (one
  positive versus mined negatives at the §10 ratio of 1:4-8, hard negatives
  a minority), plus plain BCE on Tier-D wrong-target pairs.

Dimensional contract: target document/section vectors must live in the
encoder hidden space (``target_dim == hidden_size``), because hard-negative
mining and the reranker interaction features compare the span's mean-pooled
interior block against target vectors directly.
"""

from __future__ import annotations

import importlib
import math
import random
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Final

import numpy as np

from linkdiscovery.errors import ConfigError, ContractError, EmbeddingRuntimeError
from linkdiscovery.fingerprint import fingerprint
from linkdiscovery.inline.encode import span_representation_dim
from linkdiscovery.inline.heads import (
    NaturalnessConfig,
    RerankerConfig,
    RetrievalConfig,
    TrainedHeads,
    build_naturalness_head,
    build_pair_features,
    build_reranker_head,
    build_retrieval_head,
    reranker_input_dim,
    retrieval_logits,
)
from linkdiscovery.inline.records import Tier

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

    from numpy.typing import NDArray

    from linkdiscovery.inline.records import AuditLabel, AuditSample, SpanCandidate

__all__ = [
    "DEFAULT_PAIR_FEATURE_NAMES",
    "SpanRepTable",
    "TargetCatalog",
    "TrainConfig",
    "TrainingData",
    "TrainingExample",
    "build_training_data",
    "confirmed_negative_mask",
    "default_pair_hand_features",
    "mine_hard_negatives",
    "naturalness_training_arrays",
    "reranker_positive_examples",
    "retrieval_training_arrays",
    "train_heads",
]

DEFAULT_PAIR_FEATURE_NAMES: Final = ("interior_target_cosine",)
"""Hand pair-feature order used by the trainer when building reranker rows."""

_RETRIEVAL_POSITIVE_TIERS: Final = frozenset({Tier.A, Tier.B, Tier.C})
_RERANKER_POSITIVE_TIERS: Final = frozenset({Tier.A, Tier.B})
_TIER_BADNESS: Final = {Tier.A: 0, Tier.B: 1, Tier.C: 2, Tier.D: 3}
_POSITIVE_LABEL_THRESHOLD: Final = 0.5

_INSTALL_HINT = (
    "install the optional embedding dependencies with: pip install 'linkdiscovery[embeddings]'"
)


def _require_torch() -> Any:
    """Import torch lazily, or raise an actionable error naming the extra."""
    try:
        return importlib.import_module("torch")
    except ImportError as exc:
        raise EmbeddingRuntimeError(
            f"training the inline-link heads requires the 'torch' package, which is not "
            f"installed; {_INSTALL_HINT}"
        ) from exc


@dataclass(frozen=True, slots=True)
class TrainConfig:
    """Hyperparameters for :func:`train_heads` (spec §6, §10 starting points).

    ``pi`` is the PU class prior weighting unlabeled pseudo-negatives in the
    naturalness loss; ``negative_ratio`` is negatives-per-positive for the
    reranker (§10: 1:4-8); ``hard_negative_count`` bounds how many of those
    are mined (hard negatives stay a minority per RocketQA);
    ``hard_negative_weight`` upweights mined negatives inside the retrieval
    softmax. ``device`` is ``"cpu"`` or ``"mps"`` (any torch device string
    with those prefixes, or ``"cuda"``, is accepted).
    """

    lr: float = 1e-3
    epochs: int = 30
    batch_size: int = 64
    pi: float = 0.05
    negative_ratio: int = 6
    hard_negative_count: int = 2
    hard_negative_weight: float = 2.0
    listwise_weight: float = 0.5
    projection_dim: int = 256
    naturalness_hidden: int = 128
    reranker_hidden: int = 256
    device: str = "cpu"

    def __post_init__(self) -> None:
        if self.lr <= 0:
            raise ConfigError(f"TrainConfig: lr must be > 0, got {self.lr}")
        if self.epochs < 0:
            raise ConfigError(f"TrainConfig: epochs must be >= 0, got {self.epochs}")
        if self.batch_size < 1:
            raise ConfigError(f"TrainConfig: batch_size must be >= 1, got {self.batch_size}")
        if not 0 < self.pi <= 1:
            raise ConfigError(f"TrainConfig: pi must be in (0, 1], got {self.pi}")
        if self.negative_ratio < 1:
            raise ConfigError(
                f"TrainConfig: negative_ratio must be >= 1, got {self.negative_ratio}"
            )
        if self.hard_negative_count < 0:
            raise ConfigError(
                f"TrainConfig: hard_negative_count must be >= 0, got {self.hard_negative_count}"
            )
        if self.hard_negative_weight <= 0:
            raise ConfigError(
                f"TrainConfig: hard_negative_weight must be > 0, got {self.hard_negative_weight}"
            )
        if self.listwise_weight < 0:
            raise ConfigError(
                f"TrainConfig: listwise_weight must be >= 0, got {self.listwise_weight}"
            )
        if min(self.projection_dim, self.naturalness_hidden, self.reranker_hidden) < 1:
            raise ConfigError("TrainConfig: all layer dimensions must be >= 1")
        if not self.device.startswith(("cpu", "mps", "cuda")):
            raise ConfigError(
                f"TrainConfig: device must start with 'cpu', 'mps', or 'cuda', got {self.device!r}"
            )

    def fingerprint(self) -> str:
        """Deterministic fingerprint of every hyperparameter."""
        return fingerprint(asdict(self))


class SpanRepTable:
    """Span representations keyed by audit-item or candidate ID.

    Validates every representation against the fixed layout of
    :func:`~linkdiscovery.inline.encode.span_representation`
    (``span_representation_dim(hidden_size, len(feature_names))`` wide) and
    carries the encoder fingerprint and hand-feature names that become part
    of trained-head identity.
    """

    __slots__ = ("_encoder_fingerprint", "_feature_names", "_hidden_size", "_reps")

    def __init__(
        self,
        reps: Mapping[str, NDArray[np.float32]],
        *,
        hidden_size: int,
        encoder_fingerprint: str,
        feature_names: tuple[str, ...] = (),
    ) -> None:
        """Validate widths and freeze the representations."""
        expected = span_representation_dim(hidden_size, len(feature_names))
        prepared: dict[str, NDArray[np.float32]] = {}
        for key, rep in reps.items():
            vector = np.ascontiguousarray(rep, dtype=np.float32)
            if vector.ndim != 1 or vector.shape[0] != expected:
                raise ContractError(
                    f"SpanRepTable: representation for {key!r} must be a 1-D vector of "
                    f"width {expected} (hidden_size {hidden_size}, {len(feature_names)} "
                    f"hand features), got shape {tuple(vector.shape)}"
                )
            vector.setflags(write=False)
            prepared[key] = vector
        self._reps = prepared
        self._hidden_size = hidden_size
        self._encoder_fingerprint = encoder_fingerprint
        self._feature_names = feature_names

    @property
    def hidden_size(self) -> int:
        """Encoder hidden width underlying every representation."""
        return self._hidden_size

    @property
    def encoder_fingerprint(self) -> str:
        """Fingerprint of the frozen encoder that produced the representations."""
        return self._encoder_fingerprint

    @property
    def feature_names(self) -> tuple[str, ...]:
        """Hand-feature names, in the order they were appended."""
        return self._feature_names

    @property
    def dim(self) -> int:
        """Width of every representation."""
        return span_representation_dim(self._hidden_size, len(self._feature_names))

    def __len__(self) -> int:
        return len(self._reps)

    def __contains__(self, key: object) -> bool:
        return key in self._reps

    def rep_for(self, key: str) -> NDArray[np.float32]:
        """The representation for ``key``; missing keys are a contract error."""
        rep = self._reps.get(key)
        if rep is None:
            raise ContractError(
                f"SpanRepTable: no span representation for {key!r}; every labeled audit "
                "item and candidate span passed to build_training_data must have one"
            )
        return rep


class TargetCatalog:
    """The frozen closed-world target catalog: one row per note.

    ``matrix`` holds document-level vectors; ``section_matrix`` holds each
    target's best section vector for the reranker (defaults to the document
    vectors when section granularity is unavailable). Vectors are frozen
    encoder output — they are never trained.
    """

    __slots__ = ("_document_ids", "_matrix", "_row_by_id", "_section_matrix")

    def __init__(
        self,
        document_ids: Sequence[str],
        matrix: NDArray[np.float32],
        section_matrix: NDArray[np.float32] | None = None,
    ) -> None:
        """Validate alignment and freeze both matrices."""
        prepared = np.ascontiguousarray(matrix, dtype=np.float32)
        if prepared.ndim != 2 or prepared.shape[0] != len(document_ids):  # noqa: PLR2004
            raise ContractError(
                f"TargetCatalog: matrix must be 2-D with one row per document id, got "
                f"shape {tuple(prepared.shape)} for {len(document_ids)} ids"
            )
        sections = (
            prepared
            if section_matrix is None
            else np.ascontiguousarray(section_matrix, dtype=np.float32)
        )
        if sections.shape != prepared.shape:
            raise ContractError(
                f"TargetCatalog: section_matrix shape {tuple(sections.shape)} must match "
                f"matrix shape {tuple(prepared.shape)}"
            )
        prepared.setflags(write=False)
        sections.setflags(write=False)
        self._document_ids = tuple(document_ids)
        self._row_by_id = {doc_id: row for row, doc_id in enumerate(self._document_ids)}
        if len(self._row_by_id) != len(self._document_ids):
            raise ContractError("TargetCatalog: duplicate target document ids")
        self._matrix = prepared
        self._section_matrix = sections

    @property
    def document_ids(self) -> tuple[str, ...]:
        """Target document IDs in row order."""
        return self._document_ids

    @property
    def matrix(self) -> NDArray[np.float32]:
        """Read-only ``(n_targets, dimensions)`` document-vector matrix."""
        return self._matrix

    @property
    def section_matrix(self) -> NDArray[np.float32]:
        """Read-only per-target section-best vectors (same shape as ``matrix``)."""
        return self._section_matrix

    @property
    def dimensions(self) -> int:
        """Vector dimensionality."""
        return int(self._matrix.shape[1])

    def __len__(self) -> int:
        return len(self._document_ids)

    def index_for(self, document_id: str) -> int:
        """Row index of ``document_id``; unknown ids are a contract error."""
        row = self._row_by_id.get(document_id)
        if row is None:
            raise ContractError(
                f"TargetCatalog: no target row for document {document_id!r}; every audited "
                "link target must be in the catalog"
            )
        return row


@dataclass(frozen=True, eq=False)
class TrainingExample:
    """One span with its supervision routing, resolved from the audit tiers.

    ``tier`` is ``None`` for unlabeled candidate spans; ``target_index`` is
    ``-1`` when the span has no associated target row.
    ``naturalness_label`` is ``None`` when the span is excluded from the
    naturalness head (Tier B/C). ``pseudo_negative`` marks PU unlabeled
    spans; ``confirmed_negative`` marks pseudo-negatives whose best target
    score fell below the confirmation threshold (RocketQA-style denoising).
    ``group`` is the listwise-softmax grouping key (source document).
    """

    key: str
    document_id: str
    rep: NDArray[np.float32]
    tier: Tier | None
    target_index: int
    naturalness_label: float | None
    pseudo_negative: bool = False
    confirmed_negative: bool = False
    group: str = ""


@dataclass(frozen=True, eq=False)
class TrainingData:
    """Everything :func:`train_heads` needs, resolved and validated."""

    examples: tuple[TrainingExample, ...]
    catalog: TargetCatalog
    encoder_fingerprint: str
    feature_names: tuple[str, ...]
    hidden_size: int


def confirmed_negative_mask(
    best_target_scores: NDArray[np.float32], *, threshold: float
) -> NDArray[np.bool_]:
    """PU option (b): which pseudo-negatives count as *confirmed* negatives.

    A candidate span is confidently unrelated — and therefore kept at full
    weight instead of the class-prior weight ``pi`` — only when its best
    (precomputed) target score is below ``threshold`` (SPEC-INLINE-LINKING
    §5 Q16; the RocketQA denoising discipline). Everything else stays an
    unlabeled pseudo-negative.
    """
    scores = np.asarray(best_target_scores, dtype=np.float32)
    mask: NDArray[np.bool_] = scores < threshold
    return mask


def _consensus_tier(labels: Sequence[AuditLabel]) -> Tier:
    """Majority tier over one item's labels; ties resolve to the worse tier."""
    counts: dict[Tier, int] = {}
    for label in labels:
        counts[label.tier] = counts.get(label.tier, 0) + 1
    top = max(counts.values())
    tied = [tier for tier, count in counts.items() if count == top]
    return max(tied, key=lambda tier: _TIER_BADNESS[tier])


def _naturalness_label_for(tier: Tier) -> float | None:
    """Tier routing for the naturalness head: A positive, D negative, B/C excluded."""
    if tier is Tier.A:
        return 1.0
    if tier is Tier.D:
        return 0.0
    return None


def _labeled_examples(
    labels: Sequence[AuditLabel],
    sample: AuditSample,
    reps: SpanRepTable,
    catalog: TargetCatalog,
) -> tuple[list[TrainingExample], set[tuple[str, int, int]]]:
    """Resolve audit labels into examples plus the set of labeled span keys."""
    items_by_id = {item.id: item for item in sample.items}
    by_item: dict[str, dict[str, AuditLabel]] = {}
    for label in labels:
        if label.item_id in items_by_id:
            by_item.setdefault(label.item_id, {})[label.annotator] = label
    examples: list[TrainingExample] = []
    labeled_spans: set[tuple[str, int, int]] = set()
    for item_id in sorted(by_item):
        item = items_by_id[item_id]
        tier = _consensus_tier(tuple(by_item[item_id].values()))
        examples.append(
            TrainingExample(
                key=item_id,
                document_id=item.source_document_id,
                rep=reps.rep_for(item_id),
                tier=tier,
                target_index=catalog.index_for(item.target_document_id),
                naturalness_label=_naturalness_label_for(tier),
                group=item.source_document_id,
            )
        )
        if item.source_span is not None:
            labeled_spans.add(
                (item.source_document_id, item.source_span.start, item.source_span.end)
            )
    return examples, labeled_spans


def _unlabeled_examples(
    candidates_by_doc: Mapping[str, Sequence[SpanCandidate]],
    labeled_spans: set[tuple[str, int, int]],
    reps: SpanRepTable,
    *,
    best_target_scores: Mapping[str, float] | None,
    confirmed_negative_threshold: float,
) -> list[TrainingExample]:
    """Unlabeled candidate spans as PU pseudo-negatives for the naturalness head."""
    examples: list[TrainingExample] = []
    for document_id in sorted(candidates_by_doc):
        for candidate in candidates_by_doc[document_id]:
            span_key = (candidate.document_id, candidate.span.start, candidate.span.end)
            if span_key in labeled_spans:
                continue
            confirmed = False
            if best_target_scores is not None and candidate.id in best_target_scores:
                score = np.asarray([best_target_scores[candidate.id]], dtype=np.float32)
                confirmed = bool(
                    confirmed_negative_mask(score, threshold=confirmed_negative_threshold)[0]
                )
            examples.append(
                TrainingExample(
                    key=candidate.id,
                    document_id=candidate.document_id,
                    rep=reps.rep_for(candidate.id),
                    tier=None,
                    target_index=-1,
                    naturalness_label=0.0,
                    pseudo_negative=True,
                    confirmed_negative=confirmed,
                    group=candidate.document_id,
                )
            )
    return examples


def build_training_data(
    labels: Sequence[AuditLabel],
    sample: AuditSample,
    candidates_by_doc: Mapping[str, Sequence[SpanCandidate]],
    *,
    reps: SpanRepTable,
    catalog: TargetCatalog,
    best_target_scores: Mapping[str, float] | None = None,
    confirmed_negative_threshold: float = 0.2,
) -> TrainingData:
    """Assemble tier-routed training examples from audit labels + candidates.

    Consensus per audit item is the majority tier over its labels (one label
    per annotator, later labels replacing earlier ones; ties resolve to the
    worse tier — the same pessimistic rule as the audit report). Labels whose
    item is not in ``sample`` are ignored. Candidate spans that coincide with
    a labeled item's span (same document and character range) are dropped so
    a span is never both labeled and pseudo-negative.

    ``best_target_scores`` optionally maps candidate IDs to a precomputed
    best-target score (for example the frozen bi-encoder's top cosine);
    candidates scoring below ``confirmed_negative_threshold`` become
    *confirmed* negatives at full weight (:func:`confirmed_negative_mask`),
    everything else stays a ``pi``-weighted pseudo-negative.

    Raises ``ContractError`` when the catalog vectors are not in the encoder
    hidden space (``catalog.dimensions != reps.hidden_size``), because
    hard-negative mining and reranker interaction features require them to be
    comparable.
    """
    if catalog.dimensions != reps.hidden_size:
        raise ContractError(
            f"build_training_data: target vectors must live in the encoder hidden space; "
            f"catalog dimensions {catalog.dimensions} != encoder hidden size "
            f"{reps.hidden_size}"
        )
    examples, labeled_spans = _labeled_examples(labels, sample, reps, catalog)
    examples.extend(
        _unlabeled_examples(
            candidates_by_doc,
            labeled_spans,
            reps,
            best_target_scores=best_target_scores,
            confirmed_negative_threshold=confirmed_negative_threshold,
        )
    )
    return TrainingData(
        examples=tuple(examples),
        catalog=catalog,
        encoder_fingerprint=reps.encoder_fingerprint,
        feature_names=reps.feature_names,
        hidden_size=reps.hidden_size,
    )


def naturalness_training_arrays(
    data: TrainingData, *, pi: float
) -> tuple[NDArray[np.float32], NDArray[np.float32], NDArray[np.float32], tuple[str, ...]]:
    """(reps, labels, weights, groups) for the naturalness head.

    Rows are Tier A positives, Tier D negatives, and PU pseudo-negatives.
    Weights: 1.0 for labeled rows and confirmed negatives; the class prior
    ``pi`` for unconfirmed pseudo-negatives (SPEC-INLINE-LINKING §5 Q16
    option (a)). Tier B/C rows never appear here.
    """
    rows = [example for example in data.examples if example.naturalness_label is not None]
    if not rows:
        empty = np.zeros((0,), dtype=np.float32)
        return np.zeros((0, 0), dtype=np.float32), empty, empty, ()
    reps = np.stack([example.rep for example in rows]).astype(np.float32)
    labels = np.asarray(
        [float(example.naturalness_label or 0.0) for example in rows], dtype=np.float32
    )
    weights = np.asarray(
        [
            pi if example.pseudo_negative and not example.confirmed_negative else 1.0
            for example in rows
        ],
        dtype=np.float32,
    )
    groups = tuple(example.group for example in rows)
    return reps, labels, weights, groups


def retrieval_training_arrays(
    data: TrainingData,
) -> tuple[NDArray[np.float32], NDArray[np.int64]]:
    """(reps, positive target rows) for the retrieval head: Tiers A, B, and C."""
    rows = [example for example in data.examples if example.tier in _RETRIEVAL_POSITIVE_TIERS]
    if not rows:
        return np.zeros((0, 0), dtype=np.float32), np.zeros((0,), dtype=np.int64)
    reps = np.stack([example.rep for example in rows]).astype(np.float32)
    positives = np.asarray([example.target_index for example in rows], dtype=np.int64)
    return reps, positives


def reranker_positive_examples(data: TrainingData) -> tuple[TrainingExample, ...]:
    """Reranker positives: Tier A and B only (Tier C is graph supervision)."""
    return tuple(example for example in data.examples if example.tier in _RERANKER_POSITIVE_TIERS)


def mine_hard_negatives(
    query_vectors: NDArray[np.float32],
    target_matrix: NDArray[np.float32],
    positives: NDArray[np.int64],
    *,
    k: int,
    exclude: Sequence[int] = (),
) -> NDArray[np.int64]:
    """ANCE-lite mining: the ``k`` nearest non-positive targets per query.

    ``query_vectors`` must live in the same space as ``target_matrix`` (for
    span queries, pass the mean-pooled interior block of the span
    representation). Similarity is the dot product; each row's own positive
    and every globally ``exclude``-d index are removed before taking the top
    ``k``. Ties break by target index, so mining is deterministic.

    Mined hard negatives are *candidates*, not truths: per RocketQA they may
    contain false negatives (unlabeled positives). Denoising is applied
    before training via :func:`confirmed_negative_mask` — only spans whose
    best target score is confidently low are trusted at full weight.

    Raises ``ContractError`` on dimension mismatches or when ``k`` exceeds
    the number of available non-positive targets.
    """
    queries = np.ascontiguousarray(query_vectors, dtype=np.float32)
    targets = np.ascontiguousarray(target_matrix, dtype=np.float32)
    if queries.ndim != 2 or targets.ndim != 2 or queries.shape[1] != targets.shape[1]:  # noqa: PLR2004
        raise ContractError(
            f"mine_hard_negatives: query vectors {tuple(queries.shape)} and target matrix "
            f"{tuple(targets.shape)} must both be 2-D with equal widths"
        )
    rows = np.asarray(positives, dtype=np.int64)
    if rows.shape != (queries.shape[0],):
        raise ContractError(
            f"mine_hard_negatives: positives must have one entry per query, got shape "
            f"{tuple(rows.shape)} for {queries.shape[0]} queries"
        )
    if rows.size and (int(rows.min()) < 0 or int(rows.max()) >= targets.shape[0]):
        raise ContractError(
            f"mine_hard_negatives: positive indices must be within [0, {targets.shape[0]}), "
            f"got values in [{int(rows.min())}, {int(rows.max())}]"
        )
    excluded = {int(index) for index in exclude}
    unavailable = max(len(excluded | {int(row)}) for row in rows) if rows.size else len(excluded)
    available = targets.shape[0] - unavailable
    if k < 0 or k > available:
        raise ContractError(
            f"mine_hard_negatives: k must be between 0 and {available} "
            f"(targets minus the positive and {len(excluded)} excluded), got {k}"
        )
    if k == 0 or queries.shape[0] == 0:
        return np.zeros((queries.shape[0], 0), dtype=np.int64)
    similarities = queries @ targets.T
    if excluded:
        similarities[:, sorted(excluded)] = -np.inf
    similarities[np.arange(queries.shape[0]), rows] = -np.inf
    order = np.argsort(-similarities, axis=1, kind="stable")
    return np.ascontiguousarray(order[:, :k], dtype=np.int64)


def default_pair_hand_features(
    span_rep: NDArray[np.float32], target_vector: NDArray[np.float32], *, hidden_size: int
) -> tuple[float, ...]:
    """The trainer's hand pair features, ordered as DEFAULT_PAIR_FEATURE_NAMES.

    Currently one feature: the cosine similarity between the span's
    mean-pooled interior block and the target document vector. Inference
    must reproduce this exact ordering when building reranker rows.
    """
    interior = np.asarray(span_rep, dtype=np.float32)[2 * hidden_size : 3 * hidden_size]
    target = np.asarray(target_vector, dtype=np.float32)
    denominator = float(np.linalg.norm(interior)) * float(np.linalg.norm(target)) + 1e-8
    return (float(interior @ target) / denominator,)


def _pair_row(
    span_rep: NDArray[np.float32], target_index: int, data: TrainingData
) -> NDArray[np.float32]:
    """One reranker input row for (span, target) with default hand features."""
    target_vector = data.catalog.matrix[target_index]
    return build_pair_features(
        span_rep,
        target_vector,
        data.catalog.section_matrix[target_index],
        hidden_size=data.hidden_size,
        hand_features=default_pair_hand_features(
            span_rep, target_vector, hidden_size=data.hidden_size
        ),
    )


def _pack_groups(
    keys: Sequence[Any], sizes: Mapping[Any, int], batch_size: int
) -> Iterator[list[Any]]:
    """Pack whole groups into batches of at most ``batch_size`` rows (>=1 group)."""
    batch: list[Any] = []
    rows = 0
    for key in keys:
        size = sizes[key]
        if batch and rows + size > batch_size:
            yield batch
            batch = []
            rows = 0
        batch.append(key)
        rows += size
    if batch:
        yield batch


def _train_naturalness(
    torch: Any, module: Any, data: TrainingData, config: TrainConfig, seed: int
) -> tuple[float, ...]:
    """Weighted BCE + listwise softmax auxiliary (spec §6 Q21)."""
    reps, labels, weights, groups = naturalness_training_arrays(data, pi=config.pi)
    if reps.shape[0] == 0 or config.epochs == 0:
        return ()
    functional = torch.nn.functional
    device = next(module.parameters()).device
    features = torch.from_numpy(reps).to(device)
    targets = torch.from_numpy(labels).to(device)
    row_weights = torch.from_numpy(weights).to(device)
    group_rows: dict[str, list[int]] = {}
    for row, group in enumerate(groups):
        group_rows.setdefault(group, []).append(row)
    sizes = {key: len(rows) for key, rows in group_rows.items()}
    optimizer = torch.optim.Adam(module.parameters(), lr=config.lr)
    rng = random.Random(seed)
    keys = sorted(group_rows)
    history: list[float] = []
    for _ in range(config.epochs):
        rng.shuffle(keys)
        total = 0.0
        count = 0
        for batch_keys in _pack_groups(keys, sizes, config.batch_size):
            rows: list[int] = []
            slices: list[tuple[int, int]] = []
            for key in batch_keys:
                start = len(rows)
                rows.extend(group_rows[key])
                slices.append((start, len(rows)))
            index = torch.tensor(rows, dtype=torch.long, device=device)
            logits = module(features[index]).squeeze(-1)
            batch_targets = targets[index]
            pointwise = functional.binary_cross_entropy_with_logits(
                logits, batch_targets, reduction="none"
            )
            loss = (row_weights[index] * pointwise).mean()
            listwise_terms = []
            for start, end in slices:
                positive = batch_targets[start:end] > _POSITIVE_LABEL_THRESHOLD
                if not bool(positive.any()):
                    continue
                normalizer = torch.logsumexp(logits[start:end], dim=0)
                listwise_terms.append((normalizer - logits[start:end][positive]).mean())
            if listwise_terms:
                loss = loss + config.listwise_weight * torch.stack(listwise_terms).mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += float(loss.detach()) * len(rows)
            count += len(rows)
        history.append(total / count)
    return tuple(history)


def _train_retrieval(
    torch: Any, module: Any, data: TrainingData, config: TrainConfig, seed: int
) -> tuple[float, ...]:
    """Full-catalog cross-entropy with hard-negative upweighting (spec §6 Q22)."""
    reps, positives = retrieval_training_arrays(data)
    if reps.shape[0] == 0 or config.epochs == 0:
        return ()
    functional = torch.nn.functional
    device = next(module.parameters()).device
    n_targets = len(data.catalog)
    k = min(config.hard_negative_count, n_targets - 1)
    log_weight = np.zeros((reps.shape[0], n_targets), dtype=np.float32)
    if k > 0:
        interior = reps[:, 2 * data.hidden_size : 3 * data.hidden_size]
        hard = mine_hard_negatives(interior, data.catalog.matrix, positives, k=k)
        row_index = np.repeat(np.arange(reps.shape[0]), hard.shape[1])
        log_weight[row_index, hard.reshape(-1)] = math.log(config.hard_negative_weight)
    features = torch.from_numpy(reps).to(device)
    # The catalog matrix is a read-only view; copy before handing it to torch.
    targets = torch.from_numpy(data.catalog.matrix.copy()).to(device)
    labels = torch.from_numpy(positives).to(device)
    weights = torch.from_numpy(log_weight).to(device)
    optimizer = torch.optim.Adam(module.parameters(), lr=config.lr)
    rng = random.Random(seed)
    order = list(range(reps.shape[0]))
    history: list[float] = []
    for _ in range(config.epochs):
        rng.shuffle(order)
        total = 0.0
        for start in range(0, len(order), config.batch_size):
            chunk = order[start : start + config.batch_size]
            index = torch.tensor(chunk, dtype=torch.long, device=device)
            logits = retrieval_logits(module, features[index], targets) + weights[index]
            loss = functional.cross_entropy(logits, labels[index])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += float(loss.detach()) * len(chunk)
        history.append(total / len(order))
    return tuple(history)


def _reranker_rows(
    data: TrainingData, config: TrainConfig, seed: int
) -> tuple[list[NDArray[np.float32]], NDArray[np.float32]]:
    """Build reranker groups (positive first) and standalone Tier-D negatives.

    Each Tier A/B positive gets ``negative_ratio`` mined negatives (clamped
    to the catalog size): ``hard_negative_count`` nearest non-positive
    targets plus seeded-random fills, keeping hard negatives a minority per
    spec §10.
    """
    positives = reranker_positive_examples(data)
    n_targets = len(data.catalog)
    ratio = min(config.negative_ratio, n_targets - 1)
    hard_k = min(config.hard_negative_count, ratio)
    hard = np.zeros((len(positives), 0), dtype=np.int64)
    if positives and hard_k > 0:
        interior = np.stack(
            [example.rep[2 * data.hidden_size : 3 * data.hidden_size] for example in positives]
        )
        positive_rows = np.asarray([example.target_index for example in positives], dtype=np.int64)
        hard = mine_hard_negatives(interior, data.catalog.matrix, positive_rows, k=hard_k)
    rng = np.random.default_rng(seed)
    groups: list[NDArray[np.float32]] = []
    for position, example in enumerate(positives):
        negative_indices = [int(index) for index in hard[position]]
        pool = [
            index
            for index in range(n_targets)
            if index != example.target_index and index not in set(negative_indices)
        ]
        n_random = ratio - len(negative_indices)
        if n_random > 0 and pool:
            chosen = rng.choice(len(pool), size=min(n_random, len(pool)), replace=False)
            negative_indices.extend(pool[int(offset)] for offset in np.sort(chosen))
        rows = [_pair_row(example.rep, example.target_index, data)]
        rows.extend(_pair_row(example.rep, index, data) for index in negative_indices)
        groups.append(np.stack(rows).astype(np.float32))
    tier_d_rows = [
        _pair_row(example.rep, example.target_index, data)
        for example in data.examples
        if example.tier is Tier.D
    ]
    span_dim = span_representation_dim(data.hidden_size, len(data.feature_names))
    pair_dim = reranker_input_dim(span_dim, data.hidden_size, len(DEFAULT_PAIR_FEATURE_NAMES))
    negatives = (
        np.stack(tier_d_rows).astype(np.float32)
        if tier_d_rows
        else np.zeros((0, pair_dim), dtype=np.float32)
    )
    return groups, negatives


def _train_reranker(
    torch: Any, module: Any, data: TrainingData, config: TrainConfig, seed: int
) -> tuple[float, ...]:
    """Listwise CE over retrieved lists + BCE on Tier-D wrong-target pairs."""
    groups, negatives = _reranker_rows(data, config, seed)
    if (not groups and negatives.shape[0] == 0) or config.epochs == 0:
        return ()
    functional = torch.nn.functional
    device = next(module.parameters()).device
    group_tensors = [torch.from_numpy(group).to(device) for group in groups]
    negative_tensor = torch.from_numpy(negatives).to(device)
    positive_position = torch.zeros(1, dtype=torch.long, device=device)
    sizes = {index: int(tensor.shape[0]) for index, tensor in enumerate(group_tensors)}
    optimizer = torch.optim.Adam(module.parameters(), lr=config.lr)
    rng = random.Random(seed)
    order = list(range(len(group_tensors)))
    history: list[float] = []
    for _ in range(config.epochs):
        rng.shuffle(order)
        total = 0.0
        count = 0
        for batch in _pack_groups(order, sizes, config.batch_size):
            losses = [
                functional.cross_entropy(
                    module(group_tensors[index]).squeeze(-1).unsqueeze(0), positive_position
                )
                for index in batch
            ]
            loss = torch.stack(losses).mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += float(loss.detach()) * len(batch)
            count += len(batch)
        if negative_tensor.shape[0]:
            logits = module(negative_tensor).squeeze(-1)
            loss = functional.binary_cross_entropy_with_logits(logits, torch.zeros_like(logits))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += float(loss.detach())
            count += 1
        history.append(total / count)
    return tuple(history)


def train_heads(data: TrainingData, *, config: TrainConfig, seed: int) -> TrainedHeads:
    """Train the three Architecture A heads on tier-routed data.

    Deterministic given ``seed`` on CPU: module initialization uses
    ``torch.manual_seed``, all shuffling uses seeded Python/NumPy RNGs, and
    the ops involved have deterministic CPU kernels. Honesty note: on
    ``device="mps"`` some kernels are not guaranteed bit-exact across runs,
    so exact reproducibility is only promised on CPU. With ``epochs=0`` the
    heads are returned freshly initialized (a useful untrained baseline).

    Returns a :class:`~linkdiscovery.inline.heads.TrainedHeads` bundle (moved
    back to CPU, in eval mode) whose metadata records the encoder
    fingerprint, feature names, per-head loss history, and the training
    configuration fingerprint.
    """
    torch = _require_torch()
    torch.manual_seed(seed)
    span_dim = span_representation_dim(data.hidden_size, len(data.feature_names))
    naturalness_config = NaturalnessConfig(input_dim=span_dim, hidden=config.naturalness_hidden)
    retrieval_config = RetrievalConfig(
        query_dim=span_dim,
        target_dim=data.catalog.dimensions,
        projection_dim=config.projection_dim,
    )
    reranker_config = RerankerConfig(
        input_dim=reranker_input_dim(span_dim, data.hidden_size, len(DEFAULT_PAIR_FEATURE_NAMES)),
        hidden=config.reranker_hidden,
    )
    naturalness = build_naturalness_head(naturalness_config, seed=seed)
    retrieval = build_retrieval_head(retrieval_config, seed=seed + 1)
    reranker = build_reranker_head(reranker_config, seed=seed + 2)
    device = torch.device(config.device)
    for module in (naturalness, retrieval, reranker):
        module.to(device)
        module.train()
    loss_history = {
        "naturalness": _train_naturalness(torch, naturalness, data, config, seed),
        "retrieval": _train_retrieval(torch, retrieval, data, config, seed),
        "reranker": _train_reranker(torch, reranker, data, config, seed),
    }
    for module in (naturalness, retrieval, reranker):
        module.to("cpu")
        module.eval()
    return TrainedHeads(
        naturalness=naturalness,
        retrieval=retrieval,
        reranker=reranker,
        naturalness_config=naturalness_config,
        retrieval_config=retrieval_config,
        reranker_config=reranker_config,
        encoder_fingerprint=data.encoder_fingerprint,
        feature_names=data.feature_names,
        hidden_size=data.hidden_size,
        train_config_fingerprint=config.fingerprint(),
        loss_history=loss_history,
    )
