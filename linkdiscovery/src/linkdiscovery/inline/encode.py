"""Frozen-encoder token states and span representations (Architecture A).

This module produces the *inputs* to the learned heads of
SPEC-INLINE-LINKING.md §2 Architecture A: per-token hidden states from a
frozen encoder, and the Lee/SpanBERT span representation of §3 (Question 10)
built on top of them. Nothing here trains; the encoder is frozen by design
(§9: "no backprop through 0.6B params").

Span representation layout (fixed contract, consumed by
:mod:`linkdiscovery.inline.heads` and :mod:`linkdiscovery.inline.train`)::

    [ start-token state   : hidden_size floats
    ; end-token state     : hidden_size floats
    ; mean-pooled span    : hidden_size floats   (all tokens the span overlaps)
    ; width bucket one-hot: WIDTH_BUCKET_COUNT floats (widths 1,2,3,4,5+)
    ; hand features       : len(hand_features) floats, caller-defined order ]

so the total dimensionality is
``3 * hidden_size + WIDTH_BUCKET_COUNT + len(hand_features)``
(:func:`span_representation_dim`).

Heavy dependencies (``transformers``, ``torch``) are imported lazily inside
:class:`QwenTokenEncoder`; the module itself needs only numpy, and the
:class:`HashingTokenEncoder` baseline is dependency-free and deterministic
across processes (it hashes with :mod:`hashlib`, never the builtin
``hash()``).
"""

from __future__ import annotations

import hashlib
import importlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, Protocol, runtime_checkable

import numpy as np

from linkdiscovery.errors import ContractError, EmbeddingRuntimeError
from linkdiscovery.fingerprint import fingerprint

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from linkdiscovery.contracts.units import Span

__all__ = [
    "WIDTH_BUCKET_COUNT",
    "HashingTokenEncoder",
    "QwenTokenEncoder",
    "TokenStateEncoder",
    "TokenStates",
    "WindowedTokenEncoder",
    "span_representation",
    "span_representation_dim",
]

WIDTH_BUCKET_COUNT: Final = 5
"""Number of span-width buckets in the representation: widths 1, 2, 3, 4, 5+."""

_INSTALL_HINT = (
    "install the optional embedding dependencies with: pip install 'linkdiscovery[embeddings]'"
)


def _import_optional(name: str) -> Any:
    """Import an optional heavy dependency, or raise an actionable error."""
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        raise EmbeddingRuntimeError(
            f"the token-state encoder requires the {name!r} package, which is not "
            f"installed; {_INSTALL_HINT}"
        ) from exc


@dataclass(frozen=True, slots=True)
class TokenStates:
    """Per-token hidden states for one encoded text.

    ``token_offsets`` holds half-open character ranges ``[start, end)`` into
    the *exact* text passed to ``encode_tokens``; ``states`` is the aligned
    ``(n_tokens, hidden)`` float32 matrix. Invariants (enforced at
    construction): the matrix is 2-D with one row per offset, and every
    offset satisfies ``0 <= start <= end``. The matrix is made read-only so
    a downstream head can never silently mutate encoder output.
    """

    token_offsets: tuple[tuple[int, int], ...]
    states: NDArray[np.float32]

    def __post_init__(self) -> None:
        offsets = tuple((int(start), int(end)) for start, end in self.token_offsets)
        for start, end in offsets:
            if start < 0 or end < start:
                raise ContractError(
                    f"TokenStates: invalid token offset [{start}, {end}); "
                    "start must be >= 0 and end must be >= start"
                )
        states = np.ascontiguousarray(self.states, dtype=np.float32)
        if states.ndim != 2:  # noqa: PLR2004 - 2 means "a matrix"
            raise ContractError(f"TokenStates: states must be 2-D, got {states.ndim}-D")
        if states.shape[0] != len(offsets):
            raise ContractError(
                f"TokenStates: {len(offsets)} token offsets for {states.shape[0]} state rows"
            )
        states.setflags(write=False)
        object.__setattr__(self, "token_offsets", offsets)
        object.__setattr__(self, "states", states)

    @property
    def n_tokens(self) -> int:
        """Number of encoded tokens."""
        return len(self.token_offsets)

    @property
    def hidden_size(self) -> int:
        """Width of each token state."""
        return int(self.states.shape[1])


@runtime_checkable
class TokenStateEncoder(Protocol):
    """A frozen encoder producing per-token hidden states with char offsets.

    Implementations must be deterministic for a fixed ``fingerprint``: the
    fingerprint is part of trained-head identity, so any change that alters
    the produced states must change it.
    """

    @property
    def hidden_size(self) -> int:
        """Width of the token states this encoder produces."""
        ...

    @property
    def fingerprint(self) -> str:
        """Deterministic identity of the encoder (model, revision, settings)."""
        ...

    def encode_tokens(self, text: str) -> TokenStates:
        """Encode ``text`` into per-token states with character offsets."""
        ...


