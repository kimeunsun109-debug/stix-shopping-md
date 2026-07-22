# -*- coding: utf-8 -*-
"""Confidence Engine — evidence-backed reliability 0~100 (single Memory pass)."""
from __future__ import annotations

from commerce_ai.memory import CommerceMemory, current_season, price_band
from commerce_ai.models import KnowledgeContext
from commerce_ai.stability.logging_setup import get_logger
from seo_engine.models import RecoveryResult

_log = get_logger("commerce_ai.confidence")


class ConfidenceEngine:
    BASE = {
        "title": 78.0,
        "image": 72.0,
        "price": 70.0,
        "faq": 62.0,
        "detail": 68.0,
        "keyword": 74.0,
        "ad": 55.0,
        "stock": 85.0,
        "review": 60.0,
        "seo": 70.0,
    }

    def __init__(self, memory: CommerceMemory | None = None) -> None:
        self.memory = memory or CommerceMemory()

    def score(
        self,
        category: str,
        *,
        seo: RecoveryResult | None = None,
        has_metrics: bool = False,
        competitor_support: bool = False,
        uncertainty_hint: str = "",
        context: KnowledgeContext | None = None,
        price: int | float | None = None,
        marketplace: str = "",
    ) -> tuple[float, str, str, str]:
        """
        Returns (confidence, uncertainty, evidence, failure_risk).
        Loads Memory once per call (shared cache across cards in same batch).
        """
        conf = float(self.BASE.get(category, 65.0))
        notes: list[str] = []
        ctx = context or KnowledgeContext(
            marketplace=marketplace,
            season=current_season(),
            price_band=price_band(price),
        )

        rows = self.memory.entries()
        hist = self.memory.action_stats(category, rows=rows)
        similar = self.memory.find_similar_successes(
            action_category=category, context=ctx, limit=27, rows=rows
        )
        evidence, avg_ctr = self.memory.evidence_for(
            category, ctx, rows=rows, similar=similar, hist=hist
        )

        if len(similar) >= 10:
            conf = 0.30 * conf + 0.70 * (
                hist["success_rate"] * 100 if hist["n"] else conf
            )
            conf += min(10, len(similar) * 0.2)
            notes.append(f"최근 유사 성공 {len(similar)}건 우선 반영")
        elif hist["n"] >= 3:
            conf = 0.45 * conf + 0.55 * (hist["success_rate"] * 100)
            notes.append(
                f"과거 {hist['n']}건 성공률 {hist['success_rate']*100:.0f}%"
            )
        elif hist["n"] > 0:
            conf = 0.75 * conf + 0.25 * (hist["success_rate"] * 100)
            notes.append(f"표본 적음({hist['n']}건) — 불확실성↑")

        ab_wins = sum(1 for e in similar if e.get("abWinner"))
        if ab_wins >= 2:
            conf += 4
            notes.append(f"A/B 검증 승자 {ab_wins}건")

        if has_metrics:
            conf += 6
        else:
            conf -= 8
            notes.append("실측 CTR/CVR/매출 부족")

        if competitor_support:
            conf += 5
        if seo and seo.keyword_coverage >= 70:
            conf += 3
        if seo and seo.seo_score < 50 and category in {"title", "keyword", "seo"}:
            conf += 4
            notes.append("SEO 갭 명확")

        fail_rate = 1.0 - hist["success_rate"] if hist["n"] else 0.35
        if hist["n"] < 3:
            fail_rate = max(fail_rate, 0.40)
        failure_risk = (
            f"실패 가능성 약 {fail_rate*100:.0f}%"
            + (f" (과거 실패 {hist['fail']}건)" if hist["fail"] else "")
        )
        if category == "price":
            failure_risk += " — 마진/순위 역효과 가능"
        if category == "ad":
            failure_risk += " — ROAS 악화 가능"

        conf = max(35.0, min(96.0, round(conf, 1)))
        if conf < 70:
            notes.append(uncertainty_hint or "데이터/표본 부족으로 신뢰도 중간 이하")
        uncertainty = "; ".join(notes) if notes else ""
        _log.debug("confidence %s -> %s", category, conf)
        return conf, uncertainty, evidence, failure_risk
