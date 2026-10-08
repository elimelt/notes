"""Tests for frozen-encoder token states and span representations.

The :class:`HashingTokenEncoder` tests are dependency-free. The
:class:`QwenTokenEncoder` tests are skipped without ``transformers`` and
additionally require ``LINKDISCOVERY_ALLOW_MODEL_DOWNLOAD=1`` (first run
downloads a tiny model from the Hugging Face Hub), mirroring
``tests/test_embed_sentence_transformers.py``.
"""

from __future__ import annotations

import importlib
import os
from typing import Any

import numpy as np
import pytest

from linkdiscovery.contracts.units import Span
from linkdiscovery.errors import ContractError, EmbeddingRuntimeError
from linkdiscovery.inline.encode import (
    WIDTH_BUCKET_COUNT,
    HashingTokenEncoder,
    QwenTokenEncoder,
    TokenStateEncoder,
    TokenStates,
    WindowedTokenEncoder,
    span_representation,
    span_representation_dim,
)

requires_download = pytest.mark.skipif(
    os.environ.get("LINKDISCOVERY_ALLOW_MODEL_DOWNLOAD") != "1",
    reason="set LINKDISCOVERY_ALLOW_MODEL_DOWNLOAD=1 to run tests that download a model",
)

# Tiny (~2 MB) decoder-style model kept only for the gated integration test.
TINY_MODEL = "sshleifer/tiny-gpt2"


class TestTokenStates:
    def test_holds_offsets_and_states(self) -> None:
        states = TokenStates(((0, 3), (4, 7)), np.ones((2, 4), dtype=np.float32))
        assert states.n_tokens == 2
        assert states.hidden_size == 4
        assert states.token_offsets == ((0, 3), (4, 7))

    def test_states_are_read_only(self) -> None:
        states = TokenStates(((0, 3),), np.ones((1, 4), dtype=np.float32))
        with pytest.raises(ValueError, match="read-only"):
            states.states[0, 0] = 5.0

    def test_misaligned_rows_raise(self) -> None:
        with pytest.raises(ContractError, match="1 token offsets for 2 state rows"):
            TokenStates(((0, 3),), np.ones((2, 4), dtype=np.float32))

    def test_non_matrix_states_raise(self) -> None:
        with pytest.raises(ContractError, match="must be 2-D"):
            TokenStates(((0, 3),), np.ones(4, dtype=np.float32))

    def test_invalid_offsets_raise(self) -> None:
        with pytest.raises(ContractError, match="invalid token offset"):
            TokenStates(((3, 1),), np.ones((1, 4), dtype=np.float32))
        with pytest.raises(ContractError, match="invalid token offset"):
            TokenStates(((-1, 2),), np.ones((1, 4), dtype=np.float32))


class TestHashingTokenEncoder:
    def test_offsets_match_source_text(self) -> None:
        text = "Paxos consensus, done!"
        states = HashingTokenEncoder().encode_tokens(text)
        tokens = [text[start:end] for start, end in states.token_offsets]
        assert tokens == ["Paxos", "consensus", ",", "done", "!"]

    def test_shapes_and_dtype(self) -> None:
        encoder = HashingTokenEncoder(hidden_size=16)
        states = encoder.encode_tokens("alpha beta gamma")
        assert states.states.shape == (3, 16)
        assert states.states.dtype == np.float32
        assert encoder.hidden_size == 16

    def test_default_hidden_size(self) -> None:
        assert HashingTokenEncoder().hidden_size == 64

    def test_deterministic_across_instances(self) -> None:
        first = HashingTokenEncoder().encode_tokens("raft leader election")
        second = HashingTokenEncoder().encode_tokens("raft leader election")
        np.testing.assert_array_equal(first.states, second.states)
        assert first.token_offsets == second.token_offsets

    def test_left_context_changes_state(self) -> None:
        # The same token after a different predecessor must get a different
        # state (causal-pooling mimicry), while the first token is context-free.
        after_alpha = HashingTokenEncoder().encode_tokens("alpha beta")
        after_gamma = HashingTokenEncoder().encode_tokens("gamma beta")
        assert not np.allclose(after_alpha.states[1], after_gamma.states[1])
        same_first = HashingTokenEncoder().encode_tokens("beta alpha")
        also_first = HashingTokenEncoder().encode_tokens("beta gamma")
        np.testing.assert_array_equal(same_first.states[0], also_first.states[0])

    def test_states_are_unit_norm(self) -> None:
        states = HashingTokenEncoder().encode_tokens("normalized tokens here")
        norms = np.linalg.norm(states.states, axis=1)
        np.testing.assert_allclose(norms, 1.0, rtol=1e-5)

    def test_empty_text_yields_zero_tokens(self) -> None:
        states = HashingTokenEncoder(hidden_size=8).encode_tokens("   ")
        assert states.n_tokens == 0
        assert states.states.shape == (0, 8)

    def test_satisfies_protocol(self) -> None:
        assert isinstance(HashingTokenEncoder(), TokenStateEncoder)

    def test_fingerprint_depends_on_hidden_size(self) -> None:
        assert HashingTokenEncoder(16).fingerprint == HashingTokenEncoder(16).fingerprint
        assert HashingTokenEncoder(16).fingerprint != HashingTokenEncoder(32).fingerprint

    def test_invalid_hidden_size_raises(self) -> None:
        with pytest.raises(ContractError, match="hidden_size must be >= 1"):
            HashingTokenEncoder(0)


