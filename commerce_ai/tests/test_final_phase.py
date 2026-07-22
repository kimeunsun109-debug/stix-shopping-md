# -*- coding: utf-8 -*-
"""Final-phase quality tests — jsonl cache, API, autonomous skip_batch."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


class TestJsonlUtil(unittest.TestCase):
    def test_read_cache_and_invalidate_on_append(self):
        from commerce_ai.jsonl_util import (
            append_jsonl,
            clear_all_caches,
            read_jsonl,
        )

        clear_all_caches()
        path = Path(tempfile.mkdtemp()) / "t.jsonl"
        append_jsonl(path, {"a": 1})
        a = read_jsonl(path)
        self.assertEqual(len(a), 1)
        b = read_jsonl(path)
        self.assertIs(a, b)  # cache hit same list object
        append_jsonl(path, {"a": 2})
        c = read_jsonl(path)
        self.assertEqual(len(c), 2)

    def test_skip_corrupt_lines(self):
        from commerce_ai.jsonl_util import clear_all_caches, read_jsonl

        clear_all_caches()
        path = Path(tempfile.mkdtemp()) / "bad.jsonl"
        path.write_text('{"ok":1}\nNOTJSON\n{"ok":2}\n', encoding="utf-8")
        rows = read_jsonl(path)
        self.assertEqual([r["ok"] for r in rows], [1, 2])


class TestMemorySinglePass(unittest.TestCase):
    def test_confidence_uses_entries_once(self):
        from commerce_ai.confidence import ConfidenceEngine
        from commerce_ai.memory import CommerceMemory
        from commerce_ai.models import KnowledgeContext

        path = Path(tempfile.mkdtemp()) / "m.jsonl"
        mem = CommerceMemory(path=path)
        for i in range(5):
            mem.record(
                product_id=f"p{i}",
                marketplace="coupang",
                keyword="십자수",
                action="상품명 개선",
                reason="test",
                category="title",
                outcome="success",
                metrics_before={"ctr": 0.02},
                metrics_after={"ctr": 0.03},
            )
        eng = ConfidenceEngine(mem)
        conf, unc, evid, risk = eng.score(
            "title",
            has_metrics=True,
            context=KnowledgeContext(marketplace="coupang", season="summer"),
        )
        self.assertGreaterEqual(conf, 35)
        self.assertTrue(evid)
        self.assertTrue(risk)


class TestApiSmoke(unittest.TestCase):
    def test_health_and_md_routes(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("fastapi not installed")
        from commerce_ai.api import create_app

        app = create_app()
        client = TestClient(app)
        r = client.get("/health")
        self.assertEqual(r.status_code, 200)
        r2 = client.get("/md")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("text/html", r2.headers.get("content-type", ""))


class TestAutonomousSkipBatch(unittest.TestCase):
    def test_skip_batch_returns_board(self):
        from commerce_ai.autonomous import run_autonomous_daily

        result = run_autonomous_daily(batch_limit=5, skip_batch=True)
        self.assertEqual(result.get("version"), "7.0")
        self.assertIn("board", result)
        self.assertIn("urgent", result["board"])


class TestClearRuntimeCaches(unittest.TestCase):
    def test_clear_runtime_caches(self):
        from commerce_ai.cache import CACHE, clear_runtime_caches
        from commerce_ai.jsonl_util import clear_all_caches

        CACHE.set("t", "k", {"x": 1}, ttl_sec=60)
        clear_runtime_caches()
        self.assertIsNone(CACHE.get("t", "k"))
        clear_all_caches()


if __name__ == "__main__":
    unittest.main()