class HashingTokenEncoder:
    """Deterministic, dependency-free baseline/test encoder.

    Tokenizes on word/punctuation boundaries with character offsets, then
    maps each token to a signed feature-hash vector derived from SHA-256 (so
    the states are identical across processes and platforms — the builtin
    ``hash()`` is never used). Each token's state mixes in a fraction of the
    *previous* token's hash vector before normalization, so left context
    matters, loosely mimicking the causal pooling of a decoder-style encoder
    (SPEC-INLINE-LINKING §9).
    """

    _TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")
    _PREVIOUS_MIX = 0.5
    _NORM_FLOOR = 1e-6

    def __init__(self, hidden_size: int = 64) -> None:
        """Create an encoder emitting ``hidden_size``-wide token states."""
        if hidden_size < 1:
            raise ContractError(f"HashingTokenEncoder: hidden_size must be >= 1, got {hidden_size}")
        self._hidden_size = hidden_size
        self._fingerprint = fingerprint(
            {
                "encoder": "hashing-token",
                "hidden_size": hidden_size,
                "previous_mix": self._PREVIOUS_MIX,
                "version": 1,
            }
        )

    @property
    def hidden_size(self) -> int:
        """Width of the token states this encoder produces."""
        return self._hidden_size

    @property
    def fingerprint(self) -> str:
        """Deterministic identity of the encoder configuration."""
        return self._fingerprint

    def _token_vector(self, token: str) -> NDArray[np.float32]:
        """Signed feature-hash of one token, values in ``[-1, 1]``."""
        data = bytearray()
        block = 0
        while len(data) < self._hidden_size:
            data += hashlib.sha256(f"{block}\x1f{token}".encode()).digest()
            block += 1
        raw = np.frombuffer(bytes(data[: self._hidden_size]), dtype=np.uint8)
        vector: NDArray[np.float32] = raw.astype(np.float32) / 127.5 - 1.0
        return vector

    def encode_tokens(self, text: str) -> TokenStates:
        """Encode ``text``; empty or whitespace-only text yields zero tokens."""
        matches = list(self._TOKEN_PATTERN.finditer(text))
        if not matches:
            return TokenStates((), np.zeros((0, self._hidden_size), dtype=np.float32))
        offsets: list[tuple[int, int]] = []
        rows: list[NDArray[np.float32]] = []
        previous = np.zeros(self._hidden_size, dtype=np.float32)
        for match in matches:
            offsets.append((match.start(), match.end()))
            vector = self._token_vector(match.group())
            state = vector + self._PREVIOUS_MIX * previous
            state /= max(float(np.linalg.norm(state)), self._NORM_FLOOR)
            rows.append(state.astype(np.float32))
            previous = vector
        return TokenStates(tuple(offsets), np.stack(rows))


