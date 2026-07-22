# -*- coding: utf-8 -*-
"""Error reporting — never crash the whole OS for a single failure."""
from __future__ import annotations

import json
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from commerce_ai.stability.logging_setup import get_logger

ERROR_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "commerce_history"
    / "error_reports.jsonl"
)


@dataclass
class ErrorReport:
    component: str
    message: str
    error_type: str = ""
    recoverable: bool = True
    context: dict[str, Any] = field(default_factory=dict)
    traceback: str = ""
    ts: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def report_error(
    component: str,
    exc: BaseException | None = None,
    *,
    message: str = "",
    recoverable: bool = True,
    context: dict[str, Any] | None = None,
) -> ErrorReport:
    log = get_logger("commerce_ai.errors")
    msg = message or (str(exc) if exc else "unknown error")
    report = ErrorReport(
        component=component,
        message=msg,
        error_type=type(exc).__name__ if exc else "Error",
        recoverable=recoverable,
        context=context or {},
        traceback="".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        if exc
        else "",
        ts=datetime.now().isoformat(timespec="seconds"),
    )
    try:
        ERROR_PATH.parent.mkdir(parents=True, exist_ok=True)
        with ERROR_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(report.to_dict(), ensure_ascii=False) + "\n")
    except OSError as e:
        log.warning("error report write failed: %s", e)

    level = logging_warning if recoverable else logging_error
    level(log, "[%s] %s", component, msg)
    return report


def logging_warning(log, fmt, *args):
    log.warning(fmt, *args)


def logging_error(log, fmt, *args):
    log.error(fmt, *args)


def recent_errors(limit: int = 20) -> list[dict]:
    if not ERROR_PATH.exists():
        return []
    rows: list[dict] = []
    for line in ERROR_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]
