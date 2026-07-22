# -*- coding: utf-8 -*-
"""Competitor Intelligence — daily TOP snapshot + change detection."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from seo_engine.engines.competitor import CompetitorAnalyzer
from seo_engine.keywords import extract_tokens
from seo_engine.models import CollectionBundle

STORE = Path(__file__).resolve().parent.parent.parent / "commerce_history" / "competitors"


class CompetitorIntelligence:
    def __init__(self, path: Path | None = None) -> None:
        self.dir = path or STORE
        self.dir.mkdir(parents=True, exist_ok=True)
        self._comp = CompetitorAnalyzer()

    def _file(self, marketplace: str, keyword: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in keyword)[:40]
        return self.dir / f"{marketplace}__{safe}.json"

    def analyze(self, bundle: CollectionBundle) -> tuple[list[str], list[str]]:
        """Returns (summaries, change_notes). Also persists daily snapshot."""
        report = self._comp.analyze(bundle)
        today = datetime.now().strftime("%Y-%m-%d")
        snap = {
            "date": today,
            "marketplace": bundle.marketplace,
            "keyword": bundle.keyword,
            "items": [
                {
                    "rank": c.rank,
                    "title": c.title,
                    "price": c.price,
                    "brand": c.brand,
                    "reviews": c.review_count,
                    "rating": c.rating,
                    "tokens": extract_tokens(c.title),
                }
                for c in bundle.competitors[:5]
            ],
            "repeating": [k for k, _ in report.repeating_keywords[:15]],
            "ts": datetime.now().isoformat(timespec="seconds"),
        }

        path = self._file(bundle.marketplace, bundle.keyword)
        hist: list = []
        if path.exists():
            try:
                hist = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                hist = []

        changes: list[str] = []
        if hist:
            prev = hist[-1]
            prev_titles = {i.get("title") for i in prev.get("items") or []}
            curr_titles = {i.get("title") for i in snap["items"]}
            new_products = curr_titles - prev_titles
            gone = prev_titles - curr_titles
            if new_products:
                changes.append(f"신규 상위 진입: {list(new_products)[0][:40]}")
            if gone:
                changes.append(f"상위 이탈: {list(gone)[0][:40]}")

            prev_prices = {
                i.get("title"): i.get("price") for i in (prev.get("items") or [])
            }
            for it in snap["items"]:
                t = it.get("title")
                if t in prev_prices and prev_prices[t] and it.get("price"):
                    if it["price"] != prev_prices[t]:
                        changes.append(
                            f"가격 변동: {t[:30]} {prev_prices[t]}->{it['price']}"
                        )

            prev_kw = set(prev.get("repeating") or [])
            curr_kw = set(snap["repeating"] or [])
            new_kw = sorted(curr_kw - prev_kw)
            if new_kw:
                changes.append(f"신규 반복 키워드: {', '.join(new_kw[:5])}")

            # OOS heuristic: review spike drop or missing
            for it in prev.get("items") or []:
                if it.get("title") not in curr_titles and it.get("rank") and it["rank"] <= 3:
                    changes.append(f"경쟁 TOP3 이탈(품절 가능): {it.get('title','')[:35]}")

        hist = [h for h in hist if h.get("date") != today]
        hist.append(snap)
        path.write_text(json.dumps(hist[-60:], ensure_ascii=False, indent=2), encoding="utf-8")

        return report.summaries, changes