def three_token_states(hidden: int = 4) -> TokenStates:
    """States for tokens 'foo bar baz' with hand-checkable basis vectors."""
    matrix = np.zeros((3, hidden), dtype=np.float32)
    matrix[0, 0] = 1.0
    matrix[1, 1] = 1.0
    matrix[2, 2] = 1.0
    return TokenStates(((0, 3), (4, 7), (8, 11)), matrix)


class TestSpanRepresentation:
    def test_three_token_span_hand_checked(self) -> None:
        states = three_token_states()
        rep = span_representation(states, Span(0, 11), hand_features=(0.5, 2.0))
        assert rep.dtype == np.float32
        assert rep.shape == (span_representation_dim(4, 2),)
        np.testing.assert_array_equal(rep[0:4], states.states[0])  # start token
        np.testing.assert_array_equal(rep[4:8], states.states[2])  # end token
        np.testing.assert_allclose(rep[8:12], states.states.mean(axis=0))  # interior
        np.testing.assert_array_equal(rep[12:17], [0.0, 0.0, 1.0, 0.0, 0.0])  # width 3
        np.testing.assert_array_equal(rep[17:], [0.5, 2.0])  # hand features

    def test_single_token_width_bucket(self) -> None:
        rep = span_representation(three_token_states(), Span(4, 7), hand_features=())
        np.testing.assert_array_equal(rep[12:17], [1.0, 0.0, 0.0, 0.0, 0.0])

    def test_five_plus_width_bucket(self) -> None:
        offsets = tuple((i * 2, i * 2 + 1) for i in range(7))
        states = TokenStates(offsets, np.ones((7, 2), dtype=np.float32))
        rep = span_representation(states, Span(0, 13), hand_features=())
        np.testing.assert_array_equal(rep[6:11], [0.0, 0.0, 0.0, 0.0, 1.0])

    def test_partial_overlap_selects_covering_token(self) -> None:
        states = three_token_states()
        rep = span_representation(states, Span(5, 6), hand_features=())
        np.testing.assert_array_equal(rep[0:4], states.states[1])
        np.testing.assert_array_equal(rep[4:8], states.states[1])

    def test_no_overlap_raises(self) -> None:
        with pytest.raises(ContractError, match="overlaps none"):
            span_representation(three_token_states(), Span(12, 15), hand_features=())

    def test_empty_span_at_token_boundary_raises(self) -> None:
        with pytest.raises(ContractError, match="overlaps none"):
            span_representation(three_token_states(), Span(3, 3), hand_features=())

    def test_non_finite_hand_features_raise(self) -> None:
        with pytest.raises(ContractError, match="finite"):
            span_representation(three_token_states(), Span(0, 3), hand_features=(float("nan"),))

    def test_dim_formula(self) -> None:
        assert span_representation_dim(64, 3) == 3 * 64 + WIDTH_BUCKET_COUNT + 3
        with pytest.raises(ContractError, match="hidden_size must be >= 1"):
            span_representation_dim(0, 3)


