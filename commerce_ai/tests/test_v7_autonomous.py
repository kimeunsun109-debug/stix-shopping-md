# -*- coding: utf-8 -*-
"""v7 AI MD autonomous operation tests."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from commerce_ai.knowledge import KnowledgeEvolution
from commerce_ai.memory import CommerceMemory
from commerce_ai.models import KnowledgeContext
from commerce_ai.opportunity import OpportunityEngine
from commerce_ai.priority import PriorityEngine
from commerce_ai.reports import ReportEngine
from commerce_ai.self_eval import SelfEvaluationEngine


class TestOpportunityPriority(unittest.TestCase):
    def test_detect_and_rank(self):
        snaps = [
            {
                "product_id": "p1",
                "title": "DIY 보석십자수 여름 집콕 키트",
                "seo_score": 40,
                "revenue_score": 70,
                "golden_keywords": ["DIY", "집콕", "액자"],
                "image_tips": ["밝은 배경"],
                "stock": 3,
                "recommendations": [
                    {
                        "must_do_today": True,
                        "action": "상품명 변경",
                        "category": "title",
                        "reason": "키워드",
                        "expected_effect": "CTR +8%",
                        "confidence": 88,
                        "evidence": "최근 10건",
                        "lift_pct": 8,
                        "revenue_lift_pct": 7,
                        "expected_impact": {"CTR": 8},
                    }
                ],
                "competitor_notes": ["경쟁사 품절 감지"],
            }
        ]
        opps = OpportunityEngine().detect(snaps)
        self.assertTrue(len(opps) >= 2)
        tasks = PriorityEngine().rank(opps, verify_due=[{"dueDays": 7, "action": "상품명 변경", "product_id": "p1"}])
        self.assertTrue(tasks)
        self.assertTrue(any(t.lane in {"urgent", "high", "verify"} for t in tasks))
        self.assertTrue(all(t.roi_score >= 0 for t in tasks))


class TestKnowledgeAndSelfEval(unittest.TestCase):
    def test_patterns_and_eval(self):
        path = Path(tempfile.mkdtemp()) / "m.jsonl"
        mem = CommerceMemory(path)
        for i in range(4):
            mem.record(
                product_id=f"p{i}",
                marketplace="coupang",
                keyword="DIY",
                action="상품명 변경",
                reason="DIY 전반부",
                category="title",
                outcome="success",
                context=KnowledgeContext(
                    marketplace="coupang", season="summer", price_band="10k_30k"
                ),
                metrics_before={"ctr": 0.02},
                metrics_after={"ctr": 0.025},
            )
        patterns = KnowledgeEvolution(path).discover(min_n=3)
        self.assertTrue(len(patterns) >= 1)
        lessons = KnowledgeEvolution(path).lessons_text()
        self.assertTrue(lessons)


class TestDailyReport(unittest.TestCase):
    def test_daily_report_text(self):
        from commerce_ai.batch_ops import load_recent_snapshots

        snaps = load_recent_snapshots(50)
        if len(snaps) < 3:
            snaps = [
                {
                    "date": "2026-07-17",
                    "product_id": "x",
                    "title": "테스트 DIY",
                    "seo_score": 45,
                    "revenue_score": 60,
                    "golden_keywords": ["DIY"],
                    "recommendations": [],
                    "image_tips": [],
                    "competitor_notes": [],
                }
            ]
        r = ReportEngine().build_daily(snapshots=snaps, save=False)
        self.assertIn("AI MD Daily Report", r.text)
        self.assertIn("오늘 가장 중요한 작업", r.text)
        self.assertGreaterEqual(r.analyzed_catalog, 0)


class TestAutonomousBoard(unittest.TestCase):
    def test_today_board(self):
        from commerce_ai.autonomous import today_board

        result = today_board()
        self.assertEqual(result.get("version"), "7.0")
        self.assertIn("board", result)
        self.assertIn("daily_report_text", result)
        self.assertIn("urgent", result["board"])


class TestDashboardV7(unittest.TestCase):
    def test_ops_has_board(self):
        from commerce_ai.dashboard import CommerceDashboard

        payload = CommerceDashboard().to_ops_payload()
        self.assertEqual(payload.get("version"), "7.0")
        self.assertIn("board", payload)
        self.assertIn("daily_report", payload)
        self.assertIn("self_evaluation", payload)


if __name__ == "__main__":
    unittest.main()
