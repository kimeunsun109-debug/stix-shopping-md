# -*- coding: utf-8 -*-
"""Commerce Report Generator — sections 1-21."""
from __future__ import annotations

from commerce_ai.models import CommerceResult
from seo_engine.models import CollectionBundle


def format_commerce_report(bundle: CollectionBundle, result: CommerceResult) -> str:
    seo = result.seo
    m = result.metrics
    f = result.revenue_forecast
    p = result.price_rec
    lines: list[str] = []

    lines.append("=" * 72)
    lines.append("STIX Commerce AI v6.0 - Production Ready OS Report")
    lines.append(
        f"검색어: {bundle.keyword} | 수집: {bundle.source} | "
        f"마켓: {bundle.marketplace} | {bundle.collected_at}"
    )
    if bundle.fallback_note:
        lines.append(f"수집메모: {bundle.fallback_note}")
    lines.append(f"내 상품: {bundle.mine.title}")
    lines.append(
        f"Commerce Score: {result.commerce_score}/100 | "
        f"Revenue Score: {result.revenue_score}/100 | "
        f"SEO: {seo.seo_score}/100"
    )
    if result.recommendation_success_rate is not None:
        lines.append(
            f"추천 성공률: {result.recommendation_success_rate*100:.0f}% / "
            f"실패율: {(result.recommendation_fail_rate or 0)*100:.0f}%"
        )
    if result.system_health_ok is not None:
        lines.append(
            f"System Health: {'OK' if result.system_health_ok else 'DEGRADED'}"
        )
    if result.verification_metrics:
        vm = result.verification_metrics
        lines.append(
            f"Verification: CTRΔ {vm.avg_ctr_delta_pct or '-'} | "
            f"CVRΔ {vm.avg_cvr_delta_pct or '-'} | "
            f"ROASΔ {vm.avg_roas_delta_pct or '-'}"
        )
    lines.append("=" * 72)

    lines.append("")
    lines.append(f"[1] SEO 점수: {seo.seo_score}/100 (커버리지 {seo.keyword_coverage}%)")

    lines.append("")
    lines.append(f"[2] Revenue Score: {result.revenue_score}/100")
    if m.revenue is not None:
        lines.append(f"    현재 매출: {m.revenue:,}원")
    if m.profit is not None:
        lines.append(f"    순이익: {m.profit:,}원 (마진 {m.margin_pct}%)")
    if m.roas is not None:
        lines.append(f"    ROAS: {m.roas}")

    lines.append("")
    lines.append(
        f"[3] CTR: {m.ctr:.2%}" if m.ctr is not None else "[3] CTR: (데이터 없음)"
    )
    if f.projected_ctr is not None:
        lines.append(f"    예상 CTR: {f.projected_ctr:.2%}")

    lines.append("")
    lines.append(
        f"[4] CVR: {m.cvr:.2%}" if m.cvr is not None else "[4] CVR: (데이터 없음)"
    )
    if f.projected_cvr is not None:
        lines.append(f"    예상 CVR: {f.projected_cvr:.2%}")

    lines.append("")
    lines.append("[5] Golden Keyword")
    for g in seo.golden_keywords[:15]:
        lines.append(
            f"   {g.stars} [{g.tier}] {g.keyword}  "
            f"검색량:{g.search_volume} 경쟁:{g.competition}"
        )

    lines.append("")
    lines.append("[6] 경쟁상품 분석")
    for s in seo.competitor_summaries[:5]:
        lines.append(f"   {s}")
    for c in result.competitor_changes[:8]:
        lines.append(f"   [CHANGE] {c}")
    for a in seo.trend_alerts[:5]:
        lines.append(f"   [TREND] {a}")

    lines.append("")
    lines.append("[7] SEO Gap")
    for g in seo.gaps[:12]:
        if not g.in_mine:
            lines.append(f"   - 유실 {g.keyword} {g.importance}")
    for k in seo.delete_candidates[:5]:
        lines.append(f"   - 삭제후보 {k}")
    for n in seo.learning_notes:
        if n.startswith("[GAP]"):
            lines.append(f"   {n[5:].strip()}")

    lines.append("")
    lines.append("[8] 상품명 추천")
    for i, t in enumerate(seo.title_options[:8], 1):
        lines.append(f"   {i}. {t.title}")

    lines.append("")
    lines.append("[9] 상품명 A/B Test")
    for s in seo.ab_test_summary:
        lines.append(f"   {s}")
    for r in seo.recommendation_reasons[:5]:
        lines.append(f"   이유: {r}")

    lines.append("")
    lines.append("[10] 가격 추천")
    if p.current_price is not None:
        lines.append(f"   현재: {p.current_price:,}원")
    if p.recommended_price is not None:
        lines.append(f"   추천: {p.recommended_price:,}원")
    if p.competitor_avg is not None:
        lines.append(
            f"   경쟁 평균/min/max: {p.competitor_avg:,.0f} / "
            f"{p.competitor_min or '-'} / {p.competitor_max or '-'}"
        )
    if p.expected_rank_delta is not None:
        lines.append(f"   예상 순위: {p.expected_rank_delta:+d}")
    if p.margin_delta_pct is not None:
        lines.append(f"   예상 마진: {p.margin_delta_pct:+.1f}%p")
    if p.expected_volume_lift_pct is not None:
        lines.append(f"   예상 판매량: {p.expected_volume_lift_pct:+.1f}%")
    for r in p.reasons:
        lines.append(f"   - {r}")

    lines.append("")
    lines.append("[11] 상세페이지 상단 카피")
    for row in seo.headline_copy.splitlines():
        lines.append(f"   {row}")

    lines.append("")
    lines.append("[12] 셀링포인트 TOP10")
    for i, s in enumerate(seo.selling_points, 1):
        lines.append(f"   {i}. {s}")

    lines.append("")
    lines.append("[13] 상세페이지 구조")
    for i, s in enumerate(seo.detail_structure, 1):
        lines.append(f"   {i}) {s}")

    lines.append("")
    lines.append("[14] 리뷰 인사이트")
    ri = seo.review_insight
    lines.append(f"   장점: {', '.join(ri.advantages[:6]) or '-'}")
    lines.append(f"   불만: {', '.join(ri.complaints[:4]) or '-'}")
    lines.append(f"   반품: {', '.join(ri.return_reasons[:4]) or '-'}")
    lines.append(f"   구매이유: {', '.join(ri.purchase_reasons[:4]) or '-'}")
    lines.append(f"   재구매: {', '.join(ri.repurchase_reasons[:3]) or '-'}")
    lines.append(f"   선물/장소: {', '.join(ri.gift_mentions[:2] + ri.usage_places[:2]) or '-'}")

    lines.append("")
    lines.append("[15] 대표이미지 개선안")
    for t in result.thumbnail_tips:
        lines.append(f"   - {t}")
    for s in seo.image_insight.improvements:
        if s not in result.thumbnail_tips:
            lines.append(f"   - {s}")

    lines.append("")
    lines.append("[16] CTR 개선안")
    for s in seo.ctr_tips:
        lines.append(f"   - {s}")
    for s in seo.dwell_tips:
        lines.append(f"   - [체류] {s}")

    lines.append("")
    lines.append("[17] CVR 개선안")
    for s in seo.conversion_tips:
        lines.append(f"   - {s}")

    lines.append("")
    lines.append("[18] 예상 매출 증가")
    lines.append(
        f"   현재 {f.current_revenue:,}원 -> 예상 {f.projected_revenue:,}원 "
        f"({f.lift_pct:+.1f}%)"
    )
    if f.current_profit is not None and f.projected_profit is not None:
        lines.append(
            f"   순이익 {f.current_profit:,} -> {f.projected_profit:,} "
            f"({f.profit_lift_pct:+.1f}%)"
        )
    for a in f.assumptions:
        lines.append(f"   - {a}")
    lines.append("   [Recommendation — Evidence / A/B]")
    for r in result.recommendations:
        must = "MUST" if r.must_do_today else "optional"
        lines.append(
            f"   - [{must}] {r.action} | Confidence {r.confidence:.0f}% | "
            f"위험 {r.risk} | ~{r.effort_minutes}분 | {r.expected_effect}"
        )
        lines.append(f"     이유: {r.reason[:90]}")
        if r.evidence:
            lines.append(f"     Evidence: {r.evidence[:100]}")
        if r.failure_risk:
            lines.append(f"     실패가능성: {r.failure_risk[:90]}")
        if r.expected_impact:
            impact = ", ".join(f"{k} +{v:.0f}%" for k, v in r.expected_impact.items())
            lines.append(f"     Expected Impact: {impact}")
        if r.ab_test:
            ab = r.ab_test
            lines.append(
                f"     A/B ({ab.metric}): A={ab.variant_a[:50]} | B={ab.variant_b[:50]}"
            )
    lines.append("   [Auto Recommendation]")
    for r in result.auto_recs:
        lines.append(f"   - {r.action}: {r.expected_effect}")

    lines.append("")
    lines.append("[19] Commerce Memory 저장")
    lines.append(f"   {result.memory_path or '(미저장)'}")
    for n in result.memory_notes[:8]:
        lines.append(f"   [Memory] {n}")

    lines.append("")
    lines.append("[20] Learning / Verification")
    lines.append(f"   Learning: {result.learning_path or '(미저장)'}")
    for n in result.learning_notes[:8]:
        lines.append(f"   - {n}")
    if result.verification_due:
        lines.append("   [Verification Due]")
        for d in result.verification_due[:8]:
            lines.append(
                f"   - D+{d.get('dueDays')} {d.get('action')} "
                f"({d.get('recommendation_id')})"
            )

    lines.append("")
    lines.append("[21] AI MD 오늘의 실행 계획")
    if result.alerts:
        lines.append("   [Alert Center]")
        for a in result.alerts[:8]:
            lines.append(f"   {a.emoji} {a.message} -> {a.action}")
    lines.append("   [오늘 반드시]")
    for t in result.planner_tasks:
        if not t.must_do_today:
            continue
        lines.append(
            f"   {t.priority}) [{t.category}] {t.title} "
            f"(신뢰도 {t.confidence:.0f}% / 위험 {t.risk} / "
            f"~{t.effort_minutes}분 / {t.difficulty})"
        )
        lines.append(f"      효과: {t.expected_effect}")
    lines.append("   [오늘 아니어도 됨]")
    optional = [t for t in result.planner_tasks if not t.must_do_today]
    if not optional:
        lines.append("   - (없음)")
    for t in optional:
        lines.append(
            f"   {t.priority}) {t.title} (신뢰도 {t.confidence:.0f}% / ~{t.effort_minutes}분)"
        )
    if result.execution_plan:
        lines.append(
            f"   [Execution Plan] {result.execution_plan.plan_id} "
            f"— 승인 대기 {len(result.execution_plan.steps)} steps"
        )
        lines.append(f"   {result.execution_plan.notes}")
        for s in result.execution_plan.steps[:6]:
            lines.append(
                f"   - step {s.step_id} [{s.status}] {s.action} -> {s.adapter}"
            )
            lines.append(f"     preview: {s.dry_run_preview[:100]}")

    lines.append("")
    return "\n".join(lines)
