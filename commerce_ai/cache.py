# -*- coding: utf-8 -*-
"""Simple TTL cache — avoid duplicate Analyzer/Dashboard computations."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any, Callable, Hashable, TypeVar

T = TypeVar("T")


class TtlCache:
    def __init__(self, default_ttl_sec: float = 120.0) -> None:
        self.default_ttl = default_ttl_sec
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def _key(self, namespace: str, payload: Hashable | dict | list) -> str:
        if isinstance(payload, (dict, list)):
            raw = json.dumps(payload, sort_keys=True, default=str)
        else:
            raw = str(payload)
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
        return f"{namespace}:{digest}"

    def get(self, namespace: str, payload: Hashable | dict | list) -> Any | None:
        key = self._key(namespace, payload)
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            expires, value = item
            if time.monotonic() > expires:
                del self._store[key]
                return None
            return value

    def set(
        self,
        namespace: str,
        payload: Hashable | dict | list,
        value: Any,
        ttl_sec: float | None = None,
    ) -> None:
        key = self._key(namespace, payload)
        ttl = self.default_ttl if ttl_sec is None else ttl_sec
        with self._lock:
            self._store[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def get_or_set(
        self,
        namespace: str,
        payload: Hashable | dict | list,
        factory: Callable[[], T],
        ttl_sec: float | None = None,
    ) -> T:
        hit = self.get(namespace, payload)
        if hit is not None:
            return hit
        value = factory()
        self.set(namespace, payload, value, ttl_sec=ttl_sec)
        return value


# process-wide cache
CACHE = TtlCache(default_ttl_sec=180.0)


def clear_runtime_caches() -> None:
    """Clear TTL cache + JSONL in-process caches after writes/batch."""
    CACHE.clear()
    try:
        from commerce_ai.jsonl_util import clear_all_caches

        clear_all_caches()
    except Exception:
        pass
