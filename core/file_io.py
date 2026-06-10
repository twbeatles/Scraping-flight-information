"""Small file I/O helpers shared by local JSON persistence."""

from __future__ import annotations

import os
import tempfile


def write_text_atomic(filepath: str, text: str, *, encoding: str = "utf-8") -> None:
    directory = os.path.dirname(os.path.abspath(filepath)) or "."
    os.makedirs(directory, exist_ok=True)
    prefix = f".{os.path.basename(filepath)}."
    fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, filepath)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
