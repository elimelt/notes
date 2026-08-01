"""Runtime policy: device qualification and adaptive batching (SPEC "Runtime policy").

Two rules from the SPEC live here:

1. Framework-level availability does not qualify a device. A device is
   qualified only when a *probe* performs real work on it (for the
   sentence-transformers provider: loading the model and encoding a few
   representative texts). :func:`qualify_device` walks the configured
   preference order, records every failure as a human-readable fallback
   event, and raises when nothing qualifies — no silent fallback.

2. Out-of-memory failures reduce the batch size and retry from the last
   complete batch. :func:`encode_adaptively` halves the batch on OOM,
   preserves already-encoded results, and raises when even batch size 1
   fails. It never changes model, dimensions, precision, or truncation
   policy — those are the caller's invariants and are not negotiable
   fallback dimensions.

Both functions are framework-agnostic: probes and encode callables carry all
torch/model knowledge, so this module is unit-testable with fakes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from linkdiscovery.errors import ConfigError, EmbeddingRuntimeError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from numpy.typing import NDArray

__all__ = [
    "default_is_oom",
    "encode_adaptively",
    "qualify_device",
    "resolve_batch_size",
]

_OOM_SUBSTRINGS = (
    "out of memory",
    "mps backend out of memory",
    "insufficient memory",
)

_AUTO_BATCH_BY_DEVICE = {"mps": 32, "cuda": 32}
_AUTO_BATCH_DEFAULT = 16


def default_is_oom(exc: BaseException) -> bool:
    """Recognize common out-of-memory failures by exception type and message.

    Matches :class:`MemoryError` and any exception whose message contains a
    known OOM substring (covers PyTorch CUDA/MPS OOM errors, which are plain
    ``RuntimeError`` subclasses with descriptive messages).
    """
    if isinstance(exc, MemoryError):
        return True
    message = str(exc).lower()
    return any(marker in message for marker in _OOM_SUBSTRINGS)


def qualify_device(
    preference: Sequence[str], probe: Callable[[str], None]
) -> tuple[str, tuple[str, ...]]:
    """Select the first device in ``preference`` that passes ``probe``.

    ``probe(device)`` must actually exercise the device — for a model
    provider that means building the model and encoding representative
    texts, because framework-level availability alone does not establish
    that every model operation works. A probe failure is recorded as a
    fallback event string (``"<device> unavailable: <reason>"``) and the
    next device is tried.

    Returns ``(qualified_device, fallback_events)``. Raises
    :class:`EmbeddingRuntimeError` when the preference list is empty or no
    device qualifies; the message includes every recorded failure.
    """
    if not preference:
        raise EmbeddingRuntimeError(
            "device preference is empty; configure at least one device (for example ['cpu'])"
        )
    events: list[str] = []
    for device in preference:
        try:
            probe(device)
        except Exception as exc:  # any probe failure disqualifies the device
            events.append(f"{device} unavailable: {exc}")
            continue
        return device, tuple(events)
    detail = "; ".join(events)
    raise EmbeddingRuntimeError(f"no device in preference {list(preference)!r} qualified: {detail}")


def encode_adaptively(
    encode: Callable[[Sequence[str], int], NDArray[np.float32]],
    texts: Sequence[str],
    *,
    initial_batch_size: int,
    is_oom: Callable[[BaseException], bool] = default_is_oom,
) -> tuple[NDArray[np.float32], int, tuple[str, ...]]:
    """Encode ``texts`` in batches, halving the batch size on out-of-memory.

    ``encode(batch, batch_size)`` embeds one contiguous slice of ``texts``.
    When it raises an exception recognized by ``is_oom``, the batch size is
    halved and encoding retries **from the last complete batch** —
    already-encoded results are kept, never recomputed. An OOM at batch
    size 1 raises :class:`EmbeddingRuntimeError` (there is nothing smaller
    to try). Exceptions ``is_oom`` does not recognize propagate unchanged.

    Caller invariant (documented, not enforced): the ``encode`` callable
    must be a fixed model configuration — adaptive batching never changes
    model, output dimensions, precision, or truncation policy; batch size
    is the only degree of freedom.

    Returns ``(matrix, effective_batch_size, fallback_events)`` where
    ``matrix`` stacks all results in input order, ``effective_batch_size``
    is the final batch size in use, and each fallback event describes one
    halving. An empty ``texts`` yields an empty ``(0, 0)`` matrix.
    """
    if initial_batch_size < 1:
        raise EmbeddingRuntimeError(f"initial batch size must be >= 1, got {initial_batch_size}")
    events: list[str] = []
    chunks: list[NDArray[np.float32]] = []
    batch_size = initial_batch_size
    position = 0
    total = len(texts)
    while position < total:
        batch = texts[position : position + batch_size]
        try:
            result = encode(batch, batch_size)
        except Exception as exc:
            if not is_oom(exc):
                raise
            if batch_size <= 1:
                raise EmbeddingRuntimeError(
                    f"out of memory at batch size 1 (text index {position} of {total}); "
                    f"cannot reduce further: {exc}"
                ) from exc
            halved = batch_size // 2
            events.append(
                f"batch size {batch_size}->{halved}: out of memory, retrying from "
                f"last complete batch (index {position}): {exc}"
            )
            batch_size = halved
            continue
        chunks.append(np.asarray(result, dtype=np.float32))
        position += len(batch)
    if not chunks:
        return np.zeros((0, 0), dtype=np.float32), batch_size, tuple(events)
    return np.vstack(chunks).astype(np.float32, copy=False), batch_size, tuple(events)


def resolve_batch_size(config_batch_size: int | str, *, device: str) -> int:
    """Resolve the configured batch size (a positive integer or ``"auto"``).

    ``"auto"`` picks a sane per-device default: 32 for accelerators
    (``mps``/``cuda``), 16 for the CPU. Explicit integers are returned
    unchanged. Anything else raises :class:`ConfigError`.
    """
    if isinstance(config_batch_size, bool):
        raise ConfigError(
            f"batch_size must be a positive integer or 'auto', got {config_batch_size!r}"
        )
    if isinstance(config_batch_size, int):
        if config_batch_size < 1:
            raise ConfigError(f"batch_size must be >= 1, got {config_batch_size}")
        return config_batch_size
    if config_batch_size == "auto":
        return _AUTO_BATCH_BY_DEVICE.get(device, _AUTO_BATCH_DEFAULT)
    raise ConfigError(f"batch_size must be a positive integer or 'auto', got {config_batch_size!r}")