class _TruncatingHashingEncoder(HashingTokenEncoder):
    """Hashing encoder that truncates at ``max_tokens``, mimicking a model limit.

    Test-only stand-in for the windowed wrapper's inner encoder: same states
    and offsets as :class:`HashingTokenEncoder`, but any text beyond
    ``max_tokens`` tokens is cut, exactly like ``QwenTokenEncoder``'s
    ``max_tokens`` truncation.
    """

    def __init__(self, hidden_size: int, max_tokens: int) -> None:
        super().__init__(hidden_size)
        self._max_tokens = max_tokens

    def encode_tokens(self, text: str) -> TokenStates:
        states = super().encode_tokens(text)
        if states.n_tokens <= self._max_tokens:
            return states
        return TokenStates(
            states.token_offsets[: self._max_tokens],
            np.ascontiguousarray(states.states[: self._max_tokens]),
        )


def _long_text(n_tokens: int) -> str:
    """Synthetic long text whose regex tokens are ``tok0 tok1 ...``."""
    return " ".join(f"tok{i}" for i in range(n_tokens))


class TestWindowedTokenEncoder:
    WINDOW = 16
    STRIDE = 12
    HIDDEN = 16

    def _windowed(self) -> WindowedTokenEncoder:
        inner = _TruncatingHashingEncoder(self.HIDDEN, self.WINDOW)
        return WindowedTokenEncoder(inner, window_tokens=self.WINDOW, stride_tokens=self.STRIDE)

    def test_offsets_map_to_the_right_characters(self) -> None:
        text = _long_text(100)
        states = self._windowed().encode_tokens(text)
        tokens = [text[start:end] for start, end in states.token_offsets]
        assert tokens == [f"tok{i}" for i in range(100)]
        full = HashingTokenEncoder(self.HIDDEN).encode_tokens(text)
        assert states.token_offsets == full.token_offsets

    def test_deep_inside_selection_preserves_left_context(self) -> None:
        # Every kept token must come from the window where it sits deepest
        # (most left context). For the hashing encoder a token's state mixes
        # its predecessor's hash, so deep-inside selection reproduces the
        # full-document encoding EXACTLY; taking any token as the first token
        # of a later window would lose the predecessor and change the state.
        text = _long_text(100)
        states = self._windowed().encode_tokens(text)
        full = HashingTokenEncoder(self.HIDDEN).encode_tokens(text)
        np.testing.assert_array_equal(states.states, full.states)
        # Prove the assertion has teeth: the seam token (first token beyond
        # window 0) encoded as a window-INITIAL token differs from the full
        # encoding, so exact equality really does pin the selection rule.
        seam_start = full.token_offsets[self.WINDOW][0]
        shallow = HashingTokenEncoder(self.HIDDEN).encode_tokens(text[seam_start:])
        assert not np.allclose(shallow.states[0], full.states[self.WINDOW])

    def test_short_text_matches_inner_exactly(self) -> None:
        text = _long_text(5)
        windowed = self._windowed().encode_tokens(text)
        inner = HashingTokenEncoder(self.HIDDEN).encode_tokens(text)
        assert windowed.token_offsets == inner.token_offsets
        np.testing.assert_array_equal(windowed.states, inner.states)

    def test_window_boundary_token_counts_are_exact(self) -> None:
        # Exactly one window, then one token past it: no token lost or doubled.
        for n_tokens in (self.WINDOW, self.WINDOW + 1, 2 * self.WINDOW):
            states = self._windowed().encode_tokens(_long_text(n_tokens))
            assert states.n_tokens == n_tokens

    def test_empty_text_yields_zero_tokens(self) -> None:
        states = self._windowed().encode_tokens("   ")
        assert states.n_tokens == 0
        assert states.states.shape == (0, self.HIDDEN)

    def test_satisfies_protocol_and_hidden_size(self) -> None:
        windowed = self._windowed()
        assert isinstance(windowed, TokenStateEncoder)
        assert windowed.hidden_size == self.HIDDEN

    def test_fingerprint_pins_windowing_and_inner(self) -> None:
        inner = HashingTokenEncoder(16)
        base = WindowedTokenEncoder(inner, window_tokens=16, stride_tokens=12)
        same = WindowedTokenEncoder(HashingTokenEncoder(16), window_tokens=16, stride_tokens=12)
        assert base.fingerprint == same.fingerprint
        other_window = WindowedTokenEncoder(inner, window_tokens=20, stride_tokens=12)
        other_stride = WindowedTokenEncoder(inner, window_tokens=16, stride_tokens=8)
        other_inner = WindowedTokenEncoder(
            HashingTokenEncoder(32), window_tokens=16, stride_tokens=12
        )
        fingerprints = {
            base.fingerprint,
            other_window.fingerprint,
            other_stride.fingerprint,
            other_inner.fingerprint,
        }
        assert len(fingerprints) == 4
        assert base.fingerprint != inner.fingerprint

    def test_invalid_stride_raises(self) -> None:
        inner = HashingTokenEncoder(8)
        with pytest.raises(ContractError, match="stride_tokens < window_tokens"):
            WindowedTokenEncoder(inner, window_tokens=16, stride_tokens=16)
        with pytest.raises(ContractError, match="stride_tokens < window_tokens"):
            WindowedTokenEncoder(inner, window_tokens=16, stride_tokens=0)

    @requires_download
    def test_real_tiny_model_windowed_states(self) -> None:
        pytest.importorskip("torch")
        pytest.importorskip("transformers")
        window, stride = 16, 12
        inner = QwenTokenEncoder(TINY_MODEL, "main", max_tokens=window)
        windowed = WindowedTokenEncoder(inner, window_tokens=window, stride_tokens=stride)
        text = " ".join(f"word{i} consensus" for i in range(40))
        truncated = inner.encode_tokens(text)
        states = windowed.encode_tokens(text)
        # The wrapper must reach past the inner truncation horizon.
        assert states.n_tokens > truncated.n_tokens
        assert states.states.shape == (states.n_tokens, windowed.hidden_size)
        last_end = 0
        for start, end in states.token_offsets:
            assert 0 <= start < end <= len(text)
            assert end > last_end
            last_end = end
        # A span far beyond the first window still gets a representation.
        tail_start = states.token_offsets[-2][0]
        rep = span_representation(states, Span(tail_start, len(text)), hand_features=())
        assert rep.shape == (span_representation_dim(windowed.hidden_size, 0),)


