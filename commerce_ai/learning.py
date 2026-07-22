# -*- coding: utf-8 -*-
"""Commerce Learning Engine — 7/14/30d checkpoints for all action types."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from commerce_ai.jsonl_util import append_jsonl, read_jsonl
from commerce_ai.memory import CommerceMemory
from commerce_ai.stability.logging_setup import get_logger

LEARN_DIR = Path(__file__).resolve().parent.parent / "commerce_history"
LEARN_PATH = LEARN_DIR / "learning_events.jsonl"
SUCCESS_PATH = LEARN_DIR / "learning_success.jsonl"
_log = get_logger("commerce_ai.learning")


class CommerceLearningEngine:
    WINDOWS = (7, 14, 30)

    def __init__(self) -> None:
        LEARN_DIR.mkdir(parents=True, exist_ok=True)
        self.memory = CommerceMemory()

    def log_change(
        self,
        *,
        product_id: str,
        marketplace: str,
        keyword: str,
        actions: list[str],
        seo_score: int,
        revenue_score: int,
        rank_before: int | None,
        snapshot: dict | None = None,
    ) -> dict:
        event = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "ts": datetime.now().isoformat(timespec="seconds"),
            "productId": product_id,
            "marketplace": marketplace,
            "keyword": keyword,
            "actions": actions,
            "seoScore": seo_score,
            "revenueScore": revenue_score,
            "rankBefore": rank_before,
            "snapshot": snapshot or {},
            "checkpoints": {str(d): None for d in self.WINDOWS},
        }
        try:
            append_jsonl(LEARN_PATH, event)
            _log.debug("learning.log_change product=%s", product_id)
        except OSError:
            _log.warning("learning.log_change write failed product=%s", product_id)
        return event

    def due_checkpoints(self, today: datetime | None = None) -> list[dict]:
        today = today or datetime.now()
        due = []
        for ev in read_jsonl(LEARN_PATH):
            try:
                start = datetime.strptime(ev["date"], "%Y-%m-%d")
            except Exception:
                continue
            cps = ev.get("checkpoints") or {}
            for d in self.WINDOWS:
                if cps.get(str(d)) is None and today.date() >= (
                    start + timedelta(days=d)
                ).date():
                    due.append({**ev, "dueDays": d})
        return due

    def notes_for_product(self, product_id: str) -> list[str]:
        notes = []
        rows = read_jsonl(SUCCESS_PATH)
        for s in rows[-15:]:
            if s.get("productId") == product_id:
                notes.append(
                    f"성공패턴: {', '.join(s.get('actions') or [])} | "
                    f"{s.get('metric')} {s.get('lift')}%"
                )
        notes.extend(self.memory.lessons(product_id, limit=5))
        return notes[:10]
