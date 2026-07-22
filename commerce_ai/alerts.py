# -*- coding: utf-8 -*-
"""Alert Center — rank/CTR/CVR/competitor/price/keyword alerts."""
from __future__ import annotations

from commerce_ai.models import AlertItem, CommerceInput, CommerceMetrics
from seo_engine.models import CollectionBundle, RecoveryResult


class AlertCenter:
    EMOJI = {
        "RANK_DROP": "🔴",
        "CTR_DOWN": "🟠",
        "CVR_DOWN": "🟡",
        "COMP_OOS": "🟢",
        "NEW_KW": "🔵",
        "PRICE_CHANGE": "🟣",
        "SEO_LOW": "🟠",
        "STOCK_LOW": "🔴",
    }

    def detect(
        self,
        bundle: CollectionBundle,
        metrics: CommerceMetrics,
        seo: RecoveryResult,
        inp: CommerceInput | None,
        competitor_changes: list[str],
    ) -> list[AlertItem]:
        inp = inp or CommerceInput()
        alerts: list[AlertItem] = []
        pid = bundle.mine.product_id or "unknown"

        rank_now = metrics.rank or inp.rank
        rank_y = inp.rank_yesterday
        if isinstance(rank_now, int) and isinstance(rank_y, int) and rank_now > rank_y + 2:
            alerts.append(
                AlertItem(
                    severity="critical" if rank_now - rank_y >= 5 else "high",
                    code="RANK_DROP",
                    emoji=self.EMOJI["RANK_DROP"],
                    message=f"순위 급락 {rank_y}위 -> {rank_now}위",
                    product_id=pid,
                    action="SEO Recovery + 상품명/이미지 즉시 점검",
                )
            )

        if inp.ctr is not None and inp.ctr_yesterday is not None and inp.ctr_yesterday > 0:
            drop = (inp.ctr_yesterday - inp.ctr) / inp.ctr_yesterday
            if drop >= 0.15:
                alerts.append(
                    AlertItem(
                        severity="high",
                        code="CTR_DOWN",
                        emoji=self.EMOJI["CTR_DOWN"],
                        message=f"CTR 감소 {inp.ctr_yesterday:.2%} -> {inp.ctr:.2%} ({drop*100:.0f}%)",
                        product_id=pid,
                        action="대표이미지·상품명 전반부 재설계",
                    )
                )

        if inp.cvr is not None and inp.cvr_yesterday is not None and inp.cvr_yesterday > 0:
            drop = (inp.cvr_yesterday - inp.cvr) / inp.cvr_yesterday
            if drop >= 0.15:
                alerts.append(
                    AlertItem(
                        severity="medium",
                        code="CVR_DOWN",
                        emoji=self.EMOJI["CVR_DOWN"],
                        message=f"CVR 감소 {inp.cvr_yesterday:.2%} -> {inp.cvr:.2%}",
                        product_id=pid,
                        action="FAQ·후기·가격·신뢰요소 점검",
                    )
                )

        for ch in competitor_changes:
            if "품절" in ch or "이탈" in ch:
                alerts.append(
                    AlertItem(
                        severity="info",
                        code="COMP_OOS",
                        emoji=self.EMOJI["COMP_OOS"],
                        message=ch,
                        product_id=pid,
                        action="광고/재고 확보로 점유 기회 노리기",
                    )
                )
            elif "신규 반복 키워드" in ch or "신규 키워드" in ch:
                alerts.append(
                    AlertItem(
                        severity="info",
                        code="NEW_KW",
                        emoji=self.EMOJI["NEW_KW"],
                        message=ch,
                        product_id=pid,
                        action="Golden Keyword 반영 + 상품명 테스트",
                    )
                )
            elif "가격 변동" in ch:
                alerts.append(
                    AlertItem(
                        severity="medium",
                        code="PRICE_CHANGE",
                        emoji=self.EMOJI["PRICE_CHANGE"],
                        message=ch,
                        product_id=pid,
                        action="Price Intelligence 재실행",
                    )
                )

        if seo.seo_score < 55:
            alerts.append(
                AlertItem(
                    severity="high",
                    code="SEO_LOW",
                    emoji=self.EMOJI["SEO_LOW"],
                    message=f"SEO 점수 낮음 ({seo.seo_score}/100)",
                    product_id=pid,
                    action="유실 키워드·상품명 복구",
                )
            )

        if metrics.stock is not None and metrics.stock <= 10:
            alerts.append(
                AlertItem(
                    severity="critical",
                    code="STOCK_LOW",
                    emoji=self.EMOJI["STOCK_LOW"],
                    message=f"재고 부족 ({metrics.stock})",
                    product_id=pid,
                    action="입고/옵션 재고 확인",
                )
            )

        # severity sort
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        alerts.sort(key=lambda a: order.get(a.severity, 9))
        return alerts
