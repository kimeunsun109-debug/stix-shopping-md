# -*- coding: utf-8 -*-
"""SEO History Engine + Recovery Report Generator v3 (①-⑳)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from seo_engine.models import CollectionBundle, RecoveryResult

HISTORY_DIR = Path(__file__).resolve().parent.parent / "seo_history"


def format_report(bundle: CollectionBundle, result: RecoveryResult) -> str:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("STIX AI - Coupang SEO Recovery Engine v3.0")
    lines.append(
        f"검색어: {bundle.keyword} | 수집: {bundle.source} | "
        f"마켓: {bundle.marketplace} | {bundle.collected_at}"
    )
    if bundle.fallback_note:
        lines.append(f"수집메모: {bundle.fallback_note}")
    lines.append(f"내 상품: {bundle.mine.title}")
    lines.append("=" * 72)

    sb = result.score_breakdown
    lines.append("")
    lines.append(f"[1] SEO 점수: {result.seo_score}/100")
    lines.append(
        f"    세부: 상품명{sb.title} 키워드{sb.keywords} 상세{sb.detail} "
        f"이미지{sb.image} 리뷰{sb.reviews} 속성{sb.attributes} "
        f"카테고리{sb.category} 옵션{sb.options} 브랜드{sb.brand}"
    )

    lines.append("")
    lines.append(f"[2] Keyword Coverage: {result.keyword_coverage}%")

    lines.append("")
    lines.append("[3] Golden Keywords")
    for g in result.golden_keywords[:20]:
        extra = ""
        if g.ctr_delta_pct:
            extra += f" CTR {g.ctr_delta_pct:+.0f}%"
        if g.cvr_delta_pct:
            extra += f" CVR {g.cvr_delta_pct:+.0f}%"
        if g.rank_delta:
            extra += f" 순위 {g.rank_delta:+d}"
        lines.append(
            f"   {g.stars} [{g.tier}] {g.keyword}  "
            f"검색량:{g.search_volume} 경쟁:{g.competition}{extra}"
        )
        if g.effect:
            lines.append(f"      -> {g.effect}")

    lines.append("")
    lines.append("[4] 유실 키워드")
    for g in result.gaps:
        if not g.in_mine:
            extra = f" | {g.note}" if g.note else ""
            lines.append(
                f"   - {g.keyword}  {g.importance}  (상위출현 {g.frequency}){extra}"
            )

    lines.append("")
    lines.append("[5] 추가 추천 키워드")
    for k in result.missing_keywords[:20]:
        lines.append(f"   - {k}")

    lines.append("")
    lines.append("[6] 삭제 추천 키워드")
    if result.delete_candidates:
        for k in result.delete_candidates:
            lines.append(f"   - {k}")
    else:
        lines.append("   - (해당 없음)")

    lines.append("")
    lines.append("[7] SEO Gap 분석")
    if result.duplicate_keywords:
        lines.append(f"   중복: {', '.join(result.duplicate_keywords)}")
    for n in result.learning_notes:
        if n.startswith("[GAP]"):
            lines.append(f"   {n[5:].strip()}")
    for g in result.gaps[:12]:
        status = "보유" if g.in_mine else "누락"
        lines.append(f"   - {g.keyword} | {g.importance} | {status}")

    lines.append("")
    lines.append("[8] 경쟁상품 분석")
    if result.competitor_summaries:
        for s in result.competitor_summaries:
            lines.append(f"   {s}")
    elif bundle.competitors:
        for c in bundle.competitors[:5]:
            lines.append(
                f"   #{c.rank or '-'} {c.title[:65]} | "
                f"{c.price or '-'}원 | ★{c.rating or '-'} | 리뷰 {c.review_count or '-'}"
            )
    else:
        lines.append("   (경쟁 데이터 없음)")
    for a in result.trend_alerts:
        lines.append(f"   [TREND] {a}")

    lines.append("")
    lines.append("[9] 최적 상품명 5~10개")
    for i, t in enumerate(result.title_options, 1):
        lines.append(f"   {i}. {t.title}")

    lines.append("")
    lines.append("[10] 상품명별 SEO/CTR/CVR 비교")
    for s in result.ab_test_summary:
        lines.append(f"   {s}")

    lines.append("")
    lines.append("[11] 추천 이유")
    for r in result.recommendation_reasons:
        lines.append(f"   - {r}")
    if result.recommended_title:
        for r in result.recommended_title.reasons:
            if r not in result.recommendation_reasons:
                lines.append(f"   - {r}")

    lines.append("")
    lines.append("[12] 상세페이지 상단 카피")
    for row in result.headline_copy.splitlines():
        lines.append(f"   {row}")

    lines.append("")
    lines.append("[13] 셀링포인트 TOP10")
    for i, s in enumerate(result.selling_points, 1):
        lines.append(f"   {i}. {s}")

    lines.append("")
    lines.append("[14] 상세페이지 구조")
    for i, s in enumerate(result.detail_structure, 1):
        lines.append(f"   {i}) {s}")
    lines.append("   --- 전문 초안 ---")
    for row in (result.detail_page_full or "").splitlines()[:40]:
        lines.append(f"   {row}")

    lines.append("")
    lines.append("[15] CTR 개선안")
    for s in result.ctr_tips:
        lines.append(f"   - {s}")
    lines.append("   [체류시간]")
    for s in result.dwell_tips:
        lines.append(f"   - {s}")

    lines.append("")
    lines.append("[16] CVR 개선안")
    for s in result.conversion_tips:
        lines.append(f"   - {s}")
    lines.append("   [체크리스트]")
    for k, v in result.checklist.items():
        lines.append(f"   - {k}: {v}")

    lines.append("")
    lines.append("[17] 대표이미지 개선안")
    img = result.image_insight
    lines.append("   [경쟁 패턴]")
    for s in img.competitor_patterns:
        lines.append(f"   - {s}")
    lines.append("   [내 갭]")
    for s in img.mine_gaps:
        lines.append(f"   - {s}")
    lines.append("   [개선]")
    for s in img.improvements:
        lines.append(f"   - {s}")

    lines.append("")
    lines.append("[18] 예상 순위 회복 효과")
    lines.append(f"   {result.rank_recovery_outlook}")
    lines.append(f"   {result.expected_effect}")

    lines.append("")
    lines.append("[19] SEO History 저장")
    lines.append(f"   {result.history_path or '(미저장)'}")
    for n in result.memory_notes[:8]:
        lines.append(f"   [Memory] {n}")

    lines.append("")
    lines.append("[20] Learning 결과 저장")
    lines.append(f"   {result.learning_path or '(미저장)'}")
    for n in result.learning_notes:
        if not n.startswith("[GAP]"):
            lines.append(f"   - {n}")

    ri = result.review_insight
    if ri.advantages or ri.complaints or ri.return_reasons:
        lines.append("")
        lines.append("--- 리뷰 인사이트 ---")
        lines.append(f"   장점: {', '.join(ri.advantages[:6])}")
        if ri.complaints:
            lines.append(f"   불만: {', '.join(ri.complaints[:4])}")
        if ri.return_reasons:
            lines.append(f"   반품: {', '.join(ri.return_reasons[:4])}")
        if ri.purchase_reasons:
            lines.append(f"   구매이유: {', '.join(ri.purchase_reasons[:4])}")

    lines.append("")
    return "\n".join(lines)


def save_history(
    result: RecoveryResult,
    bundle: CollectionBundle,
    *,
    changes: list[str] | None = None,
    rank_before: int | None = None,
    rank_after: int | None = None,
    ctr: float | None = None,
    cvr: float | None = None,
    change_reason: str = "",
) -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    pid = bundle.mine.product_id or "unknown"
    path = HISTORY_DIR / f"{pid}.json"
    records: list = []
    if path.exists():
        try:
            records = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(records, list):
                records = []
        except Exception:
            records = []

    best = (
        result.recommended_title.title
        if result.recommended_title
        else (
            result.title_options[0].title
            if result.title_options
            else bundle.mine.title
        )
    )
    rec = result.to_history_record(
        date=datetime.now().strftime("%Y-%m-%d"),
        title=best,
        changes=changes
        or [
            "상품명 재구성 제안 (AB)",
            "상세페이지 구조/상단 카피 변경 제안",
            "Golden Keyword / Gap 반영",
            "CTR/CVR/이미지 개선안",
        ],
        rank_before=rank_before,
        rank_after=rank_after,
        product_id=pid,
        keyword=bundle.keyword,
        ctr=ctr,
        cvr=cvr,
        added_keywords=result.missing_keywords[:20],
        removed_keywords=result.delete_candidates[:15],
        change_reason=change_reason
        or (
            "; ".join(result.recommendation_reasons[:2])
            if result.recommendation_reasons
            else "SEO recovery v3"
        ),
        marketplace=bundle.marketplace,
    )
    records.append(rec)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
