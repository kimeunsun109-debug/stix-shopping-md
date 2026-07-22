# -*- coding: utf-8 -*-
"""Competitor Trend Monitor — daily TOP5 snapshot + new keyword alerts."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from seo_engine.engines.competitor import CompetitorAnalyzer
from seo_engine.engines.golden import GoldenKeywordEngine
from seo_engine.keywords import extract_tokens
from seo_engine.models import CollectionBundle

TREND_DIR = Path(__file__).resolve().parent.parent.parent / "seo_history" / "trends"


class CompetitorTrendMonitor:
    def __init__(self, path: Path | None = None) -> None:
        self.dir = path or TREND_DIR
        self.dir.mkdir(parents=True, exist_ok=True)
        self._comp = CompetitorAnalyzer()
        self._golden = GoldenKeywordEngine()

    def _file(self, marketplace: str, keyword: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in keyword)[:40]
        return self.dir / f"{marketplace}__{safe}.json"

    def snapshot(self, bundle: CollectionBundle) -> dict:
        report = self._comp.analyze(bundle)
        today = datetime.now().strftime("%Y-%m-%d")
        keywords = set()
        for t in report.titles:
            keywords.update(extract_tokens(t))
        for k in report.keyword_freq:
            keywords.add(k)

        path = self._file(bundle.marketplace, bundle.keyword)
        history: list = []
        if path.exists():
            try:
                history = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                history = []

        prev_keywords: set[str] = set()
        if history:
            prev_keywords = set(history[-1].get("keywords") or [])

        new_kw = sorted(keywords - prev_keywords) if prev_keywords else []
        rec = {
            "date": today,
            "marketplace": bundle.marketplace,
            "searchKeyword": bundle.keyword,
            "titles": report.titles[:5],
            "keywords": sorted(keywords),
            "repeating": [k for k, _ in report.repeating_keywords[:20]],
            "newKeywords": new_kw,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
        history = [h for h in history if h.get("date") != today]
        history.append(rec)
        history.sort(key=lambda x: x.get("date", ""))
        path.write_text(json.dumps(history[-90:], ensure_ascii=False, indent=2), encoding="utf-8")

        alerts: list[str] = []
        if new_kw:
            # focus on meaningful new core-ish tokens
            notable = [k for k in new_kw if len(k) >= 2][:8]
            if notable:
                alerts.append(
                    f"새로운 핵심 키워드 발견: {', '.join(notable)}"
                )
                cat = bundle.mine.category or bundle.keyword or "default"
                store = self._golden.load()
                bucket = store.setdefault("categories", {}).setdefault(cat, {})
                for k in notable:
                    entry = bucket.setdefault(
                        k,
                        {
                            "success_score": 0.3,
                            "seen": 0,
                            "ctr_delta_pct": 0,
                            "cvr_delta_pct": 0,
                            "rank_delta_sum": 0,
                            "source": "trend",
                        },
                    )
                    entry["seen"] = int(entry.get("seen", 0)) + 1
                    entry["trend_alert"] = today
                    entry["last_stars"] = entry.get("last_stars") or "★★★☆☆"
                    entry["tier"] = entry.get("tier") or "recommend"
                self._golden.save(store)

        return {"path": str(path), "record": rec, "alerts": alerts}
