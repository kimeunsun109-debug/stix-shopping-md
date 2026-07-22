# -*- coding: utf-8 -*-
"""AI MD Planner v5 — effect-sorted daily work with confidence/risk."""
from __future__ import annotations

from commerce_ai.models import (
    AlertItem,
    PlannerTask,
    RecommendationCard,
)


class AiMdPlanner:
    def plan_from_recommendations(
        self,
        recommendations: list[RecommendationCard],
        alerts: list[AlertItem] | None = None,
    ) -> list[PlannerTask]:
        tasks: list[PlannerTask] = []
        for rec in recommendations:
            difficulty = (
                "hard"
                if rec.effort_minutes >= 40
                else ("medium" if rec.effort_minutes >= 15 else "easy")
            )
            tasks.append(
                PlannerTask(
                    priority=rec.priority,
                    title=rec.action,
                    category=rec.category,
                    expected_effect=rec.expected_effect,
                    effort_minutes=rec.effort_minutes,
                    impact_score=round(
                        rec.confidence * 0.4
                        + rec.lift_pct * 2
                        + rec.revenue_lift_pct * 3,
                        1,
                    ),
                    details=f"{rec.reason} | 신뢰도 {rec.confidence:.0f}%",
                    confidence=rec.confidence,
                    risk=rec.risk,
                    difficulty=difficulty,
                    must_do_today=rec.must_do_today,
                )
            )
        # ensure critical alerts surface
        for a in alerts or []:
            if a.code in {"RANK_DROP", "STOCK_LOW"} and not any(
                a.code.lower() in t.title.lower() or a.message[:10] in t.details
                for t in tasks
            ):
                tasks.insert(
                    0,
                    PlannerTask(
                        priority=1,
                        title=a.action or a.message[:30],
                        category="seo" if a.code == "RANK_DROP" else "stock",
                        expected_effect=a.message,
                        effort_minutes=20,
                        impact_score=95,
                        details=a.message,
                        confidence=80,
                        risk="high",
                        difficulty="medium",
                        must_do_today=True,
                    ),
                )
        tasks.sort(
            key=lambda t: (
                0 if t.must_do_today else 1,
                -t.impact_score,
                -t.confidence,
            )
        )
        for i, t in enumerate(tasks[:12], 1):
            t.priority = i
        return tasks[:12]

    # v4 compat
    def plan(self, *args, **kwargs):
        # unused in v5 analyzer — keep for import safety
        from commerce_ai.models import (
            AutoRec,
            CommerceMetrics,
            PriceRecommendation,
            RevenueForecast,
        )
        from seo_engine.models import CollectionBundle, RecoveryResult

        # signature ignored — empty
        return []