class TestQwenTokenEncoder:
    def test_missing_transformers_names_the_extra(self, monkeypatch: pytest.MonkeyPatch) -> None:
        real_import = importlib.import_module

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "transformers":
                raise ImportError("No module named 'transformers'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(importlib, "import_module", fake_import)
        with pytest.raises(EmbeddingRuntimeError, match=r"linkdiscovery\[embeddings\]"):
            QwenTokenEncoder("some/model", "main")

    def test_invalid_max_tokens_raises_before_loading(self) -> None:
        with pytest.raises(ContractError, match="max_tokens must be >= 1"):
            QwenTokenEncoder("some/model", "main", max_tokens=0)

    @requires_download
    def test_real_tiny_model_token_states(self) -> None:
        pytest.importorskip("torch")
        pytest.importorskip("transformers")
        encoder = QwenTokenEncoder(TINY_MODEL, "main", max_tokens=32)
        assert isinstance(encoder, TokenStateEncoder)
        text = "Paxos reaches consensus"
        states = encoder.encode_tokens(text)
        assert states.n_tokens > 0
        assert states.states.shape == (states.n_tokens, encoder.hidden_size)
        assert states.states.dtype == np.float32
        for start, end in states.token_offsets:
            assert 0 <= start < end <= len(text)
        # Offsets must be usable for span representations end to end.
        rep = span_representation(states, Span(0, 5), hand_features=(1.0,))
        assert rep.shape == (span_representation_dim(encoder.hidden_size, 1),)

    @requires_download
    def test_fingerprint_pins_model_and_revision(self) -> None:
        pytest.importorskip("torch")
        pytest.importorskip("transformers")
        first = QwenTokenEncoder(TINY_MODEL, "main", max_tokens=32)
        second = QwenTokenEncoder(TINY_MODEL, "main", max_tokens=64)
        assert first.fingerprint != second.fingerprint
