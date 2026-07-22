# -*- coding: utf-8 -*-
"""Retry, timeout, rate limit, circuit guard, safe_call."""
from __future__ import annotations

import functools
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

from commerce_ai.stability.errors import report_error
from commerce_ai.stability.logging_setup import get_logger

T = TypeVar("T")
_log = get_logger("commerce_ai.resilience")


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_sec: float = 0.4
    max_delay_sec: float = 8.0
    exponential: bool = True
    retry_on: tuple[type[BaseException], ...] = (Exception,)


@dataclass
class RateLimiter:
    """Simple token-bucket style limiter (calls per window)."""

    max_calls: int = 30
    period_sec: float = 60.0
    _times: list[float] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def acquire(self, timeout: float = 10.0) -> bool:
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                now = time.monotonic()
                self._times = [t for t in self._times if now - t < self.period_sec]
                if len(self._times) < self.max_calls:
                    self._times.append(now)
                    return True
                wait = self.period_sec - (now - self._times[0]) + 0.01
            if time.monotonic() + wait > deadline:
                return False
            time.sleep(min(wait, 0.5))


@dataclass
class CircuitState:
    failures: int = 0
    opened_until: float = 0.0
    threshold: int = 5
    cooldown_sec: float = 30.0


_circuits: dict[str, CircuitState] = {}
_circuits_lock = threading.Lock()


def circuit_guard(name: str, *, threshold: int = 5, cooldown_sec: float = 30.0):
    """Decorator: open circuit after N failures; fail soft while open."""

    def deco(fn: Callable[..., T]) -> Callable[..., T | None]:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with _circuits_lock:
                st = _circuits.setdefault(
                    name,
                    CircuitState(threshold=threshold, cooldown_sec=cooldown_sec),
                )
                now = time.monotonic()
                if st.opened_until > now:
                    _log.warning("circuit open: %s (%.0fs left)", name, st.opened_until - now)
                    return None
            try:
                result = fn(*args, **kwargs)
                with _circuits_lock:
                    st.failures = 0
                return result
            except Exception as e:
                with _circuits_lock:
                    st.failures += 1
                    if st.failures >= st.threshold:
                        st.opened_until = time.monotonic() + st.cooldown_sec
                        st.failures = 0
                        _log.error("circuit opened: %s", name)
                report_error(name, e, recoverable=True)
                return None

        return wrapper

    return deco


def run_with_timeout(
    fn: Callable[..., T],
    *args,
    timeout_sec: float = 30.0,
    default: T | None = None,
    component: str = "timeout",
    **kwargs,
) -> T | None:
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(fn, *args, **kwargs)
        try:
            return fut.result(timeout=timeout_sec)
        except FuturesTimeout:
            report_error(
                component,
                message=f"timeout after {timeout_sec}s",
                recoverable=True,
            )
            return default
        except Exception as e:
            report_error(component, e, recoverable=True)
            return default


def with_retry(
    fn: Callable[..., T],
    *args,
    policy: RetryPolicy | None = None,
    component: str = "retry",
    **kwargs,
) -> T:
    policy = policy or RetryPolicy()
    last: BaseException | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return fn(*args, **kwargs)
        except policy.retry_on as e:
            last = e
            if attempt >= policy.max_attempts:
                break
            delay = policy.base_delay_sec
            if policy.exponential:
                delay = min(
                    policy.max_delay_sec,
                    policy.base_delay_sec * (2 ** (attempt - 1)),
                )
            _log.warning(
                "%s attempt %s/%s failed: %s — retry in %.1fs",
                component,
                attempt,
                policy.max_attempts,
                e,
                delay,
            )
            time.sleep(delay)
    assert last is not None
    report_error(component, last, recoverable=False)
    raise last


def safe_call(
    fn: Callable[..., T],
    *args,
    default: T | None = None,
    component: str = "safe_call",
    timeout_sec: float | None = None,
    retry: RetryPolicy | None = None,
    rate_limiter: RateLimiter | None = None,
    **kwargs,
) -> T | None:
    """Never raises — logs and returns default on failure."""

    def _inner() -> T:
        if rate_limiter is not None and not rate_limiter.acquire():
            raise TimeoutError(f"rate limit exceeded: {component}")
        if retry is not None:
            return with_retry(fn, *args, policy=retry, component=component, **kwargs)
        return fn(*args, **kwargs)

    try:
        if timeout_sec is not None:
            return run_with_timeout(
                _inner,
                timeout_sec=timeout_sec,
                default=default,
                component=component,
            )
        return _inner()
    except Exception as e:
        report_error(component, e, recoverable=True)
        return default
