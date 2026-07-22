# -*- coding: utf-8 -*-
"""Async-capable task runner for Collector / Analyzer / Learning / Dashboard."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable, TypeVar

from commerce_ai.stability.logging_setup import get_logger
from commerce_ai.stability.resilience import safe_call

T = TypeVar("T")
_log = get_logger("commerce_ai.async_runtime")


class AsyncRuntime:
    """Thread-pool based async for I/O bound commerce jobs (stdlib only)."""

    def __init__(self, max_workers: int = 4) -> None:
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="commerce_ai"
        )

    def submit(self, fn: Callable[..., T], *args, **kwargs) -> Future:
        return self._pool.submit(fn, *args, **kwargs)

    def map_safe(
        self,
        fn: Callable[..., T],
        items: list,
        *,
        component: str = "async.map",
        default: T | None = None,
    ) -> list[T | None]:
        futures = [
            self.submit(safe_call, fn, item, default=default, component=component)
            for item in items
        ]
        return [f.result() for f in futures]

    def shutdown(self, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait)


_runtime: AsyncRuntime | None = None


def get_runtime() -> AsyncRuntime:
    global _runtime
    if _runtime is None:
        _runtime = AsyncRuntime()
    return _runtime
