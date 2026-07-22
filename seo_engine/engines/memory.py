# -*- coding: utf-8 -*-
"""SEO Memory — record why each change happened and what it caused."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / "seo_history"
MEMORY_PATH = MEMORY_DIR / "seo_memory.jsonl"


class SeoMemory:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or MEMORY_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        product_id: str,
        keyword: str,
        action: str,
        reason: str,
        keywords: list[str] | None = None,
        rank_before: int | None = None,
        rank_after: int | None = None,
        ctr_before: float | None = None,
        ctr_after: float | None = None,
        cvr_before: float | None = None,
        cvr_after: float | None = None,
        marketplace: str = "coupang",
    ) -> dict:
        ctr_delta = None
        cvr_delta = None
        if ctr_before is not None and ctr_after is not None and ctr_before > 0:
            ctr_delta = round((ctr_after - ctr_before) / ctr_before * 100, 1)
        if cvr_before is not None and cvr_after is not None and cvr_before > 0:
            cvr_delta = round((cvr_after - cvr_before) / cvr_before * 100, 1)
        rank_delta = None
        if rank_before is not None and rank_after is not None:
            rank_delta = rank_before - rank_after  # positive = improved

        entry = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "ts": datetime.now().isoformat(timespec="seconds"),
            "productId": product_id,
            "keyword": keyword,
            "marketplace": marketplace,
            "action": action,
            "reason": reason,
            "keywords": keywords or [],
            "rankBefore": rank_before,
            "rankAfter": rank_after,
            "rankDelta": rank_delta,
            "ctrDeltaPct": ctr_delta,
            "cvrDeltaPct": cvr_delta,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def lessons(self, product_id: str = "", limit: int = 15) -> list[str]:
        if not self.path.exists():
            return []
        notes: list[str] = []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if product_id and e.get("productId") != product_id:
                continue
            bits = [e.get("action", ""), e.get("reason", "")]
            if e.get("ctrDeltaPct") is not None:
                bits.append(f"CTR {e['ctrDeltaPct']:+.0f}%")
            if e.get("cvrDeltaPct") is not None:
                bits.append(f"CVR {e['cvrDeltaPct']:+.0f}%")
            if e.get("rankDelta") is not None:
                bits.append(f"순위 {e['rankDelta']:+d}")
            notes.append(" | ".join(b for b in bits if b))
            if len(notes) >= limit:
                break
        return notes

    def keyword_effects(self, category_hint: str = "") -> dict[str, dict]:
        """Aggregate memory into keyword -> effect map for Learning/Golden."""
        agg: dict[str, dict] = {}
        if not self.path.exists():
            return agg
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            for kw in e.get("keywords") or []:
                a = agg.setdefault(
                    kw, {"ctr": [], "cvr": [], "rank": [], "count": 0}
                )
                a["count"] += 1
                if e.get("ctrDeltaPct") is not None:
                    a["ctr"].append(e["ctrDeltaPct"])
                if e.get("cvrDeltaPct") is not None:
                    a["cvr"].append(e["cvrDeltaPct"])
                if e.get("rankDelta") is not None:
                    a["rank"].append(e["rankDelta"])
        out = {}
        for kw, a in agg.items():
            out[kw] = {
                "count": a["count"],
                "avg_ctr": round(sum(a["ctr"]) / len(a["ctr"]), 1) if a["ctr"] else None,
                "avg_cvr": round(sum(a["cvr"]) / len(a["cvr"]), 1) if a["cvr"] else None,
                "avg_rank": round(sum(a["rank"]) / len(a["rank"]), 1) if a["rank"] else None,
            }
        return out
