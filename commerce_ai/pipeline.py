# -*- coding: utf-8 -*-
"""Commerce pipeline v6: resilient analyze -> memory KB -> verification."""
from __future__ import annotations

from pathlib import Path

from commerce_ai.analyzer import CommerceAnalyzer
from commerce_ai.container import get_container
from commerce_ai.learning import LEARN_PATH, CommerceLearningEngine
from commerce_ai.memory import current_season, price_band
from commerce_ai.models import CommerceInput, CommerceResult, KnowledgeContext
from commerce_ai.report import format_commerce_report
from commerce_ai.stability.errors import report_error
from commerce_ai.stability.logging_setup import get_logger, setup_logging
from commerce_ai.stability.resilience import RetryPolicy, safe_call
from seo_engine.collectors.base import BaseCollector
from seo_engine.models import CollectionBundle

_log = get_logger("commerce_ai.pipeline")


def run_commerce(
    collector: BaseCollector,
    *,
    commerce: CommerceInput | None = None,
    save: bool = True,
    report_path: str | Path | None = None,
    title_variants: int = 8,
    open_verification: bool = True,
) -> tuple[CollectionBundle, CommerceResult, str]:
    setup_logging()
    bundle = safe_call(
        collector.collect,
        component="collector.collect",
        timeout_sec=90.0,
        retry=RetryPolicy(max_attempts=2, base_delay_sec=0.5),
        default=None,
    )
    if bundle is None:
        report_error(
            "collector",
            message="collection failed after retries",
            recoverable=False,
        )
        raise RuntimeError("Collector failed — pipeline aborted safely")

    analyzer = CommerceAnalyzer()
    result = analyzer.analyze(
        bundle, commerce=commerce, title_variants=title_variants, use_cache=False
    )
    c = get_container()

    if save:
        actions = [r.action for r in result.recommendations[:5]]
        ctx = KnowledgeContext(
            marketplace=bundle.marketplace,
            season=current_season(),
            price_band=price_band(bundle.mine.price),
            image_traits=list(result.seo.image_insight.improvements[:3]),
            review_traits=list(
                result.seo.review_insight.advantages[:2]
                + result.seo.review_insight.complaints[:2]
            ),
        )
        for rec in result.recommendations[:5]:
            safe_call(
                lambda r=rec: c.memory.record(
                    product_id=bundle.mine.product_id or "unknown",
                    marketplace=bundle.marketplace,
                    keyword=bundle.keyword,
                    action=r.action,
                    reason=r.reason,
                    category=r.category,
                    recommendation_id=r.id,
                    outcome="pending",
                    context=ctx,
                    price=bundle.mine.price,
                    metrics_before={
                        "ctr": (commerce.ctr_yesterday if commerce else None)
                        or result.metrics.ctr,
                        "cvr": (commerce.cvr_yesterday if commerce else None)
                        or result.metrics.cvr,
                        "revenue": result.metrics.revenue,
                        "rank": (commerce.rank_yesterday if commerce else None)
                        or result.metrics.rank,
                        "price": bundle.mine.price,
                    },
                    metrics_after={},
                    tags=["commerce_v6", "recommendation"],
                ),
                component="pipeline.memory",
                default=None,
            )
            if open_verification and c.verification is not None:
                safe_call(
                    lambda r=rec: c.verification.open_case(
                        recommendation_id=r.id,
                        action=r.action,
                        product_id=bundle.mine.product_id or "unknown",
                        category=r.category,
                        baseline={
                            "ctr": result.metrics.ctr,
                            "cvr": result.metrics.cvr,
                            "revenue": result.metrics.revenue,
                            "rank": result.metrics.rank,
                            "profit": result.metrics.profit,
                            "roas": result.metrics.roas,
                            "impressions": result.metrics.impressions,
                        },
                        expected_lift={
                            "ctr": r.lift_pct if r.metric == "CTR" else 0,
                            "cvr": r.lift_pct if r.metric == "CVR" else 0,
                            "revenue": r.revenue_lift_pct,
                        },
                    ),
                    component="pipeline.verification",
                    default=None,
                )

        result.memory_path = str(c.memory.path)
        result.memory_notes = c.memory.lessons(
            bundle.mine.product_id or "", limit=8
        )

        learner = CommerceLearningEngine()
        ev = safe_call(
            lambda: learner.log_change(
                product_id=bundle.mine.product_id or "unknown",
                marketplace=bundle.marketplace,
                keyword=bundle.keyword,
                actions=actions,
                seo_score=result.seo.seo_score,
                revenue_score=result.revenue_score,
                rank_before=commerce.rank_yesterday
                if commerce
                else result.metrics.rank,
                snapshot={
                    "commerce_score": result.commerce_score,
                    "plan_id": result.execution_plan.plan_id
                    if result.execution_plan
                    else "",
                    "recommendations": [r.id for r in result.recommendations[:5]],
                    "version": "6.0",
                },
            ),
            component="pipeline.learning",
            default={},
        ) or {}
        result.learning_path = str(LEARN_PATH)
        result.learning_notes.append(
            f"Learning event: {ev.get('date', '?')} / verify 1·7·14·30일"
        )

        try:
            from seo_engine.history import save_history

            hpath = save_history(
                result.seo,
                bundle,
                rank_before=commerce.rank_yesterday if commerce else None,
                rank_after=commerce.rank if commerce else None,
                ctr=result.metrics.ctr,
                cvr=result.metrics.cvr,
                change_reason="Commerce AI v6",
            )
            result.seo.history_path = str(hpath)
        except Exception as e:
            report_error("pipeline.seo_history", e, recoverable=True)

    report = format_commerce_report(bundle, result)
    if report_path:
        safe_call(
            lambda: Path(report_path).write_text(report, encoding="utf-8"),
            component="pipeline.report_write",
            default=None,
        )
    return bundle, result, report
