"""Tests for device qualification and adaptive batching."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pytest
from numpy.typing import NDArray

from linkdiscovery.embed.runtime import (
    default_is_oom,
    encode_adaptively,
    qualify_device,
    resolve_batch_size,
)
from linkdiscovery.errors import ConfigError, EmbeddingRuntimeError


class TestQualifyDevice:
    def test_first_device_qualifies(self) -> None:
        probed: list[str] = []
        device, events = qualify_device(("mps", "cpu"), probed.append)
        assert device == "mps"
        assert events == ()
        assert probed == ["mps"]

    def test_falls_back_and_records_event(self) -> None:
        def probe(device: str) -> None:
            if device == "mps":
                raise RuntimeError("convolution op not implemented for MPS")

        device, events = qualify_device(("mps", "cpu"), probe)
        assert device == "cpu"
        assert len(events) == 1
        assert events[0].startswith("mps unavailable: ")
        assert "not implemented" in events[0]

    def test_all_devices_fail(self) -> None:
        def probe(device: str) -> None:
            raise RuntimeError(f"{device} broken")

        with pytest.raises(EmbeddingRuntimeError, match=r"mps broken.*cpu broken"):
            qualify_device(("mps", "cpu"), probe)

    def test_empty_preference(self) -> None:
        with pytest.raises(EmbeddingRuntimeError, match="empty"):
            qualify_device((), lambda device: None)

    def test_probe_is_not_called_for_later_devices(self) -> None:
        probed: list[str] = []
        qualify_device(("cpu", "mps"), probed.append)
        assert probed == ["cpu"]


def _matrix_for(texts: Sequence[str]) -> NDArray[np.float32]:
    return np.array([[float(len(text)), 1.0] for text in texts], dtype=np.float32)


class TestEncodeAdaptively:
    def test_encodes_in_batches(self) -> None:
        calls: list[tuple[int, int]] = []

        def encode(texts: Sequence[str], batch_size: int) -> NDArray[np.float32]:
            calls.append((len(texts), batch_size))
            return _matrix_for(texts)

        texts = [f"t{i}" * (i + 1) for i in range(5)]
        matrix, effective, events = encode_adaptively(
            encode, texts, initial_batch_size=2, is_oom=default_is_oom
        )
        assert matrix.shape == (5, 2)
        assert effective == 2
        assert events == ()
        assert calls == [(2, 2), (2, 2), (1, 2)]
        np.testing.assert_array_equal(matrix, _matrix_for(texts))

    def test_oom_halves_and_keeps_completed_batches(self) -> None:
        encoded: list[str] = []
        call_count = 0

        def encode(texts: Sequence[str], batch_size: int) -> NDArray[np.float32]:
            nonlocal call_count
            call_count += 1
            if call_count > 1 and len(texts) > 2:
                raise RuntimeError("MPS backend out of memory")
            encoded.extend(texts)
            return _matrix_for(texts)

        texts = [f"text-{i}" for i in range(8)]
        matrix, effective, events = encode_adaptively(
            encode, texts, initial_batch_size=4, is_oom=default_is_oom
        )
        assert matrix.shape == (8, 2)
        assert effective == 2
        assert len(events) == 1
        assert "4->2" in events[0]
        # Every text encoded exactly once: completed batches are never redone.
        assert encoded == texts

    def test_oom_at_batch_size_one_raises(self) -> None:
        def encode(texts: Sequence[str], batch_size: int) -> NDArray[np.float32]:
            raise MemoryError("insufficient memory")

        with pytest.raises(EmbeddingRuntimeError, match="batch size 1"):
            encode_adaptively(encode, ["a", "b"], initial_batch_size=2, is_oom=default_is_oom)

    def test_non_oom_exceptions_propagate(self) -> None:
        def encode(texts: Sequence[str], batch_size: int) -> NDArray[np.float32]:
            raise ValueError("bad input")

        with pytest.raises(ValueError, match="bad input"):
            encode_adaptively(encode, ["a"], initial_batch_size=1, is_oom=default_is_oom)

    def test_empty_texts(self) -> None:
        def encode(texts: Sequence[str], batch_size: int) -> NDArray[np.float32]:
            raise AssertionError("must not be called")

        matrix, effective, events = encode_adaptively(
            encode, [], initial_batch_size=4, is_oom=default_is_oom
        )
        assert matrix.shape == (0, 0)
        assert effective == 4
        assert events == ()

    def test_invalid_initial_batch_size(self) -> None:
        with pytest.raises(EmbeddingRuntimeError, match=">= 1"):
            encode_adaptively(
                lambda texts, batch_size: _matrix_for(texts),
                ["a"],
                initial_batch_size=0,
                is_oom=default_is_oom,
            )


class TestDefaultIsOom:
    @pytest.mark.parametrize(
        "exc",
        [
            MemoryError("anything"),
            RuntimeError("CUDA out of memory. Tried to allocate 20.00 MiB"),
            RuntimeError("MPS backend out of memory (MPS allocated: 8.00 GB)"),
            RuntimeError("Insufficient Memory for the requested operation"),
        ],
    )
    def test_recognizes_oom(self, exc: BaseException) -> None:
        assert default_is_oom(exc)

    @pytest.mark.parametrize(
        "exc",
        [RuntimeError("shape mismatch"), ValueError("bad value"), KeyboardInterrupt()],
    )
    def test_rejects_non_oom(self, exc: BaseException) -> None:
        assert not default_is_oom(exc)


class TestResolveBatchSize:
    def test_explicit_integer(self) -> None:
        assert resolve_batch_size(7, device="cpu") == 7

    def test_auto_by_device(self) -> None:
        assert resolve_batch_size("auto", device="mps") == 32
        assert resolve_batch_size("auto", device="cuda") == 32
        assert resolve_batch_size("auto", device="cpu") == 16

    def test_rejects_non_positive(self) -> None:
        with pytest.raises(ConfigError, match=">= 1"):
            resolve_batch_size(0, device="cpu")

    def test_rejects_unknown_string(self) -> None:
        with pytest.raises(ConfigError, match="auto"):
            resolve_batch_size("huge", device="cpu")
