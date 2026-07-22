# -*- coding: utf-8 -*-
"""STIX AI - Coupang SEO Recovery Engine v3.0 data models.

Marketplace-agnostic: collectors fill CollectionBundle;
Analyzer / Learning / Dashboard are shared across Coupang, SmartStore, etc.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ProductSnapshot:
    """Normalized product payload from any collector / marketplace."""

    title: str = ""
    brand: str = ""
    price: int | None = None
    review_count: int | None = None
    rating: float | None = None
    image_urls: list[str] = field(default_factory=list)
    detail_text: str = ""
    detail_bullets: list[str] = field(default_factory=list)
    reviews: list[str] = field(default_factory=list)
    url: str = ""
    product_id: str = ""
    rank: int | None = None
    category: str = ""
    option_names: list[str] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)
    image_notes: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CollectionBundle:
    """Collector output — Mode A / B / Hybrid must produce this."""

    keyword: str
    mine: ProductSnapshot
    competitors: list[ProductSnapshot] = field(default_factory=list)
    source: str = "manual"  # cdp | manual | hybrid
    marketplace: str = "coupang"
    collected_at: str = ""
    fallback_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "mine": self.mine.to_dict(),
            "competitors": [c.to_dict() for c in self.competitors],
            "source": self.source,
            "marketplace": self.marketplace,
            "collected_at": self.collected_at,
            "fallback_note": self.fallback_note,
        }


@dataclass
class GapItem:
    keyword: str
    importance: str
    frequency: int
    in_competitors: int
    in_mine: bool
    note: str = ""


@dataclass
class TitleVariant:
    title: str
    seo_score: float
    ctr_score: float
    cvr_score: float
    expected_impressions: float
    expected_purchase_rate: float
    composite: float
    reasons: list[str] = field(default_factory=list)
    exposure_score: float = 0.0


@dataclass
class ReviewInsight:
    advantages: list[str] = field(default_factory=list)
    complaints: list[str] = field(default_factory=list)
    emotions: list[str] = field(default_factory=list)
    purchase_reasons: list[str] = field(default_factory=list)
    repurchase_reasons: list[str] = field(default_factory=list)
    gift_mentions: list[str] = field(default_factory=list)
    usage_places: list[str] = field(default_factory=list)
    return_reasons: list[str] = field(default_factory=list)
    raw_themes: dict[str, int] = field(default_factory=dict)


@dataclass
class ScoreBreakdown:
    total: int
    title: int = 0
    keywords: int = 0
    detail: int = 0
    image: int = 0
    reviews: int = 0
    attributes: int = 0
    category: int = 0
    options: int = 0
    brand: int = 0
    details: dict[str, str] = field(default_factory=dict)


@dataclass
class ImageInsight:
    competitor_patterns: list[str] = field(default_factory=list)
    mine_gaps: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)


@dataclass
class GoldenKeyword:
    keyword: str
    stars: str
    tier: str
    score: float
    reason: str = ""
    search_volume: str = ""  # 높음/중간/낮음
    competition: str = ""  # 높음/중간/낮음
    effect: str = ""
    ctr_delta_pct: float | None = None
    cvr_delta_pct: float | None = None
    rank_delta: int | None = None


@dataclass
class DashboardItem:
    product_id: str
    title: str
    seo_score: int | None
    rank: int | None
    rank_delta: int | None  # negative = improved
    ctr: float | None
    cvr: float | None
    risk: str  # critical | high | medium | low
    recovery_hint: str = ""
    marketplace: str = "coupang"


@dataclass
class RecoveryResult:
    """Full v3 recovery payload for report + history + learning + dashboard."""

    seo_score: int
    score_breakdown: ScoreBreakdown
    keyword_coverage: int
    golden_keywords: list[GoldenKeyword]
    missing_keywords: list[str]
    unused_keywords: list[str]
    delete_candidates: list[str]
    duplicate_keywords: list[str]
    gaps: list[GapItem]
    title_options: list[TitleVariant]
    recommended_title: TitleVariant | None
    headline_copy: str
    detail_page_full: str
    selling_points: list[str]
    detail_structure: list[str]
    ctr_tips: list[str]
    conversion_tips: list[str]
    dwell_tips: list[str]
    image_insight: ImageInsight
    review_insight: ReviewInsight
    checklist: dict[str, str]
    expected_effect: str
    rank_recovery_outlook: str
    keyword_scores: dict[str, float] = field(default_factory=dict)
    ab_test_summary: list[str] = field(default_factory=list)
    recommendation_reasons: list[str] = field(default_factory=list)
    competitor_summaries: list[str] = field(default_factory=list)
    history_path: str = ""
    learning_path: str = ""
    learning_notes: list[str] = field(default_factory=list)
    memory_notes: list[str] = field(default_factory=list)
    trend_alerts: list[str] = field(default_factory=list)

    def to_history_record(
        self,
        *,
        date: str,
        title: str,
        changes: list[str],
        rank_before: int | None = None,
        rank_after: int | None = None,
        product_id: str = "",
        keyword: str = "",
        ctr: float | None = None,
        cvr: float | None = None,
        added_keywords: list[str] | None = None,
        removed_keywords: list[str] | None = None,
        change_reason: str = "",
        marketplace: str = "coupang",
    ) -> dict[str, Any]:
        return {
            "date": date,
            "productId": product_id,
            "keyword": keyword,
            "title": title,
            "seoScore": self.seo_score,
            "keywordCoverage": self.keyword_coverage,
            "rankBefore": rank_before,
            "rankAfter": rank_after,
            "addedKeywords": added_keywords or self.missing_keywords[:20],
            "removedKeywords": removed_keywords or self.delete_candidates[:15],
            "CTR": ctr,
            "CVR": cvr,
            "changes": changes,
            "changeReason": change_reason
            or ("; ".join(changes[:3]) if changes else "SEO recovery suggestion"),
            "marketplace": marketplace,
        }
