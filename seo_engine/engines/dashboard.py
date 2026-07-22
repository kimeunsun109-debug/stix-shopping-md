# -*- coding: utf-8 -*-
"""Dashboard — portfolio risk / recovery priorities across products."""
from __future__ import annotations

import json
from pathlib import Path

from seo_engine.models import DashboardItem

HISTORY_DIR = Path(__file__).resolve().parent.parent.parent / "seo_history"
RANK_DIR = HISTORY_DIR / "ranks"


class Dashboard:
    def __init__(self, history_dir: Path | None = None) -> None:
        self.history_dir = history_dir or HISTORY_DIR
        self.rank_dir = self.history_dir / "ranks"

    def build(self) -> tuple[list[DashboardItem], list[str]]:
        items: list[DashboardItem] = []
        tasks: list[str] = []

        # from per-product history json
        if self.history_dir.exists():
            for path in sorted(self.history_dir.glob("*.json")):
                if path.name in {"learning_events.jsonl", "learning_success.jsonl"}:
                    continue
                if path.parent.name == "ranks" or "trends" in str(path):
                    continue
                try:
                    records = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if not isinstance(records, list) or not records:
                    continue
                last = records[-1]
                pid = str(last.get("productId") or path.stem)
                rank_now = last.get("rankAfter") or last.get("rankBefore")
                rank_prev = None
                if len(records) >= 2:
                    prev = records[-2]
                    rank_prev = prev.get("rankAfter") or prev.get("rankBefore")
                delta = None
                if isinstance(rank_now, int) and isinstance(rank_prev, int):
                    delta = rank_now - rank_prev  # positive = worse
                seo = last.get("seoScore")
                ctr = last.get("CTR")
                cvr = last.get("CVR")
                risk, hint = self._risk(seo, rank_now, delta, ctr, cvr)
                items.append(
                    DashboardItem(
                        product_id=pid,
                        title=str(last.get("title") or "")[:60],
                        seo_score=int(seo) if seo is not None else None,
                        rank=int(rank_now) if isinstance(rank_now, int) else None,
                        rank_delta=delta,
                        ctr=float(ctr) if ctr is not None else None,
                        cvr=float(cvr) if cvr is not None else None,
                        risk=risk,
                        recovery_hint=hint,
                        marketplace=str(last.get("marketplace") or "coupang"),
                    )
                )

        # enrich from rank monitor files if missing
        if self.rank_dir.exists():
            for path in self.rank_dir.glob("*.json"):
                try:
                    ranks = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if not ranks:
                    continue
                last = ranks[-1]
                pid = str(last.get("productId") or "")
                if any(i.product_id == pid for i in items):
                    # update delta from ranks
                    if len(ranks) >= 2:
                        a, b = ranks[-2].get("rank"), ranks[-1].get("rank")
                        if isinstance(a, int) and isinstance(b, int):
                            for i in items:
                                if i.product_id == pid and i.rank_delta is None:
                                    i.rank = b
                                    i.rank_delta = b - a
                                    i.risk, i.recovery_hint = self._risk(
                                        i.seo_score, i.rank, i.rank_delta, i.ctr, i.cvr
                                    )
                    continue
                a = ranks[-2].get("rank") if len(ranks) >= 2 else None
                b = ranks[-1].get("rank")
                delta = (b - a) if isinstance(a, int) and isinstance(b, int) else None
                risk, hint = self._risk(None, b if isinstance(b, int) else None, delta, None, None)
                items.append(
                    DashboardItem(
                        product_id=pid or path.stem,
                        title=str(last.get("title") or last.get("keyword") or "")[:60],
                        seo_score=None,
                        rank=int(b) if isinstance(b, int) else None,
                        rank_delta=delta,
                        ctr=None,
                        cvr=None,
                        risk=risk,
                        recovery_hint=hint,
                    )
                )

        # priority sort
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        items.sort(key=lambda x: (order.get(x.risk, 9), -(x.rank_delta or 0), x.product_id))

        # today's tasks
        for i in items:
            if i.risk in {"critical", "high"}:
                tasks.append(
                    f"[{i.risk.upper()}] {i.product_id} {i.title[:30]} — {i.recovery_hint}"
                )
        # trend alerts file scan
        trend_dir = self.history_dir / "trends"
        if trend_dir.exists():
            for path in sorted(trend_dir.glob("*.json"))[-5:]:
                try:
                    hist = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if hist and hist[-1].get("newKeywords"):
                    nk = hist[-1]["newKeywords"][:5]
                    tasks.append(
                        f"[GOLDEN] {hist[-1].get('searchKeyword')} 신규키워드: {', '.join(nk)}"
                    )

        if not tasks:
            tasks.append("긴급 작업 없음 — Ranking Monitor 일일 기록 유지")
        return items, tasks[:30]

    def _risk(
        self,
        seo: int | None,
        rank: int | None,
        delta: int | None,
        ctr: float | None,
        cvr: float | None,
    ) -> tuple[str, str]:
        if delta is not None and delta >= 5:
            return "critical", "순위 급락 — 즉시 Recovery 실행"
        if delta is not None and delta >= 3:
            return "high", "순위 하락 — Gap/Title 재분석"
        if seo is not None and seo < 50:
            return "high", "SEO 점수 낮음 — 상품명/키워드 복구"
        if seo is not None and seo < 65:
            return "medium", "SEO 개선 여지 — Golden Keyword 반영"
        if rank is not None and rank > 20:
            return "medium", "노출 하위권 — 핵심어 전반부 배치"
        return "low", "모니터링 유지"

    def format_text(self) -> str:
        items, tasks = self.build()
        lines = [
            "=" * 72,
            "STIX AI - SEO Dashboard v3.0",
            "=" * 72,
            "",
            "[오늘 해야 할 작업]",
        ]
        for t in tasks:
            lines.append(f"  - {t}")
        lines.append("")
        lines.append("[상품 현황]")
        lines.append(
            f"  {'위험':8} {'순위':>4} {'Δ':>4} {'SEO':>4}  상품"
        )
        for i in items[:40]:
            rd = f"{i.rank_delta:+d}" if i.rank_delta is not None else "-"
            rk = str(i.rank) if i.rank is not None else "-"
            sc = str(i.seo_score) if i.seo_score is not None else "-"
            lines.append(
                f"  {i.risk:8} {rk:>4} {rd:>4} {sc:>4}  {i.product_id} | {i.title}"
            )
            if i.recovery_hint:
                lines.append(f"           -> {i.recovery_hint}")
        lines.append("")
        return "\n".join(lines)
