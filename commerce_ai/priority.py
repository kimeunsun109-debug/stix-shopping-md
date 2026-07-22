# -*- coding: utf-8 -*-
"""Priority Engine — rank today's MD work by expected ROI."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from commerce_ai.opportunity import Opportunity


@dataclass
class PriorityTask:
    rank: int
    lane: str  # urgent|high|normal|done|verify
    action: str
    product_id: str
    product_title: str
    reason: str
    expected_effect: str
    expected_revenue_lift: float
    expected_ctr_lift: float
    expected_cvr_lift: float
    confidence: float
    risk: str
    effort_minutes: int
    difficulty: str
    roi_score: float
    evidence: str
    code: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_RISK_PENALTY = {"low": 0.0, "medium": 0.08, "high": 0.22}
_ACTION_EFFORT = {
    "상품명 변경": 5,
    "상품명 수정": 5,
    "가격 변경": 8,
    "대표이미지 교체": 40,
    "상세페이지 수정": 35,
    "FAQ 추가": 25,
    "광고 ON/증액 검토": 10,
    "광고 OFF/축소 검토": 8,
    "재고 확인": 10,
    "리뷰 답변 / 불만 선대응": 15,
}


class PriorityEngine:
    """
    Priority score blends:
      expected revenue lift, CTR/CVR lift, confidence, inverse effort, risk penalty
    """

    def _lane(self, o: Opportunity, roi: float, risk: str) -> str:
        if o.code == "STOCK_PROTECT" or ("stock" in o.tags and risk == "high"):
            return "urgent"
        if o.code == "COMP_STOCKOUT":
            return "urgent"
        # only extreme ROI → urgent; otherwise high/normal
        if roi >= 28 and o.confidence >= 90:
            return "urgent"
        if roi >= 14 or o.confidence >= 85:
            return "high"
        return "normal"

    def rank(
        self,
        opportunities: list[Opportunity],
        *,
        verify_due: list[dict] | None = None,
        limit: int = 40,
    ) -> list[PriorityTask]:
        tasks: list[PriorityTask] = []

        for o in opportunities:
            effort = _ACTION_EFFORT.get(o.action, 20)
            risk = "high" if "stock" in o.tags or "risk" in o.tags else "medium"
            if o.confidence >= 80 and o.revenue_lift_pct >= 6:
                risk = "low" if risk != "high" else risk
            ctr = o.lift_pct if o.metric.upper() == "CTR" else (
                o.lift_pct * 0.4 if o.metric.upper() != "CVR" else 0
            )
            cvr = o.lift_pct if o.metric.upper() == "CVR" else (
                o.lift_pct * 0.3 if o.metric.upper() == "CTR" else o.lift_pct * 0.5
            )
            difficulty = "easy" if effort <= 10 else ("medium" if effort <= 30 else "hard")
            conf = max(35.0, min(96.0, o.confidence))
            # downrank weak evidence
            if "표본" in (o.evidence or "") or "부족" in (o.evidence or ""):
                conf = min(conf, 72.0)
            roi = self._roi(
                revenue_lift=o.revenue_lift_pct,
                ctr_lift=ctr,
                cvr_lift=cvr,
                confidence=conf,
                effort=effort,
                risk=risk,
            )
            lane = self._lane(o, roi, risk)
            tasks.append(
                PriorityTask(
                    rank=0,
                    lane=lane,
                    action=o.action,
                    product_id=o.product_id,
                    product_title=o.product_title,
                    reason=o.reason,
                    expected_effect=o.expected_effect,
                    expected_revenue_lift=o.revenue_lift_pct,
                    expected_ctr_lift=round(ctr, 1),
                    expected_cvr_lift=round(cvr, 1),
                    confidence=conf,
                    risk=risk,
                    effort_minutes=effort,
                    difficulty=difficulty,
                    roi_score=roi,
                    evidence=o.evidence,
                    code=o.code,
                    tags=list(o.tags),
                )
            )

        for d in verify_due or []:
            tasks.append(
                PriorityTask(
                    rank=0,
                    lane="verify",
                    action=f"검증 D+{d.get('dueDays')}: {d.get('action')}",
                    product_id=str(d.get("product_id") or ""),
                    product_title="",
                    reason="Verification checkpoint due",
                    expected_effect="추천 성과 측정 → Memory 학습",
                    expected_revenue_lift=0,
                    expected_ctr_lift=0,
                    expected_cvr_lift=0,
                    confidence=90,
                    risk="low",
                    effort_minutes=5,
                    difficulty="easy",
                    roi_score=50,
                    evidence=str(d.get("recommendation_id") or ""),
                    code="VERIFY",
                    tags=["verify"],
                )
            )

        lane_order = {"urgent": 0, "high": 1, "verify": 2, "normal": 3, "done": 4}
        tasks.sort(key=lambda t: (lane_order.get(t.lane, 9), -t.roi_score))
        # cap urgent to top 5 for actionable MD focus
        urgent_n = 0
        for t in tasks:
            if t.lane == "urgent":
                urgent_n += 1
                if urgent_n > 5:
                    t.lane = "high"
        tasks.sort(key=lambda t: (lane_order.get(t.lane, 9), -t.roi_score))
        for i, t in enumerate(tasks[:limit], 1):
            t.rank = i
        return tasks[:limit]

    def _roi(
        self,
        *,
        revenue_lift: float,
        ctr_lift: float,
        cvr_lift: float,
        confidence: float,
        effort: int,
        risk: str,
    ) -> float:
        impact = revenue_lift * 2.0 + ctr_lift * 1.2 + cvr_lift * 1.4
        conf_w = confidence / 100.0
        effort_w = max(0.35, 1.0 - (effort / 120.0))
        penalty = _RISK_PENALTY.get(risk, 0.1)
        return round(max(0.0, impact * conf_w * effort_w * (1.0 - penalty)), 2)
