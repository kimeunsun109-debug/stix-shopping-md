# -*- coding: utf-8 -*-
"""Revenue Intelligence — forecast lift from SEO/CTR/CVR/price actions."""
from __future__ import annotations

from commerce_ai.models import CommerceInput, CommerceMetrics, RevenueForecast
from seo_engine.models import CollectionBundle, RecoveryResult


class RevenueIntelligence:
    def build_metrics(
        self, bundle: CollectionBundle, inp: CommerceInput | None, seo: RecoveryResult
    ) -> CommerceMetrics:
        inp = inp or CommerceInput()
        price = bundle.mine.price
        units = inp.units_sold
        revenue = inp.revenue
        if revenue is None and price and units:
            revenue = price * units
        if revenue is None and price:
            # heuristic: review_count as weak proxy for demand
            rc = bundle.mine.review_count or 50
            units = units or max(10, rc // 5)
            revenue = price * units
        cost = inp.cost
        profit = inp.profit
        margin = None
        if profit is None and revenue is not None and cost is not None and units:
            profit = revenue - cost * units
        if revenue and profit is not None and revenue > 0:
            margin = round(100 * profit / revenue, 1)
        elif price and cost is not None and price > 0:
            margin = round(100 * (price - cost) / price, 1)

        ctr = inp.ctr
        cvr = inp.cvr
        # estimate CTR/CVR from SEO scores if missing
        if ctr is None and seo.recommended_title:
            ctr = max(0.01, min(0.12, seo.recommended_title.ctr_score / 1000))
        if cvr is None and seo.recommended_title:
            cvr = max(0.005, min(0.08, seo.recommended_title.cvr_score / 2000))

        return CommerceMetrics(
            revenue=revenue,
            profit=profit,
            cost=cost,
            margin_pct=margin,
            units_sold=units,
            impressions=inp.impressions,
            ctr=ctr,
            cvr=cvr,
            roas=inp.roas,
            ad_spend=inp.ad_spend,
            rank=inp.rank or bundle.mine.rank,
            stock=inp.stock,
        )

    def score(self, m: CommerceMetrics, seo: RecoveryResult) -> int:
        s = 40
        s += min(25, (seo.seo_score or 0) * 0.2)
        if m.margin_pct is not None:
            s += min(15, max(0, m.margin_pct) * 0.3)
        if m.ctr is not None:
            s += min(10, m.ctr * 200)
        if m.cvr is not None:
            s += min(10, m.cvr * 250)
        return int(max(0, min(100, round(s))))

    def forecast(
        self,
        m: CommerceMetrics,
        seo: RecoveryResult,
        *,
        price_lift_vol: float = 0.0,
        apply_title: bool = True,
        apply_image: bool = True,
        apply_faq: bool = True,
    ) -> RevenueForecast:
        cur = m.revenue or 0
        assumptions: list[str] = []
        ctr_lift = 0.0
        cvr_lift = 0.0
        imp_lift = 0.0

        if apply_title and seo.recommended_title:
            # coverage gap close -> impression + CTR
            gap = max(0, 90 - seo.keyword_coverage) / 100
            ctr_lift += 0.06 + gap * 0.08
            imp_lift += 0.10 + gap * 0.15
            assumptions.append(
                f"상품명 최적화: CTR +{ctr_lift*100:.0f}%p 상대, 노출 +{imp_lift*100:.0f}%"
            )
        if apply_image:
            ctr_lift += 0.08
            assumptions.append("대표이미지 개선: CTR +8% 상대")
        if apply_faq:
            cvr_lift += 0.05
            assumptions.append("FAQ/신뢰요소: CVR +5% 상대")
        if price_lift_vol:
            cvr_lift += price_lift_vol * 0.3
            assumptions.append(f"가격 전략 반영: 판매량 관련 +{price_lift_vol*100:.0f}%")

        ctr0 = m.ctr or 0.03
        cvr0 = m.cvr or 0.02
        ctr1 = min(0.2, ctr0 * (1 + ctr_lift))
        cvr1 = min(0.15, cvr0 * (1 + cvr_lift))

        # revenue ≈ impressions * ctr * cvr * price  OR scale current revenue
        if cur > 0:
            factor = (1 + imp_lift) * (ctr1 / max(ctr0, 1e-6)) * (cvr1 / max(cvr0, 1e-6))
            if price_lift_vol:
                factor *= 1 + price_lift_vol
            # dampen extreme — MD-realistic band (~+10~45%)
            factor = min(1.45, max(1.0, factor))
            proj = int(round(cur * factor))
        else:
            proj = 0
            factor = 1.0

        lift = ((proj - cur) / cur * 100) if cur else 0.0
        profit0 = m.profit
        profit1 = None
        profit_lift = None
        if profit0 is not None and cur > 0:
            # assume margin slightly compressed if volume up via price cut
            margin_factor = 0.97 if price_lift_vol > 0.1 else 1.0
            profit1 = int(round(profit0 * (proj / cur) * margin_factor))
            profit_lift = (profit1 - profit0) / profit0 * 100 if profit0 else None

        imp0 = m.impressions
        imp1 = int(imp0 * (1 + imp_lift)) if imp0 else None
        roas1 = None
        if m.roas is not None:
            roas1 = round(m.roas * min(1.4, 1 + lift / 200), 2)

        return RevenueForecast(
            current_revenue=cur,
            projected_revenue=proj,
            lift_pct=round(lift, 1),
            current_profit=profit0,
            projected_profit=profit1,
            profit_lift_pct=round(profit_lift, 1) if profit_lift is not None else None,
            projected_ctr=round(ctr1, 4),
            projected_cvr=round(cvr1, 4),
            projected_impressions=imp1,
            projected_roas=roas1,
            assumptions=assumptions,
        )
