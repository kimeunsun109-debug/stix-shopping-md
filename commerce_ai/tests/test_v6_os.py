# -*- coding: utf-8 -*-
"""Unit + integration + smoke tests for Commerce AI v6."""
from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from commerce_ai.cache import TtlCache
from commerce_ai.confidence import ConfidenceEngine
from commerce_ai.container import CommerceContainer, set_container
from commerce_ai.execution import (
    CoupangExecutor,
    ExecutionPlanner,
    GmarketExecutor,
    NoOpExecutor,
    SmartStoreExecutor,
)
from commerce_ai.memory import CommerceMemory, current_season, price_band
from commerce_ai.models import (
    KnowledgeContext,
    RecommendationCard,
    VerificationSnapshot,
)
from commerce_ai.monitoring import SystemMonitor
from commerce_ai.recommendation_engine import RecommendationEngine
from commerce_ai.stability.resilience import RateLimiter, RetryPolicy, safe_call, with_retry
from commerce_ai.verification import VerificationEngine
from seo_engine.models import (
    CollectionBundle,
    ImageInsight,
    ProductSnapshot,
    RecoveryResult,
    ReviewInsight,
    ScoreBreakdown,
    TitleVariant,
)


def _fake_seo() -> RecoveryResult:
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


class TestStability(unittest.TestCase):
    def test_safe_call_returns_default(self):
        def boom():
            raise ValueError("x")

        self.assertEqual(safe_call(boom, default=42, component="test.safe"), 42)

    def test_retry_succeeds(self):
        state = {"n": 0}

        def flaky():
            state["n"] += 1
            if state["n"] < 2:
                raise RuntimeError("once")
            return "ok"

        self.assertEqual(
            with_retry(flaky, policy=RetryPolicy(max_attempts=3, base_delay_sec=0.01)),
            "ok",
        )

    def test_rate_limiter(self):
        lim = RateLimiter(max_calls=2, period_sec=10.0)
        self.assertTrue(lim.acquire(timeout=0.1))
        self.assertTrue(lim.acquire(timeout=0.1))
        self.assertFalse(lim.acquire(timeout=0.05))


class TestConfidenceV6(unittest.TestCase):
    def test_returns_evidence_and_failure_risk(self):
        mem = CommerceMemory(path=Path(tempfile.mkdtemp()) / "m.jsonl")
        for i in range(5):
            mem.record(
                product_id=f"p{i}",
                marketplace="coupang",
                keyword="k",
                action="상품명 변경",
                reason="ok",
                category="title",
                outcome="success",
                context=KnowledgeContext(
                    marketplace="coupang",
                    season=current_season(),
                    price_band="10k_30k",
                ),
                metrics_before={"ctr": 0.02},
                metrics_after={"ctr": 0.025},
            )
        eng = ConfidenceEngine(mem)
        conf, unc, evidence, fail = eng.score(
            "title",
            has_metrics=True,
            competitor_support=True,
            marketplace="coupang",
            price=19900,
        )
        self.assertGreaterEqual(conf, 35)
        self.assertLessEqual(conf, 96)
        self.assertIn("성공", evidence)
        self.assertIn("실패", fail)


class TestRecommendationEvidence(unittest.TestCase):
    def test_cards_include_evidence(self):
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
            marketplace="coupang",
        )
        metrics = CommerceMetrics(revenue=100000, ctr=0.03, cvr=0.02, rank=10)
        price = PriceRecommendation(
            19900, 18900, 18000, 15000, 21000, -3.0, 2, 10.0, 5.0, ["avg"]
        )
        forecast = RevenueForecast(
            100000, 120000, 20.0, None, None, None, 0.04, 0.025, None, None
        )
        eng = RecommendationEngine(
            ConfidenceEngine(CommerceMemory(path=Path(tempfile.mkdtemp()) / "m.jsonl"))
        )
        cards = eng.build(bundle, seo, metrics, price, forecast, [])
        self.assertTrue(any(c.action.startswith("상품명") for c in cards))
        self.assertTrue(all(c.evidence for c in cards))
        self.assertTrue(all(c.failure_risk for c in cards))


