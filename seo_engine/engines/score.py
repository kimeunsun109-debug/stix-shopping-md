# -*- coding: utf-8 -*-
"""SEO Score Engine — 100-point weighted score across 9 dimensions."""
from __future__ import annotations

from seo_engine.engines.gap import GapReport
from seo_engine.engines.keyword_extractor import ExtractedKeyword
from seo_engine.keywords import extract_tokens
from seo_engine.models import CollectionBundle, ScoreBreakdown


class SeoScoreEngine:
    # weights sum to 100
    WEIGHTS = {
        "title": 20,
        "keywords": 20,
        "detail": 15,
        "image": 10,
        "reviews": 10,
        "attributes": 5,
        "category": 5,
        "options": 5,
        "brand": 10,
    }

    def score(
        self,
        bundle: CollectionBundle,
        extracted: list[ExtractedKeyword],
        gap: GapReport,
    ) -> ScoreBreakdown:
        mine = bundle.mine
        core = [e for e in extracted if e.coverage_ratio >= 0.4]
        tokens = set(extract_tokens(mine.title + " " + (mine.detail_text or "")))

        # title (0-100 subscore then weight)
        title_s = 40
        if 25 <= len(mine.title) <= 55:
            title_s += 20
        front = mine.title[:15]
        title_s += min(30, sum(10 for e in core[:3] if e.keyword in front))
        if gap.duplicates:
            title_s -= 15
        title_s = max(0, min(100, title_s))

        # keywords
        covered = sum(1 for e in core if e.keyword in tokens)
        kw_s = int(100 * covered / max(len(core), 1)) if core else 50

        # detail
        detail_s = 30
        if mine.detail_text and len(mine.detail_text) > 200:
            detail_s += 30
        if mine.detail_bullets:
            detail_s += 20
        if any(m in (mine.detail_text or "") for m in gap.missing[:5]):
            detail_s += 20
        detail_s = min(100, detail_s)

        # image
        image_s = 40 if mine.image_urls or mine.image_notes else 15
        if len(mine.image_urls) >= 3:
            image_s += 30
        if mine.image_notes:
            image_s += 20
        image_s = min(100, image_s)

        # reviews
        review_s = 20
        if mine.reviews:
            review_s += min(50, len(mine.reviews) * 10)
        if mine.review_count and mine.review_count > 50:
            review_s += 20
        if mine.rating and mine.rating >= 4.5:
            review_s += 10
        review_s = min(100, review_s)

        # attributes / category / options / brand
        attr_s = 70 if mine.attributes else 35
        cat_s = 80 if mine.category else 40
        opt_s = 80 if mine.option_names else 40
        brand = mine.brand or ("스팃스" if "스팃스" in mine.title else "")
        brand_s = 90 if brand and brand in mine.title else (50 if brand else 20)

        parts = {
            "title": title_s,
            "keywords": kw_s,
            "detail": detail_s,
            "image": image_s,
            "reviews": review_s,
            "attributes": attr_s,
            "category": cat_s,
            "options": opt_s,
            "brand": brand_s,
        }
        total = int(
            round(sum(parts[k] * self.WEIGHTS[k] / 100 for k in self.WEIGHTS))
        )
        details = {
            k: f"{parts[k]}/100 × 가중치 {self.WEIGHTS[k]}"
            for k in self.WEIGHTS
        }
        return ScoreBreakdown(
            total=total,
            title=int(parts["title"] * self.WEIGHTS["title"] / 100),
            keywords=int(parts["keywords"] * self.WEIGHTS["keywords"] / 100),
            detail=int(parts["detail"] * self.WEIGHTS["detail"] / 100),
            image=int(parts["image"] * self.WEIGHTS["image"] / 100),
            reviews=int(parts["reviews"] * self.WEIGHTS["reviews"] / 100),
            attributes=int(parts["attributes"] * self.WEIGHTS["attributes"] / 100),
            category=int(parts["category"] * self.WEIGHTS["category"] / 100),
            options=int(parts["options"] * self.WEIGHTS["options"] / 100),
            brand=int(parts["brand"] * self.WEIGHTS["brand"] / 100),
            details=details,
        )
