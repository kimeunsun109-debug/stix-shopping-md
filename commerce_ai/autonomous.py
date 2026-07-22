# -*- coding: utf-8 -*-
"""
Autonomous AI MD workflow — daily scan → opportunities → priorities → report.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from commerce_ai.batch_ops import load_recent_snapshots, run_batch
from commerce_ai.cache import clear_runtime_caches
from commerce_ai.container import get_container
from commerce_ai.opportunity import OpportunityEngine
from commerce_ai.ops_catalog import catalog_stats
from commerce_ai.priority import PriorityEngine
from commerce_ai.reports import ReportEngine
from commerce_ai.self_eval import SelfEvaluationEngine
from commerce_ai.stability.logging_setup import get_logger, setup_logging

HISTORY = Path(__file__).resolve().parent.parent / "commerce_history"
_log = get_logger("commerce_ai.autonomous")


def run_autonomous_daily(
    *,
    batch_limit: int = 100,
    skip_batch: bool = False,
) -> dict[str, Any]:
    """
    Full AI MD morning workflow:
      scan → intelligence (batch) → problems/opportunities → priority → dashboard/report
    """
    setup_logging()
    _log.info("AI MD autonomous daily start")

    catalog = catalog_stats()
    batch_summary: dict[str, Any] = {}
    if not skip_batch:
        batch_summary = run_batch(
            limit=batch_limit, save_memory=True, open_verification=True
        )

    clear_runtime_caches()
    snaps = load_recent_snapshots(1000)
    today = datetime.now().strftime("%Y-%m-%d")
    today_snaps = [s for s in snaps if s.get("date") == today] or snaps[-batch_limit:]

    opps = OpportunityEngine().detect(today_snaps)
    c = get_container()
    due = c.verification.due() if c.verification else []
    tasks = PriorityEngine().rank(opps, verify_due=due, limit=50)
    daily = ReportEngine().build_daily(snapshots=today_snaps, save=True)
    self_eval = SelfEvaluationEngine().evaluate()

    # monday weekly / month-start monthly
    extras: dict[str, Any] = {}
    now = datetime.now()
    if now.weekday() == 0:  # Monday
        extras["weekly"] = ReportEngine().build_weekly(save=True)
    if now.day == 1:
        extras["monthly"] = ReportEngine().build_monthly(save=True)

    # today-first board payload
    board = {
        "urgent": [t.to_dict() for t in tasks if t.lane == "urgent"],
        "high": [t.to_dict() for t in tasks if t.lane == "high"],
        "normal": [t.to_dict() for t in tasks if t.lane == "normal"],
        "verify": [t.to_dict() for t in tasks if t.lane == "verify"],
        "done": [],
    }

    result = {
        "version": "7.0",
        "date": today,
        "catalog_total": catalog.get("total_valid"),
        "batch": {
            "analyzed": batch_summary.get("analyzed", 0 if skip_batch else None),
            "errors": batch_summary.get("errors", 0),
            "report_path": batch_summary.get("report_path"),
        },
        "daily_report": daily.to_dict(),
        "daily_report_text": daily.text,
        "board": board,
        "self_evaluation": self_eval.to_dict(),
        "opportunity_count": len(opps),
        "task_count": len(tasks),
        **extras,
    }

    # persist board for dashboard
    out = HISTORY / "daily" / f"board_{now.strftime('%Y%m%d')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    import json

    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["board_path"] = str(out)
    _log.info(
        "AI MD daily done tasks=%s urgent=%s accuracy=%s",
        len(tasks),
        len(board["urgent"]),
        self_eval.accuracy_pct,
    )
    return result


def today_board() -> dict[str, Any]:
    """Fast board from latest snapshots (no full batch)."""
    return run_autonomous_daily(skip_batch=True)
