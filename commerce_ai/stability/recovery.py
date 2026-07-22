# -*- coding: utf-8 -*-
"""Recovery helpers — degrade gracefully when subsystems fail."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from commerce_ai.stability.errors import report_error
from commerce_ai.stability.logging_setup import get_logger

T = TypeVar("T")
_log = get_logger("commerce_ai.recovery")


@dataclass
class RecoveryAction:
    component: str
    strategy: str  # skip|fallback|retry_later|noop
    detail: str = ""


def recover(
    component: str,
    primary: Callable[[], T],
    *,
    fallback: Callable[[], T] | None = None,
    default: T | None = None,
    strategy: str = "fallback",
) -> tuple[T | None, RecoveryAction]:
    try:
        return primary(), RecoveryAction(component, "ok", "primary succeeded")
    except Exception as e:
        report_error(component, e, recoverable=True)
        _log.warning("recovering %s via %s", component, strategy)
        if strategy == "fallback" and fallback is not None:
            try:
                return fallback(), RecoveryAction(
                    component, "fallback", str(e)[:120]
                )
            except Exception as e2:
                report_error(f"{component}.fallback", e2, recoverable=True)
        if strategy == "skip":
            return default, RecoveryAction(component, "skip", str(e)[:120])
        return default, RecoveryAction(component, strategy, str(e)[:120])
