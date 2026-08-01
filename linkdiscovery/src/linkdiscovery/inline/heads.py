"""The three learned heads of Architecture A (SPEC-INLINE-LINKING §2, §6).

Small torch modules trained on top of frozen-encoder span representations:

- **Naturalness head** (Q21): a 2-layer MLP producing one linkability logit
  per candidate span.
- **Retrieval head** (Q22): two linear projections mapping span
  representations and (frozen, precomputed) target document vectors into a
  shared space; the score is a scaled dot product, normalized with a
  **full-catalog softmax** — at ~258 targets the softmax runs over the
  entire catalog every step, so there is no in-batch-negative approximation.
- **Reranker head** (Architecture A's "cross-encoder-style reranker head"):
  an MLP over concatenated ``[span rep; target doc vector; target
  section-best vector; interior x target elementwise product; hand pair
  features]`` (:func:`build_pair_features`).

Torch is imported lazily inside functions so this module (and the package)
imports without the ``embeddings`` extra; constructing or scoring a head
without torch raises :class:`~linkdiscovery.errors.EmbeddingRuntimeError`.
Head configurations are pure-python frozen dataclasses; module init seeds are
explicit. The :class:`TrainedHeads` bundle carries the metadata that pins a
set of weights to one encoder and one training configuration, and its
inference helpers keep torch types out of the public boundary: numpy in,
numpy out.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from linkdiscovery.errors import ContractError, EmbeddingRuntimeError
from linkdiscovery.fingerprint import fingerprint
from linkdiscovery.inline.encode import WIDTH_BUCKET_COUNT

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from numpy.typing import NDArray

__all__ = [
    "NaturalnessConfig",
    "RerankerConfig",
    "RetrievalConfig",
    "TrainedHeads",
    "build_naturalness_head",
    "build_pair_features",
    "build_reranker_head",
    "build_retrieval_head",
    "reranker_input_dim",
    "retrieval_logits",
]

_METADATA_FILE = "metadata.json"
_WEIGHTS_FILE = "weights.pt"
_METADATA_SCHEMA_VERSION = 1

_INSTALL_HINT = (
    "install the optional embedding dependencies with: pip install 'linkdiscovery[embeddings]'"
)


def _require_torch() -> Any:
    """Import torch lazily, or raise an actionable error naming the extra."""
    try:
        return importlib.import_module("torch")
    except ImportError as exc:
        raise EmbeddingRuntimeError(
            f"the learned inline-link heads require the 'torch' package, which is not "
            f"installed; {_INSTALL_HINT}"
        ) from exc


@dataclass(frozen=True, slots=True)
class NaturalnessConfig:
    """Configuration of the naturalness head: a 2-layer MLP to one logit."""

    input_dim: int
    hidden: int = 128

    def __post_init__(self) -> None:
        if self.input_dim < 1 or self.hidden < 1:
            raise ContractError(
                f"NaturalnessConfig: input_dim and hidden must be >= 1, "
                f"got {self.input_dim} and {self.hidden}"
            )


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    """Configuration of the retrieval head: two projections into a shared space."""

    query_dim: int
    target_dim: int
    projection_dim: int = 256

    def __post_init__(self) -> None:
        if self.query_dim < 1 or self.target_dim < 1 or self.projection_dim < 1:
            raise ContractError(
                f"RetrievalConfig: all dimensions must be >= 1, got query_dim="
                f"{self.query_dim}, target_dim={self.target_dim}, "
                f"projection_dim={self.projection_dim}"
            )


@dataclass(frozen=True, slots=True)
class RerankerConfig:
    """Configuration of the reranker head: an MLP over pair features."""

    input_dim: int
    hidden: int = 256

    def __post_init__(self) -> None:
        if self.input_dim < 1 or self.hidden < 1:
            raise ContractError(
                f"RerankerConfig: input_dim and hidden must be >= 1, "
                f"got {self.input_dim} and {self.hidden}"
            )


def _build_mlp(torch: Any, input_dim: int, hidden: int, seed: int) -> Any:
    """A seeded 2-layer MLP producing one logit per row."""
    torch.manual_seed(seed)
    return torch.nn.Sequential(
        torch.nn.Linear(input_dim, hidden),
        torch.nn.ReLU(),
        torch.nn.Linear(hidden, 1),
    )


def build_naturalness_head(config: NaturalnessConfig, *, seed: int = 0) -> Any:
    """Build the naturalness MLP (``(n, input_dim) -> (n, 1)`` logits)."""
    return _build_mlp(_require_torch(), config.input_dim, config.hidden, seed)


def build_reranker_head(config: RerankerConfig, *, seed: int = 0) -> Any:
    """Build the reranker MLP (``(n, input_dim) -> (n, 1)`` logits)."""
    return _build_mlp(_require_torch(), config.input_dim, config.hidden, seed)


def build_retrieval_head(config: RetrievalConfig, *, seed: int = 0) -> Any:
    """Build the retrieval head: bias-free query/target projections.

    The head is a ``torch.nn.ModuleDict`` with ``"query"`` and ``"target"``
    linear projections into ``projection_dim``; :func:`retrieval_logits`
    computes the scaled-dot-product score matrix.
    """
    torch = _require_torch()
    torch.manual_seed(seed)
    return torch.nn.ModuleDict(
        {
            "query": torch.nn.Linear(config.query_dim, config.projection_dim, bias=False),
            "target": torch.nn.Linear(config.target_dim, config.projection_dim, bias=False),
        }
    )


def retrieval_logits(head: Any, query: Any, targets: Any) -> Any:
    """Scaled dot-product logits ``(n_queries, n_targets)`` (torch tensors).

    ``softmax`` over the last axis gives the full-catalog distribution of
    SPEC-INLINE-LINKING §6 (Q22): at a few hundred targets the caller passes
    the *entire* target matrix, so the normalizer is exact — no in-batch
    negative approximation.
    """
    projected_query = head["query"](query)
    projected_targets = head["target"](targets)
    scale = math.sqrt(projected_query.shape[-1])
    return projected_query @ projected_targets.transpose(0, 1) / scale


def reranker_input_dim(span_dim: int, hidden_size: int, hand_feature_count: int) -> int:
    """Dimensionality of :func:`build_pair_features` output.

    ``span_dim`` (the span representation) + ``hidden_size`` (target doc
    vector) + ``hidden_size`` (target section-best vector) + ``hidden_size``
    (interior x target elementwise product) + ``hand_feature_count``.
    """
    if span_dim < 1 or hidden_size < 1 or hand_feature_count < 0:
        raise ContractError(
            "reranker_input_dim: span_dim and hidden_size must be >= 1 and "
            f"hand_feature_count must be >= 0, got {span_dim}, {hidden_size}, "
            f"{hand_feature_count}"
        )
    return span_dim + 3 * hidden_size + hand_feature_count


def _pair_vector(array: NDArray[np.float32], expected: int, name: str) -> NDArray[np.float32]:
    """Validate one 1-D float32 vector of an exact width."""
    vector = np.ascontiguousarray(array, dtype=np.float32)
    if vector.ndim != 1 or vector.shape[0] != expected:
        raise ContractError(
            f"build_pair_features: {name} must be a 1-D vector of width {expected}, "
            f"got shape {tuple(vector.shape)}"
        )
    return vector


def build_pair_features(
    span_rep: NDArray[np.float32],
    target_vector: NDArray[np.float32],
    section_vector: NDArray[np.float32],
    *,
    hidden_size: int,
    hand_features: Sequence[float] = (),
) -> NDArray[np.float32]:
    """Assemble one reranker input row with a fixed feature ordering.

    Layout: ``[span_rep; target_vector; section_vector;
    interior_mean * target_vector; hand_features]`` where ``interior_mean``
    is the mean-pooled span block at ``span_rep[2 * hidden_size : 3 *
    hidden_size]`` (the layout fixed by
    :func:`~linkdiscovery.inline.encode.span_representation`). Target and
    section vectors must live in the encoder hidden space
    (``hidden_size`` wide), which is what makes the elementwise interaction
    term well-defined. Raises ``ContractError`` on any width mismatch.
    """
    span = np.ascontiguousarray(span_rep, dtype=np.float32)
    minimum_span_dim = 3 * hidden_size + WIDTH_BUCKET_COUNT
    if span.ndim != 1 or span.shape[0] < minimum_span_dim:
        raise ContractError(
            f"build_pair_features: span_rep must be a 1-D span representation of at "
            f"least {minimum_span_dim} floats for hidden_size {hidden_size}, got shape "
            f"{tuple(span.shape)}"
        )
    target = _pair_vector(target_vector, hidden_size, "target_vector")
    section = _pair_vector(section_vector, hidden_size, "section_vector")
    interior = span[2 * hidden_size : 3 * hidden_size]
    hand = np.asarray(tuple(hand_features), dtype=np.float32)
    row = np.concatenate([span, target, section, interior * target, hand])
    return np.ascontiguousarray(row, dtype=np.float32)


def _as_matrix(array: NDArray[np.float32], expected_dim: int, context: str) -> NDArray[np.float32]:
    """Validate a 2-D float32 matrix with an exact column count."""
    matrix = np.ascontiguousarray(array, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] != expected_dim:  # noqa: PLR2004 - 2-D check
        raise ContractError(
            f"{context}: expected a 2-D float array with {expected_dim} columns, "
            f"got shape {tuple(matrix.shape)}"
        )
    if not matrix.flags.writeable:
        # torch.from_numpy cannot wrap read-only arrays (frozen catalog views).
        matrix = matrix.copy()
    return matrix


def _parse_metadata(data: Any, path_text: str) -> dict[str, Any]:
    """Parse the JSON sidecar into constructor-ready values, strictly."""
    if not isinstance(data, dict):
        raise ContractError(f"trained-heads metadata at {path_text} must be a JSON object")
    try:
        return {
            "encoder_fingerprint": str(data["encoder_fingerprint"]),
            "feature_names": tuple(str(name) for name in data["feature_names"]),
            "hidden_size": int(data["hidden_size"]),
            "naturalness_config": NaturalnessConfig(**data["naturalness_config"]),
            "retrieval_config": RetrievalConfig(**data["retrieval_config"]),
            "reranker_config": RerankerConfig(**data["reranker_config"]),
            "train_config_fingerprint": str(data["train_config_fingerprint"]),
            "loss_history": {
                str(head): tuple(float(value) for value in losses)
                for head, losses in data["loss_history"].items()
            },
            "model_version": str(data["model_version"]),
        }
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ContractError(
            f"trained-heads metadata at {path_text} is invalid or incomplete: {exc}"
        ) from exc


@dataclass(eq=False)
class TrainedHeads:
    """The three trained heads plus the metadata that pins their identity.

    ``model_version`` fingerprints everything — encoder fingerprint, feature
    names, head configurations, training-config fingerprint, loss history,
    and the trained weights themselves — so two bundles score identically if
    and only if their versions match. :meth:`save` writes a directory with a
    ``weights_only``-loadable state-dict file and a JSON metadata sidecar;
    :meth:`load` refuses (``ContractError``) when the caller's encoder
    fingerprint does not match the one the heads were trained on.
    """

    naturalness: Any
    retrieval: Any
    reranker: Any
    naturalness_config: NaturalnessConfig
    retrieval_config: RetrievalConfig
    reranker_config: RerankerConfig
    encoder_fingerprint: str
    feature_names: tuple[str, ...]
    hidden_size: int
    train_config_fingerprint: str
    loss_history: dict[str, tuple[float, ...]] = field(default_factory=dict)

    def _modules_by_name(self) -> tuple[tuple[str, Any], ...]:
        return (
            ("naturalness", self.naturalness),
            ("retrieval", self.retrieval),
            ("reranker", self.reranker),
        )

    def _metadata(self) -> dict[str, Any]:
        """JSON-safe metadata, excluding ``model_version`` itself."""
        return {
            "schema_version": _METADATA_SCHEMA_VERSION,
            "encoder_fingerprint": self.encoder_fingerprint,
            "feature_names": list(self.feature_names),
            "hidden_size": self.hidden_size,
            "naturalness_config": asdict(self.naturalness_config),
            "retrieval_config": asdict(self.retrieval_config),
            "reranker_config": asdict(self.reranker_config),
            "train_config_fingerprint": self.train_config_fingerprint,
            "loss_history": {head: list(losses) for head, losses in self.loss_history.items()},
        }

    def _weights_fingerprint(self) -> str:
        """Deterministic digest of every parameter tensor, in a fixed order."""
        digest = hashlib.sha256()
        for name, module in self._modules_by_name():
            state = module.state_dict()
            for key in sorted(state):
                tensor = state[key].detach().to("cpu").contiguous()
                array = tensor.numpy()
                digest.update(f"{name}.{key}:{array.dtype}:{array.shape}".encode())
                digest.update(array.tobytes())
        return f"sha256:{digest.hexdigest()}"

    @property
    def model_version(self) -> str:
        """Fingerprint of the metadata and the trained weights together."""
        return fingerprint({"metadata": self._metadata(), "weights": self._weights_fingerprint()})

    def save(self, path: Path) -> None:
        """Write ``weights.pt`` + ``metadata.json`` into directory ``path``.

        The weights file holds plain state dicts (tensors only), so it loads
        under ``torch.load(..., weights_only=True)``.
        """
        torch = _require_torch()
        path.mkdir(parents=True, exist_ok=True)
        torch.save(
            {name: module.state_dict() for name, module in self._modules_by_name()},
            path / _WEIGHTS_FILE,
        )
        metadata = self._metadata()
        metadata["model_version"] = self.model_version
        (path / _METADATA_FILE).write_text(
            json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: Path, *, encoder_fingerprint: str | None = None) -> TrainedHeads:
        """Load a bundle written by :meth:`save`.

        When ``encoder_fingerprint`` is given it must equal the fingerprint
        recorded at training time; a mismatch raises ``ContractError``
        because heads scored on a different encoder's representations are
        meaningless. Passing ``None`` skips the check (caller takes
        responsibility). Corrupt or incomplete artifacts (missing files,
        invalid JSON, weights that disagree with the recorded
        ``model_version``) also raise ``ContractError``.
        """
        torch = _require_torch()
        metadata_path = path / _METADATA_FILE
        weights_path = path / _WEIGHTS_FILE
        if not metadata_path.is_file() or not weights_path.is_file():
            raise ContractError(
                f"trained-heads directory {str(path)!r} is missing {_METADATA_FILE!r} or "
                f"{_WEIGHTS_FILE!r}; expected a directory written by TrainedHeads.save"
            )
        try:
            raw = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(
                f"trained-heads metadata at {str(metadata_path)!r} is unreadable: {exc}"
            ) from exc
        metadata = _parse_metadata(raw, str(metadata_path))
        if encoder_fingerprint is not None and encoder_fingerprint != str(
            metadata["encoder_fingerprint"]
        ):
            raise ContractError(
                f"trained heads at {str(path)!r} were trained on encoder fingerprint "
                f"{metadata['encoder_fingerprint']!r} but the current encoder fingerprint is "
                f"{encoder_fingerprint!r}; re-train the heads or load them with the encoder "
                "they were trained on"
            )
        naturalness = build_naturalness_head(metadata["naturalness_config"], seed=0)
        retrieval = build_retrieval_head(metadata["retrieval_config"], seed=0)
        reranker = build_reranker_head(metadata["reranker_config"], seed=0)
        try:
            states = torch.load(weights_path, weights_only=True)
            naturalness.load_state_dict(states["naturalness"])
            retrieval.load_state_dict(states["retrieval"])
            reranker.load_state_dict(states["reranker"])
        except Exception as exc:
            raise ContractError(
                f"trained-heads weights at {str(weights_path)!r} are corrupt or do not "
                f"match the recorded head configurations: {exc}"
            ) from exc
        for module in (naturalness, retrieval, reranker):
            module.eval()
        loaded = cls(
            naturalness=naturalness,
            retrieval=retrieval,
            reranker=reranker,
            naturalness_config=metadata["naturalness_config"],
            retrieval_config=metadata["retrieval_config"],
            reranker_config=metadata["reranker_config"],
            encoder_fingerprint=metadata["encoder_fingerprint"],
            feature_names=metadata["feature_names"],
            hidden_size=metadata["hidden_size"],
            train_config_fingerprint=metadata["train_config_fingerprint"],
            loss_history=metadata["loss_history"],
        )
        if loaded.model_version != metadata["model_version"]:
            raise ContractError(
                f"trained heads at {str(path)!r} fail integrity verification: the stored "
                "weights and metadata do not reproduce the recorded model_version; the "
                "artifact is corrupt or was modified after saving"
            )
        return loaded

    def score_naturalness(self, reps: NDArray[np.float32]) -> NDArray[np.float32]:
        """Sigmoid linkability probabilities, shape ``(n_spans,)``.

        ``reps`` is the ``(n_spans, input_dim)`` span-representation matrix;
        numpy in, numpy out — no torch types cross this boundary.
        """
        torch = _require_torch()
        matrix = _as_matrix(reps, self.naturalness_config.input_dim, "score_naturalness")
        with torch.no_grad():
            logits = self.naturalness(torch.from_numpy(matrix)).squeeze(-1)
            probabilities = torch.sigmoid(logits)
        return np.asarray(probabilities.numpy(), dtype=np.float32)

    def score_targets(
        self, reps: NDArray[np.float32], target_matrix: NDArray[np.float32]
    ) -> NDArray[np.float32]:
        """Full-catalog softmax probabilities, shape ``(n_spans, n_targets)``.

        Every row sums to 1: the softmax normalizes over the *entire* target
        matrix passed in (SPEC-INLINE-LINKING §6 Q22).
        """
        torch = _require_torch()
        queries = _as_matrix(reps, self.retrieval_config.query_dim, "score_targets")
        targets = _as_matrix(target_matrix, self.retrieval_config.target_dim, "score_targets")
        with torch.no_grad():
            logits = retrieval_logits(
                self.retrieval, torch.from_numpy(queries), torch.from_numpy(targets)
            )
            probabilities = torch.softmax(logits, dim=-1)
        return np.asarray(probabilities.numpy(), dtype=np.float32)

    def score_pairs(self, pair_features: NDArray[np.float32]) -> NDArray[np.float32]:
        """Sigmoid reranker probabilities, shape ``(n_pairs,)``.

        Rows must follow the :func:`build_pair_features` layout.
        """
        torch = _require_torch()
        matrix = _as_matrix(pair_features, self.reranker_config.input_dim, "score_pairs")
        with torch.no_grad():
            logits = self.reranker(torch.from_numpy(matrix)).squeeze(-1)
            probabilities = torch.sigmoid(logits)
        return np.asarray(probabilities.numpy(), dtype=np.float32)
