# -*- coding: utf-8 -*-
"""Opportunity Engine — detect growth chances, not only problems."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Opportunity:
    code: str
    title: str
    action: str
    product_id: str
    product_title: str
    reason: str
    expected_effect: str
    metric: str
    lift_pct: float
    revenue_lift_pct: float
    confidence: float
    evidence: str
    season: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SEASON_KEYWORDS = {
    "spring": ("봄", "벚꽃", "졸업", "새학기"),
    "summer": ("여름", "휴가", "시원", "바닷가", "집콕"),
    "autumn": ("가을", "단풍", "할로윈"),
    "winter": ("겨울", "크리스마스", "연말", "선물", "집콕"),
}


def _current_season(month: int | None = None) -> str:
    m = month or datetime.now().month
    if m in (3, 4, 5):
        return "spring"
    if m in (6, 7, 8):
        return "summer"
    if m in (9, 10, 11):
        return "autumn"
    return "winter"


class OpportunityEngine:
    """
    Scan product snapshots for opportunities:
      - competitor stock gap / low SEO peers
      - new golden keywords
      - seasonal keyword lift
      - review/image upgrade signals
    """

    def detect(self, snapshots: list[dict[str, Any]]) -> list[Opportunity]:
        season = _current_season()
        season_kw = _SEASON_KEYWORDS.get(season, ())
        opps: list[Opportunity] = []

        for s in snapshots:
            pid = str(s.get("product_id") or "")
            title = s.get("title") or ""
            seo = int(s.get("seo_score") or 0)
            rev = int(s.get("revenue_score") or 0)
            recs = s.get("recommendations") or []
            golden = s.get("golden_keywords") or []
            tips = s.get("image_tips") or []
            stock = s.get("stock")
            price = s.get("price")

            # map existing must-do recs as opportunities (primary source)
            has_must = False
            for r in recs:
                if not r.get("must_do_today"):
                    continue
                has_must = True
                opps.append(
                    Opportunity(
                        code="REC_" + str(r.get("category") or "act").upper(),
                        title=r.get("action") or "추천 작업",
                        action=r.get("action") or "",
                        product_id=pid,
                        product_title=title,
                        reason=r.get("reason") or "",
                        expected_effect=r.get("expected_effect") or "",
                        metric=str(
                            next(iter(r.get("expected_impact") or {}), "CTR")
                        ),
                        lift_pct=float(r.get("lift_pct") or 0),
                        revenue_lift_pct=float(r.get("revenue_lift_pct") or 0),
                        confidence=float(r.get("confidence") or 60),
                        evidence=r.get("evidence") or "",
                        tags=["recommendation"],
                    )
                )

            # seasonal / growth only when not already covered by must-do flood
            if any(k in title for k in season_kw) and seo < 70 and not has_must:
                opps.append(
                    Opportunity(
                        code="SEASON_KEYWORD",
                        title="계절 키워드 기회",
                        action="상세페이지 수정",
                        product_id=pid,
                        product_title=title,
                        reason=f"{season} 시즌 키워드가 상품에 맞음 — 상세 상단 반영",
                        expected_effect="시즌 검색 유입↑ / CVR +2~4%",
                        metric="CVR",
                        lift_pct=3.0,
                        revenue_lift_pct=5.0,
                        confidence=72.0,
                        evidence=f"시즌={season}, SEO={seo}",
                        season=season,
                        tags=["season", "opportunity"],
                    )
                )

            missing = [g for g in golden[:4] if g and g not in title]
            if missing and not any(
                (r.get("action") or "").startswith("상품명") for r in recs if r.get("must_do_today")
            ):
                opps.append(
                    Opportunity(
                        code="NEW_KEYWORD",
                        title="신규/유실 Golden Keyword",
                        action="상품명 변경",
                        product_id=pid,
                        product_title=title,
                        reason=f"키워드 미반영: {', '.join(missing[:3])}",
                        expected_effect="CTR +5~10%",
                        metric="CTR",
                        lift_pct=7.0,
                        revenue_lift_pct=6.0,
                        confidence=80.0,
                        evidence=f"Golden {len(golden)}개 중 미반영 {len(missing)}",
                        tags=["keyword", "opportunity"],
                    )
                )

            if tips and seo < 65 and not any(
                "이미지" in (r.get("action") or "") for r in recs if r.get("must_do_today")
            ):
                opps.append(
                    Opportunity(
                        code="IMAGE_UPGRADE",
                        title="대표이미지 개선 기회",
                        action="대표이미지 교체",
                        product_id=pid,
                        product_title=title,
                        reason=tips[0],
                        expected_effect="CTR +10~15%",
                        metric="CTR",
                        lift_pct=12.0,
                        revenue_lift_pct=6.0,
                        confidence=74.0,
                        evidence="; ".join(tips[:2]),
                        tags=["image", "opportunity"],
                    )
                )

            if isinstance(stock, int) and stock <= 5 and rev >= 50:
                opps.append(
                    Opportunity(
                        code="STOCK_PROTECT",
                        title="재고 임박 — 광고 축소/재고 확인",
                        action="광고 OFF/축소 검토",
                        product_id=pid,
                        product_title=title,
                        reason=f"재고 {stock} · Revenue Score {rev}",
                        expected_effect="품절 손실 방어 / ROAS 보호",
                        metric="ROAS",
                        lift_pct=0.0,
                        revenue_lift_pct=3.0,
                        confidence=85.0,
                        evidence=f"stock={stock}",
                        tags=["stock", "risk", "opportunity"],
                    )
                )

            if rev >= 60 and seo < 55 and not has_must:
                opps.append(
                    Opportunity(
                        code="SEO_GROWTH",
                        title="매출 잠재력 대비 SEO 갭",
                        action="상품명 변경",
                        product_id=pid,
                        product_title=title,
                        reason=f"Revenue {rev} vs SEO {seo} — 검색 유입 확장 여지",
                        expected_effect="노출↑ / 매출 +8%",
                        metric="revenue",
                        lift_pct=8.0,
                        revenue_lift_pct=8.0,
                        confidence=78.0,
                        evidence=f"rev_score={rev}, seo={seo}",
                        tags=["seo", "growth"],
                    )
                )

            for note in s.get("competitor_notes") or []:
                if "품절" in note or "sold" in note.lower():
                    opps.append(
                        Opportunity(
                            code="COMP_STOCKOUT",
                            title="경쟁사 품절 기회",
                            action="광고 ON/증액 검토",
                            product_id=pid,
                            product_title=title,
                            reason=note[:80],
                            expected_effect="점유율 흡수 / 매출 +5~12%",
                            metric="revenue",
                            lift_pct=8.0,
                            revenue_lift_pct=10.0,
                            confidence=70.0,
                            evidence=note[:60],
                            tags=["competitor", "ads"],
                        )
                    )
                    break

        # dedupe by product+action
        seen: set[str] = set()
        unique: list[Opportunity] = []
        for o in opps:
            key = f"{o.product_id}|{o.action}|{o.code}"
            if key in seen:
                continue
            seen.add(key)
            unique.append(o)
        return unique