class QwenTokenEncoder:
    """Frozen transformers encoder extracting last-hidden-state token vectors.

    Loads ``AutoTokenizer``/``AutoModel`` lazily (missing ``transformers``
    raises :class:`~linkdiscovery.errors.EmbeddingRuntimeError` naming the
    ``embeddings`` extra) and runs the model with gradients disabled — the
    encoder stays frozen per Architecture A.

    .. warning:: **Causal-masking caveat (SPEC-INLINE-LINKING §9).**
       Qwen3-Embedding is a decoder-style model with causal masking: each
       token's last-hidden-state vector aggregates *left context only*, not
       BERT-style bidirectional context. A span's start-token state therefore
       sees nothing to its right; the span representation compensates by
       concatenating the end-token state and the pooled interior, but do not
       treat individual token states as bidirectional.
    """

    def __init__(
        self, model_id: str, revision: str, *, device: str = "cpu", max_tokens: int = 512
    ) -> None:
        """Load ``model_id`` pinned to ``revision`` onto ``device``."""
        if max_tokens < 1:
            raise ContractError(f"QwenTokenEncoder: max_tokens must be >= 1, got {max_tokens}")
        transformers = _import_optional("transformers")
        self._torch = _import_optional("torch")
        try:
            self._tokenizer = transformers.AutoTokenizer.from_pretrained(
                model_id, revision=revision
            )
            self._model = transformers.AutoModel.from_pretrained(model_id, revision=revision)
        except Exception as exc:
            raise EmbeddingRuntimeError(
                f"cannot load token-state model {model_id!r} (revision {revision!r}): {exc}"
            ) from exc
        self._model.to(device)
        self._model.eval()
        self._device = device
        self._max_tokens = max_tokens
        self._hidden_size = int(self._model.config.hidden_size)
        self._fingerprint = fingerprint(
            {
                "encoder": "qwen-token",
                "model": model_id,
                "revision": revision,
                "max_tokens": max_tokens,
                "version": 1,
            }
        )

    @property
    def hidden_size(self) -> int:
        """Hidden width of the loaded model."""
        return self._hidden_size

    @property
    def fingerprint(self) -> str:
        """Deterministic identity: model id, revision, and token budget."""
        return self._fingerprint

    def encode_tokens(self, text: str) -> TokenStates:
        """Encode ``text`` (truncated to ``max_tokens``) into token states.

        Special tokens and zero-width offsets are dropped, so every returned
        row maps to real characters of the input text.
        """
        encoded = self._tokenizer(
            text,
            return_offsets_mapping=True,
            return_special_tokens_mask=True,
            truncation=True,
            max_length=self._max_tokens,
            return_tensors="pt",
        )
        offset_mapping = encoded.pop("offset_mapping")[0].tolist()
        special_mask = encoded.pop("special_tokens_mask")[0].tolist()
        inputs = {key: value.to(self._device) for key, value in encoded.items()}
        with self._torch.no_grad():
            hidden = self._model(**inputs).last_hidden_state[0]
        matrix = hidden.detach().to("cpu").to(self._torch.float32).numpy()
        keep = [
            index
            for index, (special, (start, end)) in enumerate(
                zip(special_mask, offset_mapping, strict=True)
            )
            if not special and end > start
        ]
        offsets = tuple((int(offset_mapping[i][0]), int(offset_mapping[i][1])) for i in keep)
        states = matrix[keep] if keep else np.zeros((0, self._hidden_size), dtype=np.float32)
        return TokenStates(offsets, np.ascontiguousarray(states, dtype=np.float32))


class WindowedTokenEncoder:
    """Overlapping-window wrapper giving ANY span of a long document token states.

    The inner encoder truncates at roughly ``window_tokens`` (for
    :class:`QwenTokenEncoder`, construct it with ``max_tokens ==
    window_tokens``), so a long document's tail would otherwise get no
    states. This wrapper encodes the document in overlapping windows that
    advance ``stride_tokens`` tokens at a time and stitches the per-window
    states back into one globally-offset :class:`TokenStates`.

    **Deepest-inside selection (SPEC-INLINE-LINKING §9).** The underlying
    Qwen model is decoder-style with *causal* masking: a token's state
    aggregates its left context only, so the best state for a token is the
    one from the window where the token sits deepest — i.e. with the most
    left context. Because windows advance left to right, that is always the
    *earliest* window containing the token; the wrapper therefore keeps each
    token from the first window that reaches it and discards later windows'
    shallower re-encodings. Every kept token beyond the first window sees at
    least ``window_tokens - stride_tokens`` real preceding tokens (128 with
    the 512/384 defaults); tokens in the first window see their full genuine
    left context.

    Stitching is by *character position*, not token index: each window keeps
    exactly the tokens whose global character range extends beyond what
    earlier windows already covered, which stays correct even when
    re-tokenizing a window that starts mid-word splits the boundary tokens
    slightly differently than the previous window did (BPE drift affects
    only the shallow, discarded window prefix).

    The wrapper satisfies :class:`TokenStateEncoder`, and the windowing
    parameters are part of the fingerprint alongside the inner encoder's —
    changing the window or stride changes every produced state matrix, so it
    must change trained-head identity.

    Requirement on the inner encoder: when its input is truncated it must
    still return more than ``stride_tokens`` content tokens (Qwen at the
    512/384 defaults returns ~510 after dropping special tokens, leaving
    ample slack); otherwise the wrapper would stop before the text ends.
    """

    def __init__(
        self,
        inner: TokenStateEncoder,
        *,
        window_tokens: int = 512,
        stride_tokens: int = 384,
    ) -> None:
        """Wrap ``inner``, whose truncation limit should equal ``window_tokens``."""
        if stride_tokens < 1 or stride_tokens >= window_tokens:
            raise ContractError(
                f"WindowedTokenEncoder: need 1 <= stride_tokens < window_tokens, "
                f"got stride_tokens={stride_tokens}, window_tokens={window_tokens}"
            )
        self._inner = inner
        self._window_tokens = window_tokens
        self._stride_tokens = stride_tokens
        self._fingerprint = fingerprint(
            {
                "encoder": "windowed-token",
                "inner": inner.fingerprint,
                "window_tokens": window_tokens,
                "stride_tokens": stride_tokens,
                "version": 1,
            }
        )

    @property
    def hidden_size(self) -> int:
        """Hidden width of the wrapped encoder."""
        return self._inner.hidden_size

    @property
    def fingerprint(self) -> str:
        """Deterministic identity: inner fingerprint plus windowing parameters."""
        return self._fingerprint

    def encode_tokens(self, text: str) -> TokenStates:
        """Encode ``text`` window by window; offsets index the full ``text``.

        Loop invariant: ``covered_end`` is the character position up to which
        tokens have been emitted; a window keeps exactly the tokens whose
        global end exceeds it (the earliest — deepest-inside — window wins,
        per the class docstring). The loop stops once a window returns at
        most ``stride_tokens`` tokens: an untruncated window covered the
        remaining text, and a truncated one always returns more (see the
        inner-encoder requirement above).
        """
        offsets: list[tuple[int, int]] = []
        rows: list[NDArray[np.float32]] = []
        position = 0
        covered_end = 0
        while True:
            window = self._inner.encode_tokens(text[position:])
            for index, (start, end) in enumerate(window.token_offsets):
                global_start, global_end = start + position, end + position
                if global_end <= covered_end:
                    continue
                offsets.append((global_start, global_end))
                rows.append(np.asarray(window.states[index], dtype=np.float32))
                covered_end = max(covered_end, global_end)
            if window.n_tokens <= self._stride_tokens:
                break
            advance = window.token_offsets[self._stride_tokens][0]
            if advance <= 0:
                raise ContractError(
                    "WindowedTokenEncoder: inner encoder cannot advance past character "
                    f"{position} (token {self._stride_tokens} starts at the window origin); "
                    "the inner tokenization is degenerate"
                )
            position += advance
        if not rows:
            return TokenStates((), np.zeros((0, self.hidden_size), dtype=np.float32))
        return TokenStates(tuple(offsets), np.stack(rows))


