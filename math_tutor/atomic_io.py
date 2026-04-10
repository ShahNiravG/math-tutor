"""Crash-safe file writing helpers.

This module provides small, dependency-free helpers for writing text and JSON
files atomically. The goal is to guarantee that a reader of the destination
path always observes either the previous committed contents or the full new
contents, and never a truncated or partially written file.

Rationale
---------
Long-running generation pipelines in this project persist progress to JSON
state files (``fetch_state.json``, ``generated_output_state.json``, metadata
sidecars, curated exam catalogs). A direct ``path.write_text(...)`` is not
crash-safe: an interruption between truncation and flush can leave the file
empty or partial, silently destroying hours of AI-generation progress. These
helpers implement the canonical write-temp-then-rename pattern so a crash at
any point leaves the original file intact.

Contract
--------
- The temporary file is created in the **same directory** as the destination,
  guaranteeing the final ``os.replace`` is a same-filesystem operation and
  therefore atomic on POSIX and Windows.
- On any failure (encoding error, serialization error, disk-full on write,
  ``os.replace`` error), the temporary file is removed and the original
  destination is left untouched.
- Parent directories of the destination are created on demand, matching the
  behavior of the ad-hoc call sites this helper replaces.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Write ``content`` to ``path`` atomically.

    Args:
        path: Destination file path. Parent directories are created if missing.
        content: Text payload to write.
        encoding: Text encoding for the write. Defaults to UTF-8.

    Raises:
        OSError: If the temporary file cannot be written or the final
            ``os.replace`` into ``path`` fails. In either case the original
            file at ``path`` (if any) is preserved and no temporary file is
            left behind.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_fd, temp_path_str = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temp_path = Path(temp_path_str)
    try:
        with os.fdopen(temp_fd, "w", encoding=encoding) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except BaseException:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def atomic_write_json(
    path: Path,
    payload: Any,
    *,
    indent: int | None = None,
) -> None:
    """Serialize ``payload`` as JSON and write it to ``path`` atomically.

    Args:
        path: Destination file path. Parent directories are created if missing.
        payload: JSON-serializable object.
        indent: Optional indent passed through to :func:`json.dumps`.

    Raises:
        TypeError: If ``payload`` is not JSON-serializable. The destination
            file is not modified.
        OSError: If the underlying atomic write fails. The destination file
            is not modified.
    """
    serialized = json.dumps(payload, indent=indent)
    atomic_write_text(path, serialized)
