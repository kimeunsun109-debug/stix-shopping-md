# -*- coding: utf-8 -*-
"""Pipeline v3: collect -> analyze -> report -> history -> memory -> learning."""
from __future__ import annotations

from pathlib import Path

from seo_engine.analyzer import RecoveryAnalyzer
from seo_engine.collectors.base import BaseCollector
from seo_engine.engines.learning import SelfLearningEngine
from seo_engine.engines.memory import SeoMemory
from seo_engine.history import format_report, save_history
from seo_engine.models import CollectionBundle, RecoveryResult


def run_recovery(
    collector: BaseCollector,
    *,
    save: bool = True,
    rank_before: int | None = None,
    rank_after: int | None = None,
    ctr: float | None = None,
    cvr: float | None = None,
    ctr_before: float | None = None,
    ctr_after: float | None = None,
    cvr_before: float | None = None,
    cvr_after: float | None = None,
    report_path: str | Path | None = None,
    title_variants: int = 8,
) -> tuple[CollectionBundle, RecoveryResult, str]:
    bundle = collector.collect()
    analyzer = RecoveryAnalyzer()
    result = analyzer.analyze(
        bundle,
        rank_before=rank_before,
        rank_after=rank_after,
        title_variants=title_variants,
        ctr_before=ctr_before,
        ctr_after=ctr_after or ctr,
        cvr_before=cvr_before,
        cvr_after=cvr_after or cvr,
    )

    if save:
        path = save_history(
            result,
            bundle,
            rank_before=rank_before,
            rank_after=rank_after,
            ctr=ctr_after or ctr,
            cvr=cvr_after or cvr,
            change_reason="; ".join(result.recommendation_reasons[:2]),
        )
        result.history_path = str(path)

        learner = SelfLearningEngine()
        ev = learner.log_change(
            product_id=bundle.mine.product_id or "unknown",
            keyword=bundle.keyword,
            category=bundle.mine.category or bundle.keyword,
            title=(
                result.recommended_title.title
                if result.recommended_title
                else bundle.mine.title
            ),
            added_keywords=result.missing_keywords[:20],
            removed_keywords=result.delete_candidates[:15],
            seo_score=result.seo_score,
            rank_before=rank_before,
        )
        result.learning_path = str(
            Path(__file__).resolve().parent.parent / "seo_history" / "learning_events.jsonl"
        )
        result.learning_notes.append(
            f"Learning event 기록: {ev.get('date')} / checkpoints 7·14·30일"
        )

        mem = SeoMemory()
        mem.record(
            product_id=bundle.mine.product_id or "unknown",
            keyword=bundle.keyword,
            action="SEO Recovery 제안",
            reason="; ".join(result.recommendation_reasons[:2])
            or "상품명/키워드 복구",
            keywords=result.missing_keywords[:10],
            rank_before=rank_before,
            rank_after=rank_after,
            ctr_before=ctr_before,
            ctr_after=ctr_after or ctr,
            cvr_before=cvr_before,
            cvr_after=cvr_after or cvr,
            marketplace=bundle.marketplace,
        )
        result.memory_notes = mem.lessons(bundle.mine.product_id or "", limit=8)

        if rank_before is not None and rank_after is not None and rank_after < rank_before:
            analyzer.golden.record_success(
                bundle.mine.category or bundle.keyword or "default",
                result.missing_keywords[:20],
                rank_before=rank_before,
                rank_after=rank_after,
                ctr_before=ctr_before,
                ctr_after=ctr_after or ctr,
                cvr_before=cvr_before,
                cvr_after=cvr_after or cvr,
            )
            result.learning_notes.append(
                f"즉시학습: 순위개선 {rank_before}->{rank_after}, Golden Dictionary 갱신"
            )

    report = format_report(bundle, result)
    if report_path:
        Path(report_path).write_text(report, encoding="utf-8")
    return bundle, result, report