class TestExecutors(unittest.TestCase):
    def test_marketplace_executors_dry_run(self):
        for ex in (CoupangExecutor(), SmartStoreExecutor(), GmarketExecutor()):
            preview = ex.preview("title_update", {"to": "x"})
            self.assertIn(ex.marketplace, preview.lower())
            result = ex.execute("title_update", {"to": "x"})
            self.assertTrue(result["ok"])
            self.assertTrue(result.get("dry_run"))

    def test_approve_requires_flag(self):
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
                evidence="e",
                failure_risk="f",
                payload={"to": "new title"},
            )
        ]
        plan = planner.build_plan(
            product_id="p1",
            marketplace="coupang",
            keyword="k",
            recommendations=cards,
        )
        step = planner.approve_step(plan, plan.steps[0].step_id, execute=False)
        self.assertEqual(step.status, "approved")
        step2 = planner.approve_step(plan, plan.steps[0].step_id, execute=True)
        self.assertEqual(step2.status, "executed")
        self.assertTrue(step2.params["execution_result"]["dry_run"])


class TestVerificationMetrics(unittest.TestCase):
    def test_aggregate_and_memory_sync(self):
        tmp = Path(tempfile.mkdtemp())
        mem = CommerceMemory(path=tmp / "m.jsonl")
        mem.record(
            product_id="p1",
            marketplace="coupang",
            keyword="k",
            action="상품명 변경",
            reason="r",
            category="title",
            recommendation_id="r1",
            outcome="pending",
        )
        eng = VerificationEngine(tmp / "v.jsonl", memory=mem)
        eng.open_case(
            recommendation_id="r1",
            action="상품명 변경",
            product_id="p1",
            baseline={"ctr": 0.02, "cvr": 0.01, "revenue": 100000, "rank": 10, "roas": 2.0},
            expected_lift={"ctr": 10, "revenue": 7},
        )
        res = eng.record_checkpoint(
            "r1",
            7,
            VerificationSnapshot(
                day=7, ctr=0.025, cvr=0.012, revenue=110000, rank=7, roas=2.2
            ),
            mark_final=True,
            sync_memory=True,
        )
        self.assertIsNotNone(res)
        self.assertIn(res.status, {"success", "partial", "fail"})
        m = eng.aggregate_metrics()
        self.assertIsNotNone(m.success_rate or m.fail_rate or m.n_pending >= 0)
        self.assertTrue(m.avg_ctr_delta_pct is not None or res.status == "pending")


class TestMemoryKB(unittest.TestCase):
    def test_similar_success_matching(self):
        path = Path(tempfile.mkdtemp()) / "m.jsonl"
        mem = CommerceMemory(path)
        ctx = KnowledgeContext(
            marketplace="coupang",
            season=current_season(),
            price_band=price_band(19900),
            category="hobby",
        )
        mem.record(
            product_id="p1",
            marketplace="coupang",
            keyword="k",
            action="상품명 변경",
            reason="ok",
            category="title",
            outcome="success",
            context=ctx,
            metrics_before={"ctr": 0.02},
            metrics_after={"ctr": 0.03},
        )
        similar = mem.find_similar_successes(action_category="title", context=ctx)
        self.assertEqual(len(similar), 1)
        evidence, avg = mem.evidence_for("title", ctx)
        self.assertIn("성공", evidence)


class TestCache(unittest.TestCase):
    def test_ttl_cache(self):
        c = TtlCache(default_ttl_sec=0.2)
        c.set("n", {"a": 1}, 99)
        self.assertEqual(c.get("n", {"a": 1}), 99)
        time.sleep(0.25)
        self.assertIsNone(c.get("n", {"a": 1}))


class TestMonitor(unittest.TestCase):
    def test_health_dict(self):
        h = SystemMonitor().health()
        self.assertIn("ok", h.to_dict())
        self.assertTrue(isinstance(h.ok, bool))


class TestSmokePipeline(unittest.TestCase):
    def test_analyze_smoke(self):
        from commerce_ai.analyzer import CommerceAnalyzer
        from commerce_ai.models import CommerceInput, CommerceMetrics

        tmp = Path(tempfile.mkdtemp())
        mem = CommerceMemory(path=tmp / "m.jsonl")
        ver = VerificationEngine(tmp / "v.jsonl", memory=mem)
        container = CommerceContainer(memory=mem, verification=ver)
        set_container(container)
        bundle = CollectionBundle(
            keyword="보석십자수",
            mine=ProductSnapshot(
                title="보석십자수 키트", product_id="demo-v6", price=19900
            ),
            competitors=[],
            marketplace="coupang",
        )
        # analyzer needs seo engine — use real if available
        result = CommerceAnalyzer(container).analyze(
            bundle,
            commerce=CommerceInput(revenue=100000, ctr=0.03, cvr=0.02, rank=10),
            use_cache=False,
        )
        self.assertGreater(result.commerce_score, 0)
        self.assertTrue(result.recommendations)
        self.assertIsNotNone(result.execution_plan)
        self.assertEqual(result.to_dict()["version"], "6.0")


if __name__ == "__main__":
    unittest.main()
