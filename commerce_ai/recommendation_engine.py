# -*- coding: utf-8 -*-
"""Recommendation Engine v6 — evidence + impact + failure risk."""
from __future__ import annotations

import hashlib

from commerce_ai.confidence import ConfidenceEngine
from commerce_ai.memory import current_season, price_band
from commerce_ai.models import (
    ABTestPair,
    AlertItem,
    AutoRec,
    CommerceMetrics,
    KnowledgeContext,
    PriceRecommendation,
    RecommendationCard,
    RevenueForecast,
)
from commerce_ai.stability.logging_setup import get_logger
from seo_engine.models import CollectionBundle, RecoveryResult

_log = get_logger("commerce_ai.recommendation")


class RecommendationEngine:
    def __init__(self, confidence: ConfidenceEngine | None = None) -> None:
        self.confidence = confidence or ConfidenceEngine()

    def build(
        self,
        bundle: CollectionBundle,
        seo: RecoveryResult,
        metrics: CommerceMetrics,
        price: PriceRecommendation,
        forecast: RevenueForecast,
        alerts: list[AlertItem],
    ) -> list[RecommendationCard]:
        has_m = metrics.ctr is not None and metrics.cvr is not None
        cards: list[RecommendationCard] = []
        pid = bundle.mine.product_id or "unknown"
        ctx = KnowledgeContext(
            marketplace=bundle.marketplace,
            season=current_season(),
            price_band=price_band(bundle.mine.price or price.current_price),
            image_traits=list(seo.image_insight.improvements[:3])
            if seo.image_insight
            else [],
            review_traits=list(
                (seo.review_insight.advantages[:2] if seo.review_insight else [])
                + (seo.review_insight.complaints[:2] if seo.review_insight else [])
            ),
        )
        score_kw = dict(
            seo=seo,
            has_metrics=has_m,
            context=ctx,
            price=bundle.mine.price or price.current_price,
            marketplace=bundle.marketplace,
        )

        if seo.recommended_title:
            ctr_lift = max(5.0, (seo.recommended_title.ctr_score - 50) / 5)
            rev_lift = min(12.0, forecast.lift_pct * 0.25 + ctr_lift * 0.35)
            conf, unc, evidence, fail = self.confidence.score(
                "title", competitor_support=bool(seo.missing_keywords), **score_kw
            )
            # blend expected CTR with recent Memory wins
            if "평균 CTR" in evidence:
                try:
                    # parse "+8%" style from evidence if present
                    import re

                    m = re.search(r"CTR\s*([+-]?\d+)", evidence)
                    if m:
                        mem_ctr = float(m.group(1))
                        ctr_lift = round(0.55 * ctr_lift + 0.45 * abs(mem_ctr), 1)
                        rev_lift = min(12.0, rev_lift * 0.7 + ctr_lift * 0.35)
                except Exception:
                    pass
            opt_b = (
                seo.title_options[1].title
                if len(seo.title_options) > 1
                else seo.recommended_title.title
            )
            opt_a = seo.recommended_title.title
            if opt_a == opt_b and bundle.mine.title:
                opt_b = bundle.mine.title
            cards.append(
                self._card(
                    pid,
                    "title",
                    "상품명 변경",
                    reason="; ".join(seo.recommendation_reasons[:2])
                    or "핵심어 전반부 배치로 검색 일치율↑",
                    expected_effect=f"CTR +{ctr_lift:.0f}% / 매출 +{rev_lift:.0f}%",
                    metric="CTR",
                    lift_pct=ctr_lift,
                    revenue_lift_pct=rev_lift,
                    priority=1,
                    risk="low",
                    effort=5,
                    confidence=conf,
                    uncertainty=unc,
                    evidence=evidence,
                    failure_risk=fail,
                    expected_impact={"CTR": ctr_lift, "revenue": rev_lift},
                    payload={
                        "from": bundle.mine.title,
                        "to": opt_a,
                        "ab": {"A": opt_a, "B": opt_b},
                    },
                    must=True,
                    ab_test=ABTestPair(
                        metric="CTR",
                        variant_a=opt_a,
                        variant_b=opt_b,
                        label_a="상품명 A",
                        label_b="상품명 B",
                    ),
                )
            )

        if seo.image_insight.improvements:
            conf, unc, evidence, fail = self.confidence.score(
                "image", competitor_support=True, **score_kw
            )
            tip_a = seo.image_insight.improvements[0]
            tip_b = (
                seo.image_insight.improvements[1]
                if len(seo.image_insight.improvements) > 1
                else "현행 이미지 유지 (대조군)"
            )
            cards.append(
                self._card(
                    pid,
                    "image",
                    "대표이미지 교체",
                    reason=tip_a,
                    expected_effect="CTR +15% / 매출 +6%",
                    metric="CTR",
                    lift_pct=15.0,
                    revenue_lift_pct=6.0,
                    priority=2,
                    risk="low",
                    effort=40,
                    confidence=conf,
                    uncertainty=unc,
                    evidence=evidence,
                    failure_risk=fail,
                    expected_impact={"CTR": 15.0, "revenue": 6.0},
                    payload={"tips": seo.image_insight.improvements[:3], "ab": {"A": tip_a, "B": tip_b}},
                    must=True,
                    ab_test=ABTestPair(
                        metric="CTR",
                        variant_a=tip_a,
                        variant_b=tip_b,
                        label_a="이미지 A",
                        label_b="이미지 B",
                    ),
                )
            )

        if (
            price.recommended_price
            and price.current_price
            and price.recommended_price != price.current_price
        ):
            conf, unc, evidence, fail = self.confidence.score(
                "price",
                competitor_support=price.competitor_avg is not None,
                uncertainty_hint="마진 변동 리스크 있음",
                **score_kw,
            )
            risk = "high" if (price.margin_delta_pct or 0) < -5 else "medium"
            cvr_l = float(price.expected_cvr_lift_pct or 6)
            cards.append(
                self._card(
                    pid,
                    "price",
                    "가격 변경",
                    reason="; ".join(price.reasons[:2]),
                    expected_effect=(
                        f"CVR +{cvr_l:.0f}% / "
                        f"판매량 +{price.expected_volume_lift_pct or 0:.0f}% / "
                        f"마진 {price.margin_delta_pct or 0:+.1f}%p"
                    ),
                    metric="CVR",
                    lift_pct=cvr_l,
                    revenue_lift_pct=max(3.0, (price.expected_volume_lift_pct or 0) * 0.5),
                    priority=3,
                    risk=risk,
                    effort=8,
                    confidence=conf,
                    uncertainty=unc,
                    evidence=evidence,
                    failure_risk=fail,
                    expected_impact={"CVR": cvr_l, "revenue": max(3.0, (price.expected_volume_lift_pct or 0) * 0.5)},
                    payload={
                        "from": price.current_price,
                        "to": price.recommended_price,
                        "ab": {
                            "A": str(price.recommended_price),
                            "B": str(price.current_price),
                        },
                    },
                    must=risk != "high",
                    ab_test=ABTestPair(
                        metric="CVR",
                        variant_a=str(price.recommended_price),
                        variant_b=str(price.current_price),
                        label_a="추천가 A",
                        label_b="현행가 B",
                    ),
                )
            )

        conf, unc, evidence, fail = self.confidence.score("faq", **score_kw)
        faq_a = "구매 FAQ 5문 (난이도/구성/교환/배송/보관)"
        faq_b = "상세 상단 셀링포인트 보강 (FAQ 최소)"
        cards.append(
            self._card(
                pid,
                "faq",
                "FAQ 추가",
                reason="구매 망설임(난이도/구성/교환) 선대응",
                expected_effect="체류시간 +18% / CVR +5%",
                metric="dwell",
                lift_pct=18.0,
                revenue_lift_pct=4.0,
                priority=4,
                risk="low",
                effort=25,
                confidence=conf,
                uncertainty=unc,
                evidence=evidence,
                failure_risk=fail,
                expected_impact={"dwell": 18.0, "CVR": 5.0},
                payload={"structure": seo.detail_structure, "ab": {"A": faq_a, "B": faq_b}},
                must=False,
                ab_test=ABTestPair(
                    metric="CVR",
                    variant_a=faq_a,
                    variant_b=faq_b,
                    label_a="FAQ A",
                    label_b="상세카피 B",
                ),
            )
        )

        if seo.missing_keywords:
            conf, unc, evidence, fail = self.confidence.score(
                "keyword", competitor_support=True, **score_kw
            )
            cards.append(
                self._card(
                    pid,
                    "keyword",
                    "Golden Keyword 반영",
                    reason=f"유실 키워드: {', '.join(seo.missing_keywords[:4])}",
                    expected_effect=f"커버리지 {seo.keyword_coverage}%->90%+",
                    metric="rank",
                    lift_pct=float(min(12, len(seo.missing_keywords) * 2)),
                    revenue_lift_pct=5.0,
                    priority=2,
                    risk="low",
                    effort=12,
                    confidence=conf,
                    uncertainty=unc,
                    evidence=evidence,
                    failure_risk=fail,
                    expected_impact={"rank": float(min(12, len(seo.missing_keywords) * 2)), "revenue": 5.0},
                    payload={"keywords": seo.missing_keywords[:8]},
                    must=True,
                )
            )

        for a in alerts:
            if a.code == "RANK_DROP":
                conf, unc, evidence, fail = self.confidence.score("seo", **score_kw)
                cards.insert(
                    0,
                    self._card(
                        pid,
                        "seo",
                        "순위 급락 복구",
                        reason=a.message,
                        expected_effect="노출 회복 / 매출 방어",
                        metric="rank",
                        lift_pct=10.0,
                        revenue_lift_pct=8.0,
                        priority=1,
                        risk="medium",
                        effort=35,
                        confidence=conf,
                        uncertainty=unc,
                        evidence=evidence,
                        failure_risk=fail,
                        expected_impact={"rank": 10.0, "revenue": 8.0},
                        payload={"alert": a.code},
                        must=True,
                    ),
                )
            if a.code == "STOCK_LOW":
                conf, unc, evidence, fail = self.confidence.score(
                    "stock", has_metrics=True, context=ctx, marketplace=bundle.marketplace
                )
                cards.append(
                    self._card(
                        pid,
                        "stock",
                        "재고 확인",
                        reason=a.message,
                        expected_effect="품절 방지",
                        metric="revenue",
                        lift_pct=0.0,
                        revenue_lift_pct=0.0,
                        priority=1,
                        risk="high",
                        effort=10,
                        confidence=conf,
                        uncertainty=unc,
                        evidence=evidence,
                        failure_risk=fail,
                        expected_impact={},
                        payload={"stock": metrics.stock},
                        must=True,
                    )
                )

        cards.sort(
            key=lambda c: (
                0 if c.must_do_today else 1,
                c.priority,
                -(c.confidence * max(c.lift_pct, 1)),
            )
        )
        for i, c in enumerate(cards[:12], 1):
            c.priority = i
        out = cards[:12]
        _log.info(
            "recommendation.build product=%s cards=%s must=%s",
            pid,
            len(out),
            sum(1 for c in out if c.must_do_today),
        )
        return out

    def to_auto_recs(self, cards: list[RecommendationCard]) -> list[AutoRec]:
        return [
            AutoRec(
                action=c.action,
                expected_effect=c.expected_effect,
                metric=c.metric,
                lift_pct=c.lift_pct,
                priority=c.priority,
            )
            for c in cards
        ]

    def _card(
        self,
        product_id: str,
        category: str,
        action: str,
        *,
        reason: str,
        expected_effect: str,
        metric: str,
        lift_pct: float,
        revenue_lift_pct: float,
        priority: int,
        risk: str,
        effort: int,
        confidence: float,
        uncertainty: str,
        evidence: str,
        failure_risk: str,
        expected_impact: dict,
        payload: dict,
        must: bool,
        ab_test: ABTestPair | None = None,
    ) -> RecommendationCard:
        rid = hashlib.sha1(
            f"{product_id}:{category}:{action}:{payload}".encode("utf-8")
        ).hexdigest()[:12]
        return RecommendationCard(
            id=rid,
            action=action,
            category=category,
            reason=reason,
            expected_effect=expected_effect,
            metric=metric,
            lift_pct=lift_pct,
            revenue_lift_pct=revenue_lift_pct,
            priority=priority,
            risk=risk,
            effort_minutes=effort,
            confidence=confidence,
            uncertainty=uncertainty,
            evidence=evidence,
            failure_risk=failure_risk,
            expected_impact=expected_impact,
            payload=payload,
            must_do_today=must,
            ab_test=ab_test,
        )
