"""Exclusive, no-follow atomic JSON writes."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def atomic_replace_json(path: Path, data: Any) -> None:
    """Write `data` as JSON via an exclusive O_NOFOLLOW temp file, then replace.

    A leftover ``.tmp`` that is a symlink is unlinked (the link itself) before
    the exclusive create, so the write cannot follow an attacker-controlled path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        os.unlink(tmp)
    except FileNotFoundError:
        pass
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
