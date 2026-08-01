"""Atomic text-file writing local to the report stage.

:class:`~linkdiscovery.artifacts.store.ArtifactStore` already implements
atomic publishing, but its writer is private and tied to the store's group
layout, while reporters write into a user-chosen output directory. This
module therefore mirrors the store's pattern (same-directory temporary file +
``os.replace``) without depending on store internals, so a crashed or
interrupted report write can never appear as a complete report file.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from linkdiscovery.errors import ReportError

__all__ = ["atomic_write_text"]


def atomic_write_text(path: Path, text: str) -> None:
    """Atomically write ``text`` (UTF-8) to ``path``.

    The payload goes to a temporary file created in the destination
    directory, is flushed and fsynced, and is published with ``os.replace``
    (atomic on POSIX within one filesystem). On any failure the temporary
    file is removed, so a failed write leaves neither a partial destination
    file nor junk behind; an existing destination file is left untouched.

    Raises :class:`~linkdiscovery.errors.ReportError` on any OS-level failure.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ReportError(f"cannot create report directory {path.parent}: {exc}") from exc
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".partial-", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.replace(path)
    except OSError as exc:
        tmp_path.unlink(missing_ok=True)
        raise ReportError(f"atomic write to {path} failed: {exc}") from exc
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