def span_representation_dim(hidden_size: int, hand_feature_count: int) -> int:
    """Dimensionality of :func:`span_representation` output.

    ``3 * hidden_size`` (start + end + mean-pooled span) plus
    :data:`WIDTH_BUCKET_COUNT` width-bucket slots plus the hand features.
    """
    if hidden_size < 1 or hand_feature_count < 0:
        raise ContractError(
            "span_representation_dim: hidden_size must be >= 1 and hand_feature_count "
            f"must be >= 0, got {hidden_size} and {hand_feature_count}"
        )
    return 3 * hidden_size + WIDTH_BUCKET_COUNT + hand_feature_count


def _hand_feature_vector(hand_features: Sequence[float]) -> NDArray[np.float32]:
    """Validate and convert hand features to a finite float32 vector."""
    vector = np.asarray(tuple(hand_features), dtype=np.float32)
    if vector.ndim != 1:
        raise ContractError("span_representation: hand_features must be a flat sequence of floats")
    if vector.size and not bool(np.isfinite(vector).all()):
        raise ContractError(
            "span_representation: hand_features must be finite; got NaN or infinity"
        )
    return vector


def span_representation(
    states: TokenStates, span: Span, *, hand_features: Sequence[float]
) -> NDArray[np.float32]:
    """The Lee/SpanBERT span representation (SPEC-INLINE-LINKING §3, Q10).

    ``span`` is a character range into the *same text* that produced
    ``states``. The tokens whose offsets overlap the span define the
    representation: the first overlapping token supplies the start state,
    the last supplies the end state, and the mean over *all* overlapping
    tokens is the pooled interior. The width bucket one-hot encodes the
    overlapping-token count (1, 2, 3, 4, 5+), and ``hand_features`` are
    appended verbatim in caller order.

    Output layout and dimensionality are documented at module level; the
    total width is ``span_representation_dim(states.hidden_size,
    len(hand_features))``. Raises
    :class:`~linkdiscovery.errors.ContractError` when the span overlaps no
    token (the span indexes different text, or lies entirely in whitespace)
    or when hand features are not finite floats.
    """
    overlapping = [
        index
        for index, (start, end) in enumerate(states.token_offsets)
        if end > span.start and start < span.end
    ]
    if not overlapping:
        raise ContractError(
            f"span_representation: span [{span.start}, {span.end}) overlaps none of the "
            f"{states.n_tokens} encoded tokens; the span must index the exact text that "
            "was encoded and must cover at least one token"
        )
    hand = _hand_feature_vector(hand_features)
    start_state = states.states[overlapping[0]]
    end_state = states.states[overlapping[-1]]
    interior = states.states[overlapping].mean(axis=0)
    width_bucket = np.zeros(WIDTH_BUCKET_COUNT, dtype=np.float32)
    width_bucket[min(len(overlapping), WIDTH_BUCKET_COUNT) - 1] = 1.0
    representation = np.concatenate([start_state, end_state, interior, width_bucket, hand])
    return np.ascontiguousarray(representation, dtype=np.float32)
