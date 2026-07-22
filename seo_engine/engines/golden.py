# -*- coding: utf-8 -*-
"""Golden Keyword Engine v3 — volume/competition/CTR/CVR/rank learning."""
from __future__ import annotations

import json
from pathlib import Path

from seo_engine.engines.gap import GapReport
from seo_engine.engines.keyword_extractor import ExtractedKeyword
from seo_engine.keywords import stars_to_tier
from seo_engine.models import CollectionBundle, GoldenKeyword

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GOLDEN_PATH = DATA_DIR / "golden_keywords.json"


class GoldenKeywordEngine:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or GOLDEN_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, category: str = "default") -> dict:
        if not self.path.exists():
            return {"categories": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"categories": {}}

    def save(self, store: dict) -> None:
        self.path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

    def build(
        self,
        bundle: CollectionBundle,
        extracted: list[ExtractedKeyword],
        gap: GapReport,
        *,
        category: str = "",
    ) -> list[GoldenKeyword]:
        cat = category or bundle.mine.category or bundle.keyword or "default"
        store = self.load()
        learned = store.get("categories", {}).get(cat, {})

        out: list[GoldenKeyword] = []
        seen: set[str] = set()

        for e in extracted:
            if e.keyword in seen:
                continue
            stars = e.importance
            entry = learned.get(e.keyword, {})
            boost = float(entry.get("success_score", 0))
            ctr_d = entry.get("ctr_delta_pct")
            cvr_d = entry.get("cvr_delta_pct")
            rank_d = entry.get("rank_delta_sum")
            if boost >= 2:
                stars = "★★★★★"
            elif boost >= 1 and stars in {"★★★☆☆", "★★☆☆☆"}:
                stars = "★★★★☆"
            tier = stars_to_tier(stars)
            if e.keyword in gap.delete_candidates:
                stars, tier = "★☆☆☆☆", "delete"

            effect_parts = [
                f"검색량 {e.search_volume}",
                f"경쟁도 {e.competition}",
                f"효과점수 {e.effect}",
            ]
            if ctr_d is not None and float(ctr_d) != 0:
                effect_parts.append(f"CTR {float(ctr_d):+.0f}%")
            if cvr_d is not None and float(cvr_d) != 0:
                effect_parts.append(f"CVR {float(cvr_d):+.0f}%")
            if rank_d is not None and float(rank_d) != 0:
                effect_parts.append(f"순위 {float(rank_d):+.0f}")

            out.append(
                GoldenKeyword(
                    keyword=e.keyword,
                    stars=stars,
                    tier=tier,
                    score=e.coverage_ratio + boost * 0.1 + e.effect / 200,
                    reason=f"경쟁출현 {e.frequency}/{max(len(bundle.competitors),1)} | "
                    + " | ".join(effect_parts),
                    search_volume=e.search_volume,
                    competition=e.competition,
                    effect="; ".join(effect_parts),
                    ctr_delta_pct=float(ctr_d) if ctr_d is not None else None,
                    cvr_delta_pct=float(cvr_d) if cvr_d is not None else None,
                    rank_delta=int(rank_d) if rank_d is not None else None,
                )
            )
            seen.add(e.keyword)

        for d in gap.delete_candidates:
            if d in seen:
                continue
            out.append(
                GoldenKeyword(
                    keyword=d,
                    stars="★☆☆☆☆",
                    tier="delete",
                    score=0.0,
                    reason="경쟁 빈도 0 / 노이즈",
                    search_volume="낮음",
                    competition="낮음",
                    effect="삭제 추천",
                )
            )
            seen.add(d)

        out.sort(key=lambda g: (-g.score, g.keyword))
        self._upsert_dict(store, cat, out, extracted)
        return out[:40]

    def _upsert_dict(
        self,
        store: dict,
        cat: str,
        items: list[GoldenKeyword],
        extracted: list[ExtractedKeyword],
    ) -> None:
        cats = store.setdefault("categories", {})
        bucket = cats.setdefault(cat, {})
        vol_map = {e.keyword: e for e in extracted}
        for g in items:
            entry = bucket.setdefault(
                g.keyword,
                {
                    "success_score": 0,
                    "seen": 0,
                    "ctr_delta_pct": 0,
                    "cvr_delta_pct": 0,
                    "rank_delta_sum": 0,
                },
            )
            entry["seen"] = int(entry.get("seen", 0)) + 1
            entry["last_stars"] = g.stars
            entry["tier"] = g.tier
            if g.keyword in vol_map:
                e = vol_map[g.keyword]
                entry["search_volume"] = e.search_volume
                entry["competition"] = e.competition
                entry["effect"] = e.effect
        self.save(store)

    def record_success(
        self,
        category: str,
        keywords: list[str],
        *,
        rank_before: int,
        rank_after: int,
        ctr_before: float | None = None,
        ctr_after: float | None = None,
        cvr_before: float | None = None,
        cvr_after: float | None = None,
    ) -> None:
        if rank_after >= rank_before and not (
            ctr_after is not None
            and ctr_before is not None
            and ctr_after > ctr_before
        ):
            if not (
                cvr_after is not None
                and cvr_before is not None
                and cvr_after > cvr_before
            ):
                if rank_after >= rank_before:
                    return

        store = self.load()
        bucket = store.setdefault("categories", {}).setdefault(category or "default", {})
        gain = max(0, rank_before - rank_after)
        ctr_d = None
        cvr_d = None
        if ctr_before is not None and ctr_after is not None and ctr_before > 0:
            ctr_d = (ctr_after - ctr_before) / ctr_before * 100
        if cvr_before is not None and cvr_after is not None and cvr_before > 0:
            cvr_d = (cvr_after - cvr_before) / cvr_before * 100

        for kw in keywords:
            entry = bucket.setdefault(
                kw,
                {
                    "success_score": 0,
                    "seen": 0,
                    "ctr_delta_pct": 0,
                    "cvr_delta_pct": 0,
                    "rank_delta_sum": 0,
                },
            )
            entry["success_score"] = float(entry.get("success_score", 0)) + max(1, gain) * 0.5
            if gain:
                entry["rank_delta_sum"] = float(entry.get("rank_delta_sum", 0)) + gain
            if ctr_d is not None:
                entry["ctr_delta_pct"] = round(
                    (float(entry.get("ctr_delta_pct", 0)) + ctr_d) / 2, 1
                )
            if cvr_d is not None:
                entry["cvr_delta_pct"] = round(
                    (float(entry.get("cvr_delta_pct", 0)) + cvr_d) / 2, 1
                )
        self.save(store)
