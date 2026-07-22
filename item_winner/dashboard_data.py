# -*- coding: utf-8
"""Aggregate item-winner monitor data for mobile dashboard."""
from __future__ import annotations

import json
import re
import socket
from datetime import datetime, timedelta
from pathlib import Path

from item_winner.config import B7000_TARGETS, INTERVAL_SEC, MONITOR_UNTIL
from item_winner.notify import dispatch_new_alerts, recent_alerts
from item_winner.tunnel import read_public_url

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "monitor_history.jsonl"
LOG = ROOT / "monitor.log"

SKU_LABELS = {t.key: t.label for t in B7000_TARGETS}


def local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def _parse_log_ts(line: str) -> datetime | None:
    m = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", line)
    if not m:
        return None
    return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")


def load_recent_log(limit: int = 40) -> list[str]:
    if not LOG.exists():
        return []
    lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-limit:]


def load_latest_by_sku() -> dict[str, dict]:
    latest: dict[str, dict] = {}
    if not HISTORY.exists():
        return latest
    for line in HISTORY.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        sku = row.get("sku")
        if sku:
            latest[sku] = row
    return latest


def monitor_health() -> dict:
    now = datetime.now()
    end = datetime.fromisoformat(MONITOR_UNTIL) if MONITOR_UNTIL else None
    lines = load_recent_log(200)
    last_ts: datetime | None = None
    last_cycle: datetime | None = None
    for line in reversed(lines):
        ts = _parse_log_ts(line)
        if ts and last_ts is None:
            last_ts = ts
        if ts and "=== cycle end ===" in line:
            last_cycle = ts
            break
    stale_min = INTERVAL_SEC // 60 + 15
    alive = bool(last_ts and (now - last_ts) < timedelta(minutes=stale_min))
    return {
        "alive": alive,
        "last_log_at": last_ts.isoformat(timespec="seconds") if last_ts else None,
        "last_cycle_at": last_cycle.isoformat(timespec="seconds") if last_cycle else None,
        "monitor_until": MONITOR_UNTIL or "continuous",
        "days_left": max(0, (end - now).days) if end else None,
        "interval_min": INTERVAL_SEC // 60,
    }


def build_status() -> dict:
    latest = load_latest_by_sku()
    skus = []
    for target in B7000_TARGETS:
        row = latest.get(target.key, {})
        skus.append(
            {
                "key": target.key,
                "label": target.label,
                "my_price": row.get("my_price"),
                "competitor_price": row.get("competitor_price"),
                "is_winner": row.get("is_winner"),
                "action": row.get("action", "-"),
                "recommended": row.get("recommended"),
                "applied": row.get("applied"),
                "reason": row.get("reason", ""),
                "updated_at": row.get("ts"),
                "hold_price": target.hold_price,
                "reactive_lower_only": target.reactive_lower_only,
            }
        )
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "health": monitor_health(),
        "skus": skus,
        "recent_log": load_recent_log(25),
        "alerts": recent_alerts(15),
        "public_url": read_public_url(),
        "local_url": f"http://{local_ip()}:{8765}/",
    }
