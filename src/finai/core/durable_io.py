"""Crash-safe file writes.

Windows can leave a file full of null bytes if the PC loses power, sleeps hard or is shut
down right after a write that was still in the disk cache. Writing to a temporary file,
forcing it to disk with fsync, then renaming it over the target means the target always
holds either the old content or the complete new content.
"""

from __future__ import annotations

import os
from pathlib import Path


def write_text_durable(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w", encoding=encoding) as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)
