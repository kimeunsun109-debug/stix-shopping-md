# -*- coding: utf-8 -*-
"""Ranking Monitor — daily rank snapshots + drop detection."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

RANK_DIR = Path(__file__).resolve().parent.parent.parent / "seo_history" / "ranks"


class RankingMonitor:
    def __init__(self, path: Path | None = None) -> None:
        self.dir = path or RANK_DIR
        self.dir.mkdir(parents=True, exist_ok=True)

    def _file(self, product_id: str, keyword: str) -> Path:
        safe_kw = "".join(c if c.isalnum() or c in "-_" else "_" for c in keyword)[:40]
        return self.dir / f"{product_id or 'unknown'}__{safe_kw}.json"

    def record(
        self,
        *,
        product_id: str,
        keyword: str,
        rank: int | None,
        title: str = "",
        source: str = "manual",
    ) -> dict:
        path = self._file(product_id, keyword)
        records: list = []
        if path.exists():
            try:
                records = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                records = []
        today = datetime.now().strftime("%Y-%m-%d")
        # upsert today
        records = [r for r in records if r.get("date") != today]
        rec = {
            "date": today,
            "rank": rank,
            "title": title,
            "keyword": keyword,
            "productId": product_id,
            "source": source,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
        records.append(rec)
        records.sort(key=lambda r: r.get("date", ""))
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"path": str(path), "record": rec, "alert": self.detect_drop(records)}

    def detect_drop(self, records: list[dict], threshold: int = 3) -> dict | None:
        ranked = [r for r in records if isinstance(r.get("rank"), int)]
        if len(ranked) < 2:
            return None
        prev, curr = ranked[-2], ranked[-1]
        before, after = prev["rank"], curr["rank"]
        if after > before + threshold - 1:
            return {
                "type": "rank_drop",
                "rankBefore": before,
                "rankAfter": after,
                "delta": after - before,
                "message": f"순위 하락 감지: {before}위 -> {after}위 (자동 분석 권장)",
                "should_analyze": True,
            }
        return None

    def latest(self, product_id: str, keyword: str) -> list[dict]:
        path = self._file(product_id, keyword)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
