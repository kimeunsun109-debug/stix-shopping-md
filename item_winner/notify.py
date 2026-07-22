# -*- coding: utf-8
"""Price-change alerts (browser + optional Telegram)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

from item_winner.config import B7000_TARGETS
from item_winner.env_util import load_env

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "monitor_history.jsonl"
SENT_FILE = ROOT / "alert_sent.json"
LABELS = {t.key: t.label for t in B7000_TARGETS}


def _fmt_price(n: int | None) -> str:
    if n is None:
        return "-"
    return f"{n:,}원"


def _alert_id(row: dict, kind: str) -> str:
    return f"{row.get('ts')}:{row.get('sku')}:{kind}"


def build_alert_events() -> list[dict]:
    if not HISTORY.exists():
        return []
    prev: dict[str, dict] = {}
    events: list[dict] = []
    for line in HISTORY.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        sku = row.get("sku")
        if not sku:
            continue
        label = LABELS.get(sku, sku)
        old = prev.get(sku)

        if old:
            if row.get("my_price") != old.get("my_price") and row.get("my_price") is not None:
                events.append(
                    {
                        "id": _alert_id(row, "my_price"),
                        "ts": row.get("ts"),
                        "sku": sku,
                        "label": label,
                        "kind": "my_price",
                        "title": f"{label} 내 가격 변경",
                        "body": f"{_fmt_price(old.get('my_price'))} → {_fmt_price(row.get('my_price'))}",
                    }
                )
            if row.get("competitor_price") != old.get("competitor_price") and row.get(
                "competitor_price"
            ) is not None:
                events.append(
                    {
                        "id": _alert_id(row, "competitor"),
                        "ts": row.get("ts"),
                        "sku": sku,
                        "label": label,
                        "kind": "competitor",
                        "title": f"{label} 경쟁자 가격 변경",
                        "body": f"{_fmt_price(old.get('competitor_price'))} → {_fmt_price(row.get('competitor_price'))}",
                    }
                )

        action = row.get("action")
        if action and action != "HOLD" and row.get("applied"):
            events.append(
                {
                    "id": _alert_id(row, "applied"),
                    "ts": row.get("ts"),
                    "sku": sku,
                    "label": label,
                    "kind": "applied",
                    "title": f"{label} Wing 반영",
                    "body": f"{action} → {_fmt_price(row.get('recommended'))}",
                }
            )

        prev[sku] = row

    return events


def recent_alerts(limit: int = 20) -> list[dict]:
    events = build_alert_events()
    return events[-limit:][::-1]


def _load_sent() -> set[str]:
    if not SENT_FILE.exists():
        return set()
    try:
        data = json.loads(SENT_FILE.read_text(encoding="utf-8"))
        return set(data if isinstance(data, list) else [])
    except Exception:
        return set()


def _save_sent(ids: set[str]) -> None:
    keep = sorted(ids)[-500:]
    SENT_FILE.write_text(json.dumps(keep, ensure_ascii=False), encoding="utf-8")


def send_telegram(text: str, env: dict | None = None) -> bool:
    e = env or load_env()
    token = e.get("ITEM_WINNER_TELEGRAM_BOT_TOKEN") or e.get("TELEGRAM_BOT_TOKEN", "")
    chat = e.get("ITEM_WINNER_TELEGRAM_CHAT_ID") or e.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {"chat_id": chat, "text": text, "disable_web_page_preview": "true"}
    ).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception:
        return False


def dispatch_new_alerts(env: dict | None = None) -> int:
    """Send Telegram for alerts not yet sent."""
    e = env or load_env()
    if not (e.get("ITEM_WINNER_TELEGRAM_BOT_TOKEN") or e.get("TELEGRAM_BOT_TOKEN")):
        return 0
    sent = _load_sent()
    new_ids: set[str] = set()
    for alert in build_alert_events():
        aid = alert["id"]
        if aid in sent:
            continue
        msg = f"STIX 가격 알림\n{alert['title']}\n{alert['body']}\n({alert.get('ts', '')})"
        if send_telegram(msg, e):
            new_ids.add(aid)
    if new_ids:
        sent.update(new_ids)
        _save_sent(sent)
    return len(new_ids)
