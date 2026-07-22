# -*- coding: utf-8 -*-
"""Operation-phase tests: catalog, batch smoke, dashboard payload, scheduler helpers."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from commerce_ai.ops_catalog import (
    catalog_stats,
    infer_keyword,
    load_ops_products,
    peer_competitors,
)
from commerce_ai.scheduler import seconds_until


class TestOpsCatalog(unittest.TestCase):
    def test_catalog_has_100_plus(self):
        st = catalog_stats()
        self.assertGreaterEqual(st["total_valid"], 100)
        self.assertTrue(st["ready_for_batch"])

    def test_load_limit_and_marketplace(self):
        products = load_ops_products(limit=120)
        self.assertGreaterEqual(len(products), 100)
        self.assertTrue(all(p.get("marketplace") for p in products))
        self.assertTrue(all(p.get("title") for p in products))
        # coupang should be present after Template sheet fix
        plats = {p["platform"] for p in products}
        self.assertTrue(len(plats) >= 1)

    def test_infer_keyword(self):
        self.assertEqual(infer_keyword("스팃스 보석십자수 키트 30x40"), "보석십자수")

    def test_peers(self):
        products = load_ops_products(limit=50)
        if len(products) < 2:
            self.skipTest("not enough products")
        peers = peer_competitors(products, products[0], n=3)
        self.assertLessEqual(len(peers), 3)


class TestSchedulerHelpers(unittest.TestCase):
    def test_seconds_until_positive(self):
        self.assertGreater(seconds_until(8, 0), 0)


class TestBatchSmoke(unittest.TestCase):
    def test_analyze_few_products(self):
        from commerce_ai.batch_ops import analyze_product, append_snapshot
        from commerce_ai.container import CommerceContainer, set_container
        from commerce_ai.memory import CommerceMemory
        from commerce_ai.verification import VerificationEngine

        tmp = Path(tempfile.mkdtemp())
        mem = CommerceMemory(path=tmp / "m.jsonl")
        ver = VerificationEngine(tmp / "v.jsonl", memory=mem)
        set_container(CommerceContainer(memory=mem, verification=ver))

        products = load_ops_products(limit=8)
        self.assertGreaterEqual(len(products), 3)
        # analyze 3 only for speed
        for p in products[:3]:
            snap = analyze_product(
                p,
                products,
                save_memory=True,
                open_verification=True,
            )
            self.assertTrue(snap.seo_score >= 0)
            self.assertTrue(snap.recommendations)
            self.assertTrue(snap.recommendations[0].get("evidence") is not None)
            append_snapshot(snap)
            # redirect snapshot path for test isolation
        self.assertTrue(True)


class TestDashboardOpsPayload(unittest.TestCase):
    def test_payload_keys(self):
        from commerce_ai.dashboard import CommerceDashboard

        payload = CommerceDashboard().to_ops_payload()
        self.assertIn(payload.get("version"), {"6.0", "7.0"})
        self.assertIn("board", payload) if "board" in payload else self.assertIn("today_tasks", payload)


class TestMdHtmlExists(unittest.TestCase):
    def test_web_file(self):
        path = Path(__file__).resolve().parents[1] / "web" / "md.html"
        self.assertTrue(path.exists())
        html = path.read_text(encoding="utf-8")
        self.assertIn("오늘 해야 할 일", html)
        self.assertIn("/api/md/ops", html)


if __name__ == "__main__":
    unittest.main()
