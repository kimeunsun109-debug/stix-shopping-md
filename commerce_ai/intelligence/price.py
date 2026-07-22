# -*- coding: utf-8 -*-
"""Price Intelligence — competitor price + margin + volume tradeoff."""
from __future__ import annotations

from commerce_ai.models import CommerceInput, CommerceMetrics, PriceRecommendation
from seo_engine.models import CollectionBundle


class PriceIntelligence:
    def recommend(
        self,
        bundle: CollectionBundle,
        metrics: CommerceMetrics,
        inp: CommerceInput | None = None,
    ) -> PriceRecommendation:
        inp = inp or CommerceInput()
        mine = bundle.mine.price
        prices = [c.price for c in bundle.competitors if c.price]
        avg = (sum(prices) / len(prices)) if prices else None
        pmin = min(prices) if prices else None
        pmax = max(prices) if prices else None
        cost = metrics.cost or inp.cost

        reasons: list[str] = []
        rec = mine
        margin_delta = 0.0
        rank_delta = 0
        vol_lift = 0.0
        cvr_lift = 0.0

        if mine is None:
            return PriceRecommendation(
                current_price=None,
                recommended_price=int(avg) if avg else None,
                competitor_avg=avg,
                competitor_min=pmin,
                competitor_max=pmax,
                margin_delta_pct=None,
                expected_rank_delta=None,
                expected_volume_lift_pct=None,
                expected_cvr_lift_pct=None,
                reasons=["내 상품 가격 없음 — 경쟁 평균 참고"],
            )

        if avg and mine > avg * 1.08:
            # slightly above market — nudge down toward avg
            target = int(round(avg / 100) * 100 - 100)  # psychological .900
            if target % 1000 == 0:
                target -= 100
            if target < mine:
                rec = max(target, int(mine * 0.92))
                drop = (mine - rec) / mine
                vol_lift = min(0.35, drop * 2.5)
                cvr_lift = min(0.15, drop * 1.2)
                rank_delta = max(1, int(drop * 40))
                reasons.append(
                    f"경쟁 평균 {avg:,.0f}원 대비 {mine - avg:,.0f}원 고가 — "
                    f"{rec:,}원으로 가격 경쟁력 확보"
                )
        elif avg and mine < avg * 0.9:
            # too cheap — optional raise if margin thin
            if cost and mine - cost < mine * 0.15:
                rec = min(int(avg * 0.95), int(mine * 1.05))
                vol_lift = -0.05
                cvr_lift = -0.02
                rank_delta = -1
                reasons.append("마진 방어를 위해 소폭 인상 검토 (저가 피로)")
            else:
                reasons.append("가격 경쟁력 양호 — 현상 유지 권장")
                rec = mine
        else:
            # near market: psychological pricing
            if mine % 1000 < 900:
                rec = (mine // 1000) * 1000 + 900
                if rec >= mine:
                    rec = mine - 100 if mine > 1000 else mine
                if rec != mine and rec > 0:
                    drop = (mine - rec) / mine
                    vol_lift = min(0.12, drop * 3)
                    cvr_lift = min(0.06, drop * 1.5)
                    rank_delta = 1 if drop > 0 else 0
                    reasons.append(f"심리적 가격 {rec:,}원 (끝자리 900 전략)")
                else:
                    reasons.append("경쟁가 밴드 내 — 현상 유지 + 상품명/이미지로 승부")
                    rec = mine
            else:
                reasons.append("경쟁가 밴드 내 — 현상 유지 + 상품명/이미지로 승부")

        if cost and rec and mine:
            m0 = (mine - cost) / mine * 100
            m1 = (rec - cost) / rec * 100
            margin_delta = m1 - m0
            if margin_delta < -5:
                reasons.append(f"마진 {margin_delta:.1f}%p 감소 — 판매량 증가로 상쇄 필요")

        if not reasons:
            reasons.append("가격 데이터 기반 조정 여지 적음")

        return PriceRecommendation(
            current_price=mine,
            recommended_price=rec,
            competitor_avg=round(avg, 0) if avg else None,
            competitor_min=pmin,
            competitor_max=pmax,
            margin_delta_pct=round(margin_delta, 1),
            expected_rank_delta=rank_delta,
            expected_volume_lift_pct=round(vol_lift * 100, 1),
            expected_cvr_lift_pct=round(cvr_lift * 100, 1),
            reasons=reasons,
        )
