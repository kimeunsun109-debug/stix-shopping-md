# -*- coding: utf-8 -*-
"""Keyword Engine v3 — volume / competition / importance / effect."""
from __future__ import annotations

from dataclasses import dataclass

from seo_engine.engines.competitor import CompetitorAnalyzer, CompetitorReport
from seo_engine.keywords import importance_stars
from seo_engine.models import CollectionBundle


@dataclass
class ExtractedKeyword:
    keyword: str
    frequency: int
    coverage_ratio: float
    importance: str
    search_volume: str = "중간"  # 높음/중간/낮음 (proxy)
    competition: str = "중간"
    effect: float = 0.0  # 0~100 learned + coverage blend


def _volume_label(ratio: float, freq: int) -> str:
    if ratio >= 0.7 or freq >= 4:
        return "높음"
    if ratio >= 0.4 or freq >= 2:
        return "중간"
    return "낮음"


def _competition_label(ratio: float) -> str:
    if ratio >= 0.8:
        return "높음"
    if ratio >= 0.4:
        return "중간"
    return "낮음"


class KeywordExtractor:
    def __init__(self) -> None:
        self._comp = CompetitorAnalyzer()

    def extract(
        self, bundle: CollectionBundle, comp: CompetitorReport | None = None
    ) -> list[ExtractedKeyword]:
        report = comp or self._comp.analyze(bundle)
        n = max(report.top_n, 1)
        cat = bundle.mine.category or bundle.keyword or "default"
        # lazy import to avoid circular dependency with golden
        from seo_engine.engines.golden import GoldenKeywordEngine

        learned = GoldenKeywordEngine().load().get("categories", {}).get(cat, {})

        out: list[ExtractedKeyword] = []
        for kw, freq in report.keyword_freq.items():
            ratio = freq / n
            if ratio < 0.2 and freq < 2:
                continue
            entry = learned.get(kw, {})
            success = float(entry.get("success_score", 0))
            ctr_d = float(entry.get("ctr_delta_pct", 0) or 0)
            cvr_d = float(entry.get("cvr_delta_pct", 0) or 0)
            rank_d = float(entry.get("rank_delta_sum", 0) or 0)
            effect = min(
                100.0,
                ratio * 50
                + success * 8
                + max(0, ctr_d) * 0.5
                + max(0, cvr_d) * 0.5
                + max(0, rank_d) * 2,
            )
            out.append(
                ExtractedKeyword(
                    keyword=kw,
                    frequency=freq,
                    coverage_ratio=ratio,
                    importance=importance_stars(freq, n),
                    search_volume=_volume_label(ratio, freq),
                    competition=_competition_label(ratio),
                    effect=round(effect, 1),
                )
            )
        out.sort(key=lambda x: (-x.effect, -x.coverage_ratio, -x.frequency, x.keyword))
        return out