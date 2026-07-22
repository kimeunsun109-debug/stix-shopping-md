# -*- coding: utf-8 -*-
"""Daily scheduler — 08:00 AI MD autonomous workflow."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from commerce_ai.stability.errors import report_error
from commerce_ai.stability.logging_setup import get_logger, setup_logging

_log = get_logger("commerce_ai.scheduler")
HISTORY = Path(__file__).resolve().parent.parent / "commerce_history"


def run_daily_job(*, limit: int = 100) -> dict:
    """One full AI MD autonomous cycle."""
    setup_logging()
    from commerce_ai.autonomous import run_autonomous_daily
    from commerce_ai.cache import clear_runtime_caches
    from commerce_ai.dashboard import CommerceDashboard

    _log.info("daily AI MD job start limit=%s", limit)
    result = run_autonomous_daily(batch_limit=limit, skip_batch=False)
    clear_runtime_caches()
    dash = CommerceDashboard().format_text()
    stamp = datetime.now().strftime("%Y%m%d")
    dash_path = HISTORY / "daily" / f"dashboard_{stamp}.txt"
    dash_path.parent.mkdir(parents=True, exist_ok=True)
    dash_path.write_text(dash, encoding="utf-8")
    # also store daily report text next to dashboard
    report_txt = result.get("daily_report_text") or ""
    if report_txt:
        (HISTORY / "daily" / f"AI_MD_Daily_{stamp}.txt").write_text(
            report_txt, encoding="utf-8"
        )
    result["dashboard_path"] = str(dash_path)
    _log.info(
        "daily job done tasks=%s urgent=%s",
        result.get("task_count"),
        len((result.get("board") or {}).get("urgent") or []),
    )
    return result


def seconds_until(hour: int, minute: int = 0) -> float:
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target = target + timedelta(days=1)
    return (target - now).total_seconds()


class DailyScheduler:
    def __init__(
        self,
        *,
        hour: int = 8,
        minute: int = 0,
        limit: int = 100,
        job: Callable[[], dict] | None = None,
    ) -> None:
        self.hour = hour
        self.minute = minute
        self.limit = limit
        self.job = job or (lambda: run_daily_job(limit=self.limit))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_result: dict | None = None

    def start(self, *, run_immediately: bool = False) -> None:
        if self._thread and self._thread.is_alive():
            return

        def loop():
            setup_logging()
            if run_immediately:
                try:
                    self.last_result = self.job()
                except Exception as e:
                    report_error("scheduler.immediate", e, recoverable=True)
            while not self._stop.is_set():
                wait = seconds_until(self.hour, self.minute)
                _log.info(
                    "next AI MD run in %.0fs (%02d:%02d)", wait, self.hour, self.minute
                )
                if self._stop.wait(timeout=min(wait, 3600)):
                    break
                now = datetime.now()
                if now.hour == self.hour and now.minute <= self.minute + 2:
                    try:
                        self.last_result = self.job()
                    except Exception as e:
                        report_error("scheduler.daily", e, recoverable=True)
                    self._stop.wait(timeout=120)

        self._thread = threading.Thread(
            target=loop,
            name="commerce-ai-md-scheduler",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)


def run_forever(
    *, hour: int = 8, minute: int = 0, limit: int = 100, now: bool = False
) -> None:
    sched = DailyScheduler(hour=hour, minute=minute, limit=limit)
    sched.start(run_immediately=now)
    _log.info("AI MD scheduler running — Ctrl+C to stop")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        sched.stop()
