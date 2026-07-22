# -*- coding: utf-8 -*-
"""Competitor Analyzer — TOP1~5 structure & keyword frequency."""
from __future__ import annotations

from dataclasses import dataclass, field

from seo_engine.keywords import extract_tokens, token_counter
from seo_engine.models import CollectionBundle, ProductSnapshot


@dataclass
class CompetitorReport:
    top_n: int
    titles: list[str] = field(default_factory=list)
    brands: list[str] = field(default_factory=list)
    avg_price: float | None = None
    avg_rating: float | None = None
    avg_reviews: float | None = None
    keyword_freq: dict[str, int] = field(default_factory=dict)
    repeating_keywords: list[tuple[str, int]] = field(default_factory=list)
    image_count: int = 0
    summaries: list[str] = field(default_factory=list)


class CompetitorAnalyzer:
    def analyze(self, bundle: CollectionBundle, top_n: int = 5) -> CompetitorReport:
        comps = bundle.competitors[:top_n]
        titles = [c.title for c in comps if c.title]
        brands = [c.brand for c in comps if c.brand]
        prices = [c.price for c in comps if c.price]
        ratings = [c.rating for c in comps if c.rating]
        reviews = [c.review_count for c in comps if c.review_count]
        texts = titles + [(c.detail_text or "")[:1200] for c in comps]
        freq = token_counter(texts)
        repeating = [(k, v) for k, v in freq.most_common(40) if v >= max(2, len(comps) // 2 or 1)]
        image_count = sum(1 for c in comps if c.image_urls)
        summaries = []
        for c in comps:
            summaries.append(
                f"#{c.rank or '-'} {c.title[:60]} | "
                f"{c.price or '-'}원 | ★{c.rating or '-'} | 리뷰 {c.review_count or '-'} | "
                f"이미지 {len(c.image_urls)}"
            )
        return CompetitorReport(
            top_n=len(comps),
            titles=titles,
            brands=brands,
            avg_price=(sum(prices) / len(prices)) if prices else None,
            avg_rating=(sum(ratings) / len(ratings)) if ratings else None,
            avg_reviews=(sum(reviews) / len(reviews)) if reviews else None,
            keyword_freq=dict(freq.most_common(50)),
            repeating_keywords=repeating,
            image_count=image_count,
            summaries=summaries,
        )

    def mine_token_set(self, mine: ProductSnapshot) -> set[str]:
        blob = " ".join(
            [
                mine.title,
                mine.brand,
                mine.detail_text or "",
                " ".join(mine.detail_bullets),
                " ".join(mine.option_names),
                mine.category,
            ]
        )
        return set(extract_tokens(blob))
