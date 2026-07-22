# -*- coding: utf-8 -*-
"""Commerce Analyzer v6 — OS orchestration with recovery."""
from __future__ import annotations

from commerce_ai.cache import CACHE
from commerce_ai.container import CommerceContainer, get_container
from commerce_ai.models import CommerceInput, CommerceResult, VerificationMetrics
from commerce_ai.stability.logging_setup import get_logger, setup_logging
from commerce_ai.stability.recovery import recover
from commerce_ai.stability.resilience import safe_call
from seo_engine.models import CollectionBundle

_log = get_logger("commerce_ai.analyzer")


class CommerceAnalyzer:
    def __init__(self, container: CommerceContainer | None = None) -> None:
        setup_logging()
        self.c = container or get_container()

    def analyze(
        self,
        bundle: CollectionBundle,
        *,
        commerce: CommerceInput | None = None,
        title_variants: int = 8,
        use_cache: bool = True,
    ) -> CommerceResult:
        commerce = commerce or CommerceInput()
        c = self.c
        cache_key = {
            "pid": bundle.mine.product_id,
            "kw": bundle.keyword,
            "mp": bundle.marketplace,
            "title": bundle.mine.title,
            "rev": commerce.revenue,
            "rank": commerce.rank,
        }
        if use_cache:
            hit = CACHE.get("analyze", cache_key)
            if hit is not None:
                _log.info("cache hit analyze %s", bundle.mine.product_id)
                return hit

        seo_result, _ = recover(
            "analyzer.seo",
            lambda: c.seo.analyze(
                bundle,
                rank_before=commerce.rank_yesterday,
                rank_after=commerce.rank,
                title_variants=title_variants,
                ctr_before=commerce.ctr_yesterday,
                ctr_after=commerce.ctr,
                cvr_before=commerce.cvr_yesterday,
                cvr_after=commerce.cvr,
            ),
            fallback=None,
            default=None,
        )
        if seo_result is None:
            raise RuntimeError("SEO analyzer failed and no fallback available")

        thumb = safe_call(
            c.thumbnail.analyze,
            bundle,
            component="analyzer.thumbnail",
            default=None,
        )
        if thumb is not None:
            seo_result.image_insight = c.thumbnail.to_image_insight(thumb)

        comp_result = safe_call(
            c.competitor.analyze,
            bundle,
            component="analyzer.competitor",
            default=([], []),
        )
        comp_summaries, comp_changes = comp_result or ([], [])
        if comp_summaries:
            seo_result.competitor_summaries = comp_summaries
        seo_result.trend_alerts = list(seo_result.trend_alerts) + [
            x for x in comp_changes if "키워드" in x
        ]

        metrics = c.revenue.build_metrics(bundle, commerce, seo_result)
        price_rec = c.price.recommend(bundle, metrics, commerce)
        vol = (price_rec.expected_volume_lift_pct or 0) / 100
        forecast = c.revenue.forecast(
            metrics, seo_result, price_lift_vol=max(0.0, vol)
        )
        rev_score = c.revenue.score(metrics, seo_result)

        alerts = safe_call(
            c.alerts.detect,
            bundle,
            metrics,
            seo_result,
            commerce,
            comp_changes,
            component="analyzer.alerts",
            default=[],
        ) or []

        assert c.recommendations is not None
        cards = c.recommendations.build(
            bundle, seo_result, metrics, price_rec, forecast, alerts
        )
        auto_recs = c.recommendations.to_auto_recs(cards)
        tasks = c.planner.plan_from_recommendations(cards, alerts)

        assert c.execution is not None
        plan = c.execution.build_plan(
            product_id=bundle.mine.product_id or "unknown",
            marketplace=bundle.marketplace,
            keyword=bundle.keyword,
            recommendations=cards,
        )

        assert c.verification is not None
        vmetrics = c.verification.aggregate_metrics(bundle.mine.product_id or "")
        ok_rate, fail_rate = vmetrics.success_rate, vmetrics.fail_rate
        due = [
            {
                "recommendation_id": d.get("recommendation_id"),
                "action": d.get("action"),
                "dueDays": d.get("dueDays"),
                "productId": d.get("product_id"),
            }
            for d in c.verification.due()
            if not bundle.mine.product_id
            or d.get("product_id") == bundle.mine.product_id
        ][:10]

        avg_conf = (
            sum(x.confidence for x in cards) / len(cards) if cards else 60
        )
        commerce_score = int(
            round(
                max(
                    0,
                    min(
                        100,
                        seo_result.seo_score * 0.35
                        + rev_score * 0.45
                        + avg_conf * 0.20,
                    ),
                )
            )
        )

        learn_notes = safe_call(
            c.learning.notes_for_product,
            bundle.mine.product_id or "",
            component="analyzer.learning",
            default=[],
        ) or []

        health = safe_call(
            c.monitor.health,
            component="analyzer.monitor",
            default=None,
        )

        result = CommerceResult(
            seo=seo_result,
            metrics=metrics,
            revenue_score=rev_score,
            revenue_forecast=forecast,
            price_rec=price_rec,
            alerts=alerts,
            planner_tasks=tasks,
            auto_recs=auto_recs,
            recommendations=cards,
            execution_plan=plan,
            verification_due=due,
            verification_metrics=vmetrics,
            competitor_changes=comp_changes,
            thumbnail_tips=(
                [
                    f"[{thumb.provider}] 배경:{thumb.background} 텍스트:{thumb.text_density} "
                    f"손:{thumb.hand_present} 시선:{thumb.attention}"
                ]
                + thumb.improvements
                if thumb is not None
                else list(seo_result.image_insight.improvements)
            ),
            commerce_score=commerce_score,
            recommendation_success_rate=ok_rate,
            recommendation_fail_rate=fail_rate,
            recommendation_accuracy=ok_rate,
            learning_notes=learn_notes,
            system_health_ok=health.ok if health else None,
        )
        if use_cache:
            CACHE.set("analyze", cache_key, result, ttl_sec=120.0)
        return result
