"""Token counters implementing the :class:`~linkdiscovery.interfaces.TokenCounter` Protocol.

Two implementations are provided:

- :class:`SimpleTokenCounter`: a deterministic, dependency-free word and
  punctuation counter for tests and the hashing embedding provider. It is an
  approximation and therefore not valid for reproducing a real model's input
  budget (SPEC "Chunking"), but it is stable across platforms and versions.
- :class:`HuggingFaceTokenCounter`: counts with a pinned
  ``transformers.AutoTokenizer``, which is the reproducible choice when a real
  embedding model is configured. ``transformers`` is imported lazily so the
  core package works without the ``embeddings`` extra.
"""

from __future__ import annotations

import importlib
import re
from typing import Any

from linkdiscovery.errors import PreprocessError

__all__ = ["HuggingFaceTokenCounter", "SimpleTokenCounter"]


class SimpleTokenCounter:
    """Deterministic regex token counter: one token per word or punctuation mark.

    A token is a maximal run of word characters (``\\w+``) or a single
    non-word, non-space character. Whitespace never contributes tokens, so
    token counts are additive across whitespace-separated concatenation:
    ``count(a + " " + b) == count(a) + count(b)``. That invariant is what
    makes the chunker's greedy packing exact under this counter.
    """

    _TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")

    def count_tokens(self, text: str) -> int:
        """Return the number of word/punctuation tokens in ``text``."""
        return len(self._TOKEN_PATTERN.findall(text))

    @property
    def fingerprint(self) -> str:
        """Stable identity of this approximation; bumped if the regex changes."""
        return "simple-tokenizer:v1"


class HuggingFaceTokenCounter:
    """Counts tokens with a pinned Hugging Face tokenizer.

    The tokenizer is resolved by ``model_id`` at an immutable ``revision``
    so counts are reproducible (SPEC: revisions are pinned). Special tokens
    are excluded from counts because chunk budgets measure content, not the
    model's sequence framing.

    Raises :class:`~linkdiscovery.errors.PreprocessError` when the
    ``transformers`` package is not installed (it ships with the
    ``embeddings`` extra) or when the tokenizer cannot be loaded.
    """

    def __init__(self, model_id: str, revision: str) -> None:
        if not model_id or not revision:
            raise PreprocessError(
                "HuggingFaceTokenCounter requires a non-empty model_id and revision; "
                f"got model_id={model_id!r}, revision={revision!r}"
            )
        try:
            transformers: Any = importlib.import_module("transformers")
        except ImportError as exc:
            raise PreprocessError(
                "HuggingFaceTokenCounter requires the 'transformers' package, which is not "
                "installed; install the embeddings extra "
                "(for example: uv pip install 'linkdiscovery[embeddings]') "
                "or use SimpleTokenCounter for tokenizer-free operation"
            ) from exc
        self._model_id = model_id
        self._revision = revision
        try:
            self._tokenizer: Any = transformers.AutoTokenizer.from_pretrained(
                model_id, revision=revision
            )
        except Exception as exc:
            raise PreprocessError(
                f"HuggingFaceTokenCounter could not load tokenizer {model_id!r} "
                f"at revision {revision!r}: {exc}"
            ) from exc

    def count_tokens(self, text: str) -> int:
        """Return the number of model tokens in ``text``, excluding special tokens."""
        return len(self._tokenizer.encode(text, add_special_tokens=False))

    @property
    def fingerprint(self) -> str:
        """Tokenizer identity: model id plus pinned revision."""
        return f"hf-tokenizer:{self._model_id}@{self._revision}"
