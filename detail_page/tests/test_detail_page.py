# -*- coding: utf-8 -*-
import unittest

import numpy as np
from PIL import Image

from detail_page.catalog import CATEGORY_NOTICE, PRODUCTS
from detail_page.render import render_html, split_panels


class CatalogTests(unittest.TestCase):
    def test_keys_unique_and_not_ambiguous(self):
        keys = [p.key for p in PRODUCTS]
        self.assertEqual(len(keys), len(set(keys)))
        for a in keys:
            for b in keys:
                if a != b:
                    self.assertFalse(b.startswith(a), f"{a} 가 {b} 의 접두사라 파일 매칭이 모호합니다")

    def test_required_fields(self):
        for p in PRODUCTS:
            self.assertTrue(p.name and p.eng and p.lead, p.key)
            self.assertEqual(len(p.points), 3, p.key)
            self.assertEqual(len(p.feats), 3, p.key)
            self.assertTrue(p.specs, p.key)
            self.assertIn(p.cat, CATEGORY_NOTICE, p.key)
            self.assertNotIn("\ufffd", p.name + p.lead + p.qa, p.key)


class RenderTests(unittest.TestCase):
    def test_split_panels_finds_gutter(self):
        a = np.full((1024, 1024, 3), 255, np.uint8)
        rng = np.random.default_rng(0)
        for (y, x) in [(0, 0), (0, 520), (520, 0), (520, 520)]:
            a[y:y + 504, x:x + 504] = rng.integers(0, 255, (504, 504, 3))
        panels = split_panels(Image.fromarray(a))
        self.assertEqual(len(panels), 4)
        for p in panels:
            self.assertGreater(np.asarray(p).std(), 40)  # 흰 여백이 섞여 들어오지 않아야 함

    def test_render_html_has_six_sections(self):
        imgs = {k: f"../images/x_{k}.jpg" for k in ("main", "why", "use1", "use2")}
        out = render_html(PRODUCTS[0], imgs, "x", with_tools=False)
        for i in range(1, 7):
            self.assertIn(f'id="sec-0{i}"', out)
        self.assertNotIn("html2canvas", out)


if __name__ == "__main__":
    unittest.main()
