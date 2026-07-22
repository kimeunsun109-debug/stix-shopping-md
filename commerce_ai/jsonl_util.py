# -*- coding: utf-8 -*-
"""Shared JSONL helpers — mtime-aware in-process cache (behavior-preserving)."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable

_lock = threading.RLock()
# path -> (mtime_ns, size, rows)
_CACHE: dict[str, tuple[int, int, list[dict[str, Any]]]] = {}


def _stat(path: Path) -> tuple[int, int] | None:
    try:
        st = path.stat()
        return int(st.st_mtime_ns), int(st.st_size)
    except OSError:
        return None


def invalidate(path: Path | str) -> None:
    key = str(Path(path).resolve()) if Path(path).exists() else str(path)
    with _lock:
        _CACHE.pop(key, None)
        # also try unresolved
        _CACHE.pop(str(path), None)


def read_jsonl(
    path: Path,
    *,
    skip_corrupt: bool = True,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """Read JSONL into list of dicts. Blank lines skipped; corrupt lines skipped if skip_corrupt."""
    if not path.exists():
        return []
    key = str(path.resolve())
    meta = _stat(path)
    if meta is None:
        return []
    mtime_ns, size = meta
    if use_cache:
        with _lock:
            hit = _CACHE.get(key)
            if hit and hit[0] == mtime_ns and hit[1] == size:
                return hit[2]

    rows: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            if not skip_corrupt:
                raise
            continue

    if use_cache:
        with _lock:
            _CACHE[key] = (mtime_ns, size, rows)
    return rows


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    invalidate(path)


def rewrite_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )
    invalidate(path)


def map_jsonl(
    path: Path,
    fn: Callable[[dict[str, Any]], dict[str, Any] | None],
) -> int:
    """Rewrite file applying fn; None return keeps row. Returns changed count."""
    rows = read_jsonl(path, use_cache=False)
    changed = 0
    out: list[dict[str, Any]] = []
    for row in rows:
        new = fn(row)
        if new is None:
            out.append(row)
        else:
            out.append(new)
            changed += 1
    if changed:
        rewrite_jsonl(path, out)
    return changed


def clear_all_caches() -> None:
    with _lock:
        _CACHE.clear()
