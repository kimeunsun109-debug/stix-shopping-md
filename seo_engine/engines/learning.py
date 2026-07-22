# -*- coding: utf-8 -*-
"""Self Learning — track 7/14/30d outcomes; feed Golden Keyword Engine."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from seo_engine.engines.golden import GoldenKeywordEngine

LEARN_DIR = Path(__file__).resolve().parent.parent.parent / "seo_history"
LEARN_PATH = LEARN_DIR / "learning_events.jsonl"
SUCCESS_PATH = LEARN_DIR / "learning_success.jsonl"


class SelfLearningEngine:
    WINDOWS = (7, 14, 30)

    def __init__(self) -> None:
        LEARN_DIR.mkdir(parents=True, exist_ok=True)
        self.golden = GoldenKeywordEngine()

    def log_change(
        self,
        *,
        product_id: str,
        keyword: str,
        category: str,
        title: str,
        added_keywords: list[str],
        removed_keywords: list[str],
        seo_score: int,
        rank_before: int | None,
    ) -> dict:
        event = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "ts": datetime.now().isoformat(timespec="seconds"),
            "productId": product_id,
            "keyword": keyword,
            "category": category,
            "title": title,
            "addedKeywords": added_keywords,
            "removedKeywords": removed_keywords,
            "seoScore": seo_score,
            "rankBefore": rank_before,
            "checkpoints": {str(d): None for d in self.WINDOWS},
        }
        with LEARN_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def update_checkpoint(
        self,
        product_id: str,
        keyword: str,
        change_date: str,
        days: int,
        rank_after: int,
    ) -> list[str]:
        """Fill 7/14/30 checkpoint when rank is observed; learn on success."""
        notes: list[str] = []
        if not LEARN_PATH.exists():
            return notes
        lines = LEARN_PATH.read_text(encoding="utf-8").splitlines()
        updated: list[str] = []
        for line in lines:
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except Exception:
                updated.append(line)
                continue
            if (
                ev.get("productId") == product_id
                and ev.get("keyword") == keyword
                and ev.get("date") == change_date
            ):
                cps = ev.setdefault("checkpoints", {})
                cps[str(days)] = rank_after
                before = ev.get("rankBefore")
                if isinstance(before, int) and rank_after < before:
                    self._record_success(ev, rank_after, days)
                    notes.append(
                        f"{days}일 학습: 순위 {before}->{rank_after} 개선, "
                        f"키워드 {ev.get('addedKeywords', [])[:5]} 강화"
                    )
                ev["checkpoints"] = cps
            updated.append(json.dumps(ev, ensure_ascii=False))
        LEARN_PATH.write_text("\n".join(updated) + ("\n" if updated else ""), encoding="utf-8")
        return notes

    def _record_success(self, ev: dict, rank_after: int, days: int) -> None:
        before = ev.get("rankBefore")
        payload = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "windowDays": days,
            "productId": ev.get("productId"),
            "keyword": ev.get("keyword"),
            "title": ev.get("title"),
            "keywords": ev.get("addedKeywords", []),
            "rankBefore": before,
            "rankAfter": rank_after,
        }
        with SUCCESS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        if isinstance(before, int):
            self.golden.record_success(
                ev.get("category") or ev.get("keyword") or "default",
                list(ev.get("addedKeywords") or []),
                rank_before=before,
                rank_after=rank_after,
            )

    def due_checkpoints(self, today: datetime | None = None) -> list[dict]:
        """List learning events that need 7/14/30 rank checks."""
        today = today or datetime.now()
        due = []
        if not LEARN_PATH.exists():
            return due
        for line in LEARN_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            try:
                start = datetime.strptime(ev["date"], "%Y-%m-%d")
            except Exception:
                continue
            cps = ev.get("checkpoints") or {}
            for d in self.WINDOWS:
                if cps.get(str(d)) is None and today.date() >= (start + timedelta(days=d)).date():
                    due.append({**ev, "dueDays": d})
        return due

    def notes_for_product(self, product_id: str) -> list[str]:
        notes = []
        if SUCCESS_PATH.exists():
            for line in SUCCESS_PATH.read_text(encoding="utf-8").splitlines()[-20:]:
                try:
                    s = json.loads(line)
                except Exception:
                    continue
                if s.get("productId") == product_id:
                    notes.append(
                        f"성공패턴: {s.get('title','')[:40]} | "
                        f"{s.get('rankBefore')}->{s.get('rankAfter')} | "
                        f"{', '.join((s.get('keywords') or [])[:5])}"
                    )
        return notes[:10]
