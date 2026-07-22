# -*- coding: utf-8 -*-
"""Auto Recommendation — scored action cards."""
from __future__ import annotations

from commerce_ai.models import AutoRec, PriceRecommendation, RevenueForecast
from seo_engine.models import RecoveryResult


class AutoRecommendation:
    def build(
        self,
        seo: RecoveryResult,
        price: PriceRecommendation,
        forecast: RevenueForecast,
    ) -> list[AutoRec]:
        recs: list[AutoRec] = []
        if seo.recommended_title:
            lift = max(5.0, (seo.recommended_title.ctr_score - 50) / 5)
            recs.append(
                AutoRec(
                    action="상품명 수정",
                    expected_effect=f"CTR +{lift:.0f}% / SEO {seo.recommended_title.seo_score:.0f}",
                    metric="CTR",
                    lift_pct=lift,
                    priority=1,
                )
            )
        if seo.image_insight.improvements:
            recs.append(
                AutoRec(
                    action="대표이미지 변경",
                    expected_effect="CTR +15%",
                    metric="CTR",
                    lift_pct=15,
                    priority=2,
                )
            )
        if (
            price.recommended_price
            and price.current_price
            and price.recommended_price != price.current_price
        ):
            recs.append(
                AutoRec(
                    action="가격 변경",
                    expected_effect=f"CVR +{price.expected_cvr_lift_pct or 6:.0f}%",
                    metric="CVR",
                    lift_pct=float(price.expected_cvr_lift_pct or 6),
                    priority=3,
                )
            )
        recs.append(
            AutoRec(
                action="FAQ 추가",
                expected_effect="체류시간 +18% / CVR +5%",
                metric="dwell",
                lift_pct=18,
                priority=4,
            )
        )
        if seo.missing_keywords:
            recs.append(
                AutoRec(
                    action=f"키워드 보강 ({', '.join(seo.missing_keywords[:3])})",
                    expected_effect=f"커버리지 {seo.keyword_coverage}%->90%+",
                    metric="rank",
                    lift_pct=max(5.0, (90 - seo.keyword_coverage) / 3),
                    priority=5,
                )
            )
        if forecast.lift_pct >= 10:
            recs.append(
                AutoRec(
                    action="추천 패키지 일괄 적용",
                    expected_effect=f"예상 매출 +{forecast.lift_pct}%",
                    metric="revenue",
                    lift_pct=forecast.lift_pct,
                    priority=1,
                )
            )
        recs.sort(key=lambda r: (r.priority, -r.lift_pct))
        return recs[:8]
