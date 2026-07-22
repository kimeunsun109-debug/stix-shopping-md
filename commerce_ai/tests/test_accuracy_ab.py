# -*- coding: utf-8 -*-
"""Accuracy / A/B / Memory growth tests — no new engines."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from commerce_ai.confidence import ConfidenceEngine
from commerce_ai.memory import CommerceMemory
from commerce_ai.models import KnowledgeContext
from commerce_ai.recommendation_engine import RecommendationEngine
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


def _seo() -> RecoveryResult:
    t1 = TitleVariant(
        title="DIY 보석십자수 키트 A",
        seo_score=85,
        ctr_score=70,
        cvr_score=65,
        expected_impressions=0.5,
        expected_purchase_rate=0.05,
        composite=75,
        reasons=["A"],
    )
    t2 = TitleVariant(
        title="집콕 DIY 보석십자수 B",
        seo_score=80,
        ctr_score=68,
        cvr_score=64,
        expected_impressions=0.45,
        expected_purchase_rate=0.05,
        composite=72,
        reasons=["B"],
    )
    return RecoveryResult(
        seo_score=60,
        score_breakdown=ScoreBreakdown(total=60),
        keyword_coverage=50,
        golden_keywords=[],
        missing_keywords=["집콕"],
        unused_keywords=[],
        delete_candidates=[],
        duplicate_keywords=[],
        gaps=[],
        title_options=[t1, t2],
        recommended_title=t1,
        headline_copy="x",
        detail_page_full="x",
        selling_points=["a"],
        detail_structure=["s"],
        ctr_tips=[],
        conversion_tips=[],
        dwell_tips=[],
        image_insight=ImageInsight(improvements=["밝은 배경", "제품 클로즈업"]),
        review_insight=ReviewInsight(),
        checklist={},
        expected_effect="",
        rank_recovery_outlook="",
        recommendation_reasons=["DIY 전반부"],
    )


class TestABRecommendations(unittest.TestCase):
    def test_title_image_price_have_ab(self):
        from commerce_ai.models import (
            CommerceMetrics,
            PriceRecommendation,
            RevenueForecast,
        )

        mem = CommerceMemory(path=Path(tempfile.mkdtemp()) / "m.jsonl")
        eng = RecommendationEngine(ConfidenceEngine(mem))
        cards = eng.build(
            CollectionBundle(
                keyword="보석십자수",
                mine=ProductSnapshot(title="old", product_id="p1", price=19900),
                competitors=[],
                marketplace="coupang",
            ),
            _seo(),
            CommerceMetrics(revenue=100000, ctr=0.03, cvr=0.02, rank=10),
            PriceRecommendation(
                19900, 18900, 18000, 15000, 21000, -3.0, 2, 10.0, 5.0, ["avg"]
            ),
            RevenueForecast(
                100000, 120000, 20.0, None, None, None, 0.04, 0.025, None, None
            ),
            [],
        )
        title = next(c for c in cards if c.action.startswith("상품명"))
        self.assertIsNotNone(title.ab_test)
        self.assertEqual(title.ab_test.metric, "CTR")
        self.assertTrue(title.evidence)
        self.assertTrue(title.failure_risk)
        img = next(c for c in cards if "이미지" in c.action)
        self.assertIsNotNone(img.ab_test)


class TestMemoryRecentAndAB(unittest.TestCase):
    def test_ab_winner_and_recent_evidence(self):
        path = Path(tempfile.mkdtemp()) / "m.jsonl"
        mem = CommerceMemory(path)
        ctx = KnowledgeContext(
            marketplace="coupang", season="summer", price_band="10k_30k"
        )
        for i in range(5):
            e = mem.record(
                product_id=f"p{i}",
                marketplace="coupang",
                keyword="k",
                action="상품명 변경",
                reason="ok",
                category="title",
                outcome="success",
                recommendation_id=f"r{i}",
                context=ctx,
                metrics_before={"ctr": 0.02},
                metrics_after={"ctr": 0.028},
            )
        mem.record_ab_winner("r0", winner="A", metric="CTR", lift_a=10, lift_b=3)
        evidence, avg = mem.evidence_for("title", ctx)
        self.assertIn("성공", evidence)
        similar = mem.find_similar_successes(action_category="title", context=ctx)
        self.assertTrue(any(e.get("abWinner") == "A" for e in similar))


class TestVerificationAB(unittest.TestCase):
    def test_ab_compare_updates_memory(self):
        tmp = Path(tempfile.mkdtemp())
        mem = CommerceMemory(tmp / "m.jsonl")
        mem.record(
            product_id="p1",
            marketplace="coupang",
            keyword="k",
            action="상품명 변경",
            reason="r",
            category="title",
            recommendation_id="rid1",
            outcome="pending",
        )
        ver = VerificationEngine(tmp / "v.jsonl", memory=mem)
        ver.open_case(
            recommendation_id="rid1",
            action="상품명 변경",
            product_id="p1",
            baseline={"ctr": 0.02},
        )
        out = ver.record_ab_result(
            "rid1", metric="CTR", value_a=0.03, value_b=0.022
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out["winner"], "A")


if __name__ == "__main__":
    unittest.main()
