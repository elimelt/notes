"""The sentence-transformers provider: real models behind the provider protocol.

All heavy imports (``sentence_transformers``, ``torch``) happen lazily via
:mod:`importlib` inside ``__init__``, so this module imports cleanly in
environments without the ``embeddings`` extra; constructing the provider
there raises :class:`~linkdiscovery.errors.EmbeddingRuntimeError` telling the
user to install ``linkdiscovery[embeddings]``.

Policy, per the SPEC:

- The model is loaded pinned to ``config.revision`` on the requested device.
- Precision is honored exactly: ``float16``/``bfloat16`` convert the model
  dtype and are verified with a small tensor operation on the device; an
  unsupported precision raises instead of silently degrading to float32.
- ``config.dimensions`` smaller than the model's native width enables
  Matryoshka truncation (``truncate_dim``); a width the model cannot satisfy
  raises, never silently mismatches.
- ``config.instruction`` (Qwen3-style prompt prefix) is applied identically
  to every text via the ``prompt`` argument and is part of the fingerprint.
- The fingerprint uses the RESOLVED model revision — the commit hash reported
  by the loaded model when available — so ``revision: main`` drift is
  detectable.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

import numpy as np

from linkdiscovery.errors import EmbeddingRuntimeError
from linkdiscovery.fingerprint import fingerprint

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from linkdiscovery.config import EmbeddingConfig

__all__ = ["SentenceTransformersProvider"]

_INSTALL_HINT = (
    "install the optional embedding dependencies with: pip install 'linkdiscovery[embeddings]'"
)

_MATRIX_NDIM = 2


def _import_optional(name: str) -> Any:
    """Import an optional heavy dependency, or raise an actionable error."""
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        raise EmbeddingRuntimeError(
            f"the sentence-transformers embedding provider requires the {name!r} package, "
            f"which is not installed; {_INSTALL_HINT}"
        ) from exc


class SentenceTransformersProvider:
    """A pinned ``SentenceTransformer`` model behind the provider protocol.

    Construction loads the model (network access on first download only),
    applies dimension truncation and precision, and verifies both; every
    failure mode raises :class:`EmbeddingRuntimeError` with the model,
    revision, and device named. ``encode`` returns un-normalized float32
    matrices (the embedder normalizes) and verifies the output width on
    every call, so a dimension mismatch can never pass silently.
    """

    def __init__(self, config: EmbeddingConfig, device: str) -> None:
        """Load ``config.model`` at ``config.revision`` onto ``device``."""
        st_module = _import_optional("sentence_transformers")
        torch = _import_optional("torch")
        self._config = config
        self._device = device
        self._instruction = config.instruction
        self._model = self._load_model(st_module, config, device)
        self._apply_dimensions(config)
        self._apply_precision(torch, config, device)
        if config.max_input_tokens is not None:
            self._model.max_seq_length = config.max_input_tokens
        self._max_input_tokens = self._effective_max_input_tokens(config)
        resolved_revision = self._detect_revision(self._model, config.revision)
        # The SPEC model-fingerprint inputs: identifier, immutable (resolved)
        # revision, tokenizer revision, pooling method, instruction text,
        # output dimension, normalization, precision, maximum input length.
        # The tokenizer ships in the same pinned repository as the model, so
        # its revision is the resolved model revision.
        self._fingerprint = fingerprint(
            {
                "provider": "sentence-transformers",
                "model": config.model,
                "revision": resolved_revision,
                "tokenizer_revision": resolved_revision,
                "pooling": self._detect_pooling(self._model),
                "instruction": config.instruction,
                "dimensions": config.dimensions,
                "normalize": config.normalize,
                "precision": config.precision,
                "max_input_tokens": self._max_input_tokens,
            }
        )

    @staticmethod
    def _load_model(st_module: Any, config: EmbeddingConfig, device: str) -> Any:
        try:
            return st_module.SentenceTransformer(
                config.model, revision=config.revision, device=device
            )
        except Exception as exc:
            raise EmbeddingRuntimeError(
                f"cannot load sentence-transformers model {config.model!r} "
                f"(revision {config.revision!r}) on device {device!r}: {exc}"
            ) from exc

    def _apply_dimensions(self, config: EmbeddingConfig) -> None:
        """Enable Matryoshka truncation, or raise on an unsatisfiable width."""
        native = self._model.get_sentence_embedding_dimension()
        if native is None:
            # The model does not report its width; trust the configuration and
            # rely on the per-call output check in :meth:`encode`.
            self._model.truncate_dim = config.dimensions
            return
        native = int(native)
        if config.dimensions > native:
            raise EmbeddingRuntimeError(
                f"model {config.model!r} produces {native}-dimensional embeddings, but the "
                f"configuration requests {config.dimensions}; requested dimensions must be "
                f"<= the model's native width (Matryoshka truncation can only shrink)"
            )
        if config.dimensions < native:
            self._model.truncate_dim = config.dimensions

    def _apply_precision(self, torch: Any, config: EmbeddingConfig, device: str) -> None:
        """Convert the model to the configured dtype and verify device support.

        Precision is never silently changed: if the device cannot execute the
        configured dtype, this raises instead of falling back to float32.
        """
        dtype_by_name = {
            "float32": torch.float32,
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
        }
        dtype = dtype_by_name.get(config.precision)
        if dtype is None:
            raise EmbeddingRuntimeError(
                f"unknown precision {config.precision!r}; expected one of: "
                f"{', '.join(sorted(dtype_by_name))}"
            )
        if dtype is torch.float32:
            return  # models load in float32; nothing to convert or verify
        try:
            self._model.to(dtype=dtype)
            probe = torch.ones((2, 2), device=device, dtype=dtype)
            (probe @ probe).float().sum().item()
        except Exception as exc:
            raise EmbeddingRuntimeError(
                f"precision {config.precision!r} is not supported on device {device!r}: {exc}; "
                "configure a precision this device supports (precision is never changed "
                "silently)"
            ) from exc

    def _effective_max_input_tokens(self, config: EmbeddingConfig) -> int | None:
        if config.max_input_tokens is not None:
            return config.max_input_tokens
        model_max = getattr(self._model, "max_seq_length", None)
        return int(model_max) if isinstance(model_max, int) else None

    @staticmethod
    def _detect_revision(model: Any, configured: str) -> str:
        """Return the loaded model's commit hash when available, else ``configured``."""
        try:
            modules = list(model)
        except TypeError:
            modules = []
        for module in modules:
            auto_model = getattr(module, "auto_model", None)
            commit = getattr(getattr(auto_model, "config", None), "_commit_hash", None)
            if isinstance(commit, str) and commit:
                return commit
        return configured

    @staticmethod
    def _detect_pooling(model: Any) -> str:
        """Read the pooling mode from the model's pooling module when present."""
        try:
            modules = list(model)
        except TypeError:
            modules = []
        for module in modules:
            getter = getattr(module, "get_pooling_mode_str", None)
            if callable(getter):
                try:
                    return str(getter())
                except Exception:  # fingerprinting must not fail on odd models
                    return "unknown"
        return "unknown"

    @property
    def model_fingerprint(self) -> str:
        """Fingerprint over the resolved revision and every output-affecting option."""
        return self._fingerprint

    @property
    def dimensions(self) -> int:
        """Configured output width (native or Matryoshka-truncated)."""
        return self._config.dimensions

    @property
    def max_input_tokens(self) -> int | None:
        """Effective token budget: the configured cap, else the model's own limit."""
        return self._max_input_tokens

    @property
    def device(self) -> str:
        """The device the model was loaded onto."""
        return self._device

    def count_tokens(self, text: str) -> int:
        """Count tokens with the model's tokenizer (including special tokens)."""
        try:
            encoded = self._model.tokenizer(text, add_special_tokens=True)
            return len(encoded["input_ids"])
        except Exception as exc:
            raise EmbeddingRuntimeError(
                f"tokenizer for model {self._config.model!r} failed to count tokens: {exc}"
            ) from exc

    def encode(self, texts: Sequence[str], *, batch_size: int) -> NDArray[np.float32]:
        """Embed ``texts`` into an un-normalized ``(n, dimensions)`` float32 matrix.

        Out-of-memory errors propagate unchanged so the caller's adaptive
        batching can react; the output shape is verified on every call.
        """
        if not texts:
            return np.zeros((0, self.dimensions), dtype=np.float32)
        kwargs: dict[str, Any] = {
            "batch_size": batch_size,
            "convert_to_numpy": True,
            "normalize_embeddings": False,
            "show_progress_bar": False,
        }
        if self._instruction is not None:
            kwargs["prompt"] = self._instruction
        raw = self._model.encode(list(texts), **kwargs)
        matrix = np.asarray(raw, dtype=np.float32)
        if matrix.ndim != _MATRIX_NDIM or matrix.shape != (len(texts), self.dimensions):
            raise EmbeddingRuntimeError(
                f"model {self._config.model!r} returned shape {matrix.shape} for "
                f"{len(texts)} texts; expected ({len(texts)}, {self.dimensions}) — "
                "embedding dimension mismatch"
            )
        return matrix
