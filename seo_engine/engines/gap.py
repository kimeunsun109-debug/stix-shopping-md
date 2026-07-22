# -*- coding: utf-8 -*-
"""SEO Gap Analyzer — missing / duplicate / noise / brand position."""
from __future__ import annotations

from dataclasses import dataclass, field

from seo_engine.engines.competitor import CompetitorAnalyzer
from seo_engine.engines.keyword_extractor import ExtractedKeyword, KeywordExtractor
from seo_engine.keywords import extract_tokens
from seo_engine.models import CollectionBundle, GapItem


@dataclass
class GapReport:
    gaps: list[GapItem] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    delete_candidates: list[str] = field(default_factory=list)
    unused: list[str] = field(default_factory=list)
    brand_position_note: str = ""
    priority_notes: list[str] = field(default_factory=list)
    coverage_pct: int = 0


class SeoGapAnalyzer:
    def __init__(self) -> None:
        self._comp = CompetitorAnalyzer()
        self._kw = KeywordExtractor()

    def analyze(
        self,
        bundle: CollectionBundle,
        extracted: list[ExtractedKeyword] | None = None,
    ) -> GapReport:
        extracted = extracted or self._kw.extract(bundle)
        mine_tokens = self._comp.mine_token_set(bundle.mine)
        title = bundle.mine.title
        mine_title_tokens = list(dict.fromkeys(extract_tokens(title)))

        def _title_count(tok: str) -> int:
            if not tok:
                return 0
            if tok.isascii():
                return title.lower().count(tok.lower())
            return title.count(tok)

        n = max(len(bundle.competitors), 1)
        gaps: list[GapItem] = []
        missing: list[str] = []
        core = [e for e in extracted if e.coverage_ratio >= 0.4]

        for e in extracted[:50]:
            in_mine = e.keyword in mine_tokens or e.keyword.lower() in bundle.mine.title.lower()
            if not in_mine and e.coverage_ratio >= 0.4:
                missing.append(e.keyword)
            note = ""
            if e.coverage_ratio >= 0.7 and not in_mine:
                note = "검색 우선순위 높음 - 상품명 전반부 배치 권장"
            gaps.append(
                GapItem(
                    keyword=e.keyword,
                    importance=e.importance,
                    frequency=e.frequency,
                    in_competitors=e.frequency,
                    in_mine=in_mine,
                    note=note,
                )
            )

        duplicates = [t for t in mine_title_tokens if _title_count(t) >= 2]

        delete: list[str] = []
        comp_freq = {e.keyword: e.frequency for e in extracted}
        for t in mine_title_tokens:
            if comp_freq.get(t, 0) == 0 and t not in {"스팃스", "STIX"} and len(t) >= 2:
                if not __import__("re").match(r"\d{2}x\d{2}", t.lower()):
                    delete.append(t)
        delete = list(dict.fromkeys(delete))[:15]

        unused = [e.keyword for e in core if e.keyword not in mine_tokens][:20]

        covered = sum(
            1
            for e in core
            if e.keyword in mine_tokens or e.keyword.lower() in bundle.mine.title.lower()
        )
        coverage = int(round(100 * covered / max(len(core), 1)))

        brand = bundle.mine.brand or ("스팃스" if "스팃스" in bundle.mine.title else "")
        brand_note = "브랜드 미확인"
        if brand:
            pos = bundle.mine.title.find(brand)
            if pos < 0:
                brand_note = f"브랜드 '{brand}' 상품명 미포함 - 자연스럽게 중후반 배치 권장"
            elif pos < 15:
                brand_note = f"브랜드 '{brand}'가 앞쪽({pos}) - 핵심어보다 앞에 있으면 검색 효율 저하 가능"
            else:
                brand_note = f"브랜드 '{brand}' 위치 {pos}자 - 핵심어 후 배치로 양호"

        priority = []
        for m in missing[:5]:
            priority.append(f"[우선] '{m}' 누락 - 상품명/옵션/상세 상단에 추가")
        if duplicates:
            priority.append(f"[정리] 상품명 중복 토큰: {', '.join(duplicates)}")

        return GapReport(
            gaps=gaps[:40],
            missing=missing[:30],
            duplicates=duplicates,
            delete_candidates=delete,
            unused=unused,
            brand_position_note=brand_note,
            priority_notes=priority,
            coverage_pct=coverage,
        )
