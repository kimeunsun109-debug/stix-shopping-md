# -*- coding: utf-8 -*-
"""Unit tests for Commerce AI v5 OS layers (stdlib unittest)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from commerce_ai.confidence import ConfidenceEngine
from commerce_ai.container import CommerceContainer, set_container
from commerce_ai.execution import ExecutionPlanner, NoOpExecutor
from commerce_ai.memory import CommerceMemory
from commerce_ai.models import RecommendationCard, VerificationSnapshot
from commerce_ai.recommendation_engine import RecommendationEngine
from commerce_ai.verification import VerificationEngine
from seo_engine.models import (
    CollectionBundle,
    ImageInsight,
    ProductSnapshot,
    RecoveryResult,
    ReviewInsight,
    ScoreBreakdown,
)


def _fake_seo() -> RecoveryResult:
    from seo_engine.models import TitleVariant

    return RecoveryResult(
        seo_score=60,
        score_breakdown=ScoreBreakdown(total=60),
        keyword_coverage=50,
        golden_keywords=[],
        missing_keywords=["집콕", "액자형"],
        unused_keywords=[],
        delete_candidates=["튜립"],
        duplicate_keywords=[],
        gaps=[],
        title_options=[
            TitleVariant(
                title="DIY 보석십자수 키트 스팃스",
                seo_score=85,
                ctr_score=70,
                cvr_score=65,
                expected_impressions=0.5,
                expected_purchase_rate=0.05,
                composite=75,
                reasons=["DIY 전반부"],
            )
        ],
        recommended_title=TitleVariant(
            title="DIY 보석십자수 키트 스팃스",
            seo_score=85,
            ctr_score=70,
            cvr_score=65,
            expected_impressions=0.5,
            expected_purchase_rate=0.05,
            composite=75,
            reasons=["DIY 전반부"],
        ),
        headline_copy="x",
        detail_page_full="x",
        selling_points=["a"],
        detail_structure=["s"],
        ctr_tips=[],
        conversion_tips=[],
        dwell_tips=[],
        image_insight=ImageInsight(improvements=["밝은 배경"]),
        review_insight=ReviewInsight(),
        checklist={},
        expected_effect="",
        rank_recovery_outlook="",
        recommendation_reasons=["DIY를 앞쪽에 배치"],
    )


class TestConfidence(unittest.TestCase):
    def test_score_range(self):
        mem = CommerceMemory(path=Path(tempfile.mkdtemp()) / "m.jsonl")
        eng = ConfidenceEngine(mem)
        c, *_ = eng.score("title", has_metrics=True, competitor_support=True)
        self.assertGreaterEqual(c, 35)
        self.assertLessEqual(c, 96)


class TestRecommendation(unittest.TestCase):
    def test_builds_cards_with_confidence(self):
        from commerce_ai.models import (
            CommerceMetrics,
            PriceRecommendation,
            RevenueForecast,
        )

        seo = _fake_seo()
        bundle = CollectionBundle(
            keyword="보석십자수",
            mine=ProductSnapshot(title="old", product_id="p1", price=19900),
            competitors=[],
        )
        metrics = CommerceMetrics(revenue=100000, ctr=0.03, cvr=0.02, rank=10)
        price = PriceRecommendation(
            19900, 18900, 18000, 15000, 21000, -3.0, 2, 10.0, 5.0, ["avg"]
        )
        forecast = RevenueForecast(
            100000, 120000, 20.0, None, None, None, 0.04, 0.025, None, None
        )
        eng = RecommendationEngine(ConfidenceEngine(CommerceMemory(
            path=Path(tempfile.mkdtemp()) / "m.jsonl"
        )))
        cards = eng.build(bundle, seo, metrics, price, forecast, [])
        self.assertTrue(any(c.action.startswith("상품명") for c in cards))
        self.assertTrue(all(0 < c.confidence <= 100 for c in cards))


class TestExecution(unittest.TestCase):
    def test_approve_dry_run(self):
        planner = ExecutionPlanner()
        cards = [
            RecommendationCard(
                id="abc",
                action="상품명 변경",
                category="title",
                reason="r",
                expected_effect="e",
                metric="CTR",
                lift_pct=10,
                revenue_lift_pct=5,
                priority=1,
                risk="low",
                effort_minutes=5,
                confidence=90,
                payload={"to": "new title"},
            )
        ]
        plan = planner.build_plan(
            product_id="p1",
            marketplace="coupang",
            keyword="k",
            recommendations=cards,
        )
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].status, "pending_approval")
        step = planner.approve_step(plan, plan.steps[0].step_id, execute=True)
        self.assertEqual(step.status, "executed")
        self.assertTrue(step.params["execution_result"]["dry_run"])


class TestVerification(unittest.TestCase):
    def test_open_and_checkpoint(self):
        path = Path(tempfile.mkdtemp()) / "v.jsonl"
        eng = VerificationEngine(path)
        eng.open_case(
            recommendation_id="r1",
            action="상품명 변경",
            product_id="p1",
            baseline={"ctr": 0.02, "cvr": 0.01, "revenue": 100000, "rank": 10},
            expected_lift={"ctr": 10, "revenue": 7},
        )
        res = eng.record_checkpoint(
            "r1",
            7,
            VerificationSnapshot(day=7, ctr=0.025, cvr=0.012, revenue=110000, rank=7),
            mark_final=True,
        )
        self.assertIsNotNone(res)
        self.assertIn(res.status, {"success", "partial", "fail"})


class TestMemoryStats(unittest.TestCase):
    def test_action_stats(self):
        path = Path(tempfile.mkdtemp()) / "m.jsonl"
        mem = CommerceMemory(path)
        mem.record(
            product_id="p1",
            marketplace="coupang",
            keyword="k",
            action="상품명 변경",
            reason="ok",
            category="title",
            outcome="success",
            metrics_before={"ctr": 0.02},
            metrics_after={"ctr": 0.03},
        )
        mem.record(
            product_id="p1",
            marketplace="coupang",
            keyword="k",
            action="상품명 변경",
            reason="bad",
            category="title",
            outcome="fail",
            metrics_before={"ctr": 0.03},
            metrics_after={"ctr": 0.02},
        )
        st = mem.action_stats("title")
        self.assertEqual(st["n"], 2)
        self.assertAlmostEqual(st["success_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
