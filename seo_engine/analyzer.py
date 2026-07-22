# -*- coding: utf-8 -*-
"""Orchestrator v3: modular engines -> RecoveryResult."""
from __future__ import annotations

from seo_engine.engines.ab_test import AbTestEngine
from seo_engine.engines.competitor import CompetitorAnalyzer
from seo_engine.engines.ctr import CtrOptimizer
from seo_engine.engines.cvr import CvrOptimizer
from seo_engine.engines.detail import DetailPageGenerator
from seo_engine.engines.gap import SeoGapAnalyzer
from seo_engine.engines.golden import GoldenKeywordEngine
from seo_engine.engines.image import ImageAnalyzer
from seo_engine.engines.keyword_extractor import KeywordExtractor
from seo_engine.engines.learning import SelfLearningEngine
from seo_engine.engines.memory import SeoMemory
from seo_engine.engines.ranking import RankingMonitor
from seo_engine.engines.review import ReviewAnalyzer
from seo_engine.engines.score import SeoScoreEngine
from seo_engine.engines.title import TitleOptimizer
from seo_engine.engines.trend import CompetitorTrendMonitor
from seo_engine.models import CollectionBundle, RecoveryResult


class RecoveryAnalyzer:
    """Shared analysis engine — marketplace/collector agnostic."""

    def __init__(self) -> None:
        self.competitor = CompetitorAnalyzer()
        self.keywords = KeywordExtractor()
        self.gap = SeoGapAnalyzer()
        self.title = TitleOptimizer()
        self.review = ReviewAnalyzer()
        self.detail = DetailPageGenerator()
        self.ctr = CtrOptimizer()
        self.cvr = CvrOptimizer()
        self.image = ImageAnalyzer()
        self.score = SeoScoreEngine()
        self.golden = GoldenKeywordEngine()
        self.ab = AbTestEngine()
        self.ranking = RankingMonitor()
        self.learning = SelfLearningEngine()
        self.memory = SeoMemory()
        self.trend = CompetitorTrendMonitor()

    def analyze(
        self,
        bundle: CollectionBundle,
        *,
        rank_before: int | None = None,
        rank_after: int | None = None,
        title_variants: int = 8,
        ctr_before: float | None = None,
        ctr_after: float | None = None,
        cvr_before: float | None = None,
        cvr_after: float | None = None,
    ) -> RecoveryResult:
        comp = self.competitor.analyze(bundle)
        extracted = self.keywords.extract(bundle, comp)
        gap = self.gap.analyze(bundle, extracted)
        review = self.review.analyze(bundle)
        headline, detail_full, selling, structure = self.detail.generate(
            bundle, review, gap
        )
        titles = self.title.generate(bundle, extracted, gap, n=title_variants)
        best, ab_lines, rec_reasons = self.ab.compare(titles)
        ctr_tips, dwell = self.ctr.optimize(bundle, extracted)
        cvr_tips, checklist = self.cvr.optimize(bundle, review)
        image = self.image.analyze(bundle)
        breakdown = self.score.score(bundle, extracted, gap)
        golden = self.golden.build(bundle, extracted, gap)

        trend = self.trend.snapshot(bundle)
        trend_alerts = list(trend.get("alerts") or [])

        coverage = gap.coverage_pct
        score = breakdown.total

        outlook = (
            f"커버리지 {coverage}% / SEO {score}점 기준, "
            f"유실 키워드 {len(gap.missing)}개 보완 + 상품명 전반부 재배치 시 "
            f"검색 관련성·CTR 동시 회복 기대."
        )
        if rank_before and rank_after is None:
            outlook += f" 현재 관측 순위 {rank_before}위 — Ranking Monitor로 일일 추적 권장."
        if rank_before and rank_after:
            delta = rank_before - rank_after
            outlook += f" 순위 변화 {rank_before}->{rank_after} (Δ{delta:+d})."

        effect = (
            f"핵심 키워드 커버리지 {coverage}% -> 목표 90%+, "
            f"추천 상품명 적용 시 예상 SEO "
            f"{best.seo_score if best else score}/CTR {best.ctr_score if best else '-'} "
            f"(현재 SEO 추정 {score}/100)."
        )

        learning_notes = [f"[GAP] {gap.brand_position_note}"]
        for p in gap.priority_notes:
            learning_notes.append(f"[GAP] {p}")
        learning_notes.extend(
            self.learning.notes_for_product(bundle.mine.product_id or "")
        )

        if rank_after is not None or rank_before is not None:
            snap = self.ranking.record(
                product_id=bundle.mine.product_id or "unknown",
                keyword=bundle.keyword,
                rank=rank_after if rank_after is not None else rank_before,
                title=bundle.mine.title,
                source=bundle.source,
            )
            if snap.get("alert"):
                learning_notes.append(snap["alert"]["message"])

        memory_notes = self.memory.lessons(bundle.mine.product_id or "", limit=8)

        return RecoveryResult(
            seo_score=score,
            score_breakdown=breakdown,
            keyword_coverage=coverage,
            golden_keywords=golden,
            missing_keywords=gap.missing,
            unused_keywords=gap.unused,
            delete_candidates=gap.delete_candidates,
            duplicate_keywords=gap.duplicates,
            gaps=gap.gaps,
            title_options=titles,
            recommended_title=best,
            headline_copy=headline,
            detail_page_full=detail_full,
            selling_points=selling,
            detail_structure=structure,
            ctr_tips=ctr_tips,
            conversion_tips=cvr_tips,
            dwell_tips=dwell,
            image_insight=image,
            review_insight=review,
            checklist=checklist,
            expected_effect=effect,
            rank_recovery_outlook=outlook,
            keyword_scores={e.keyword: e.effect for e in extracted[:30]},
            ab_test_summary=ab_lines,
            recommendation_reasons=rec_reasons,
            competitor_summaries=comp.summaries,
            learning_notes=learning_notes,
            memory_notes=memory_notes,
            trend_alerts=trend_alerts,
        )


def analyze(bundle: CollectionBundle, **kwargs) -> RecoveryResult:
    return RecoveryAnalyzer().analyze(bundle, **kwargs)
