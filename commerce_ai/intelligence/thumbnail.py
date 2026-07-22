# -*- coding: utf-8 -*-
"""Thumbnail Intelligence — heuristic analyzer with Vision API swap point."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from seo_engine.models import CollectionBundle, ImageInsight


@dataclass
class ThumbnailAnalysis:
    background: str = ""
    color: str = ""
    text_density: str = ""
    ocr_guess: str = ""
    hand_present: bool = False
    product_zoom: str = ""
    composition: str = ""
    whitespace: str = ""
    attention: str = ""
    improvements: list[str] = field(default_factory=list)
    competitor_patterns: list[str] = field(default_factory=list)
    provider: str = "heuristic"


class ThumbnailProvider(ABC):
    """Swap HeuristicThumbnailProvider -> VisionApiThumbnailProvider later."""

    @abstractmethod
    def analyze(self, bundle: CollectionBundle) -> ThumbnailAnalysis:
        raise NotImplementedError


class HeuristicThumbnailProvider(ThumbnailProvider):
    def analyze(self, bundle: CollectionBundle) -> ThumbnailAnalysis:
        notes = (bundle.mine.image_notes or "").lower()
        patterns: list[str] = []
        for c in bundle.competitors[:5]:
            cn = (c.image_notes or "").lower()
            if "밝" in cn or "bright" in cn:
                patterns.append("경쟁: 밝은 배경")
            if "손" in cn or "hand" in cn:
                patterns.append("경쟁: 손 등장")
            if "완성" in c.title or "액자" in c.title:
                patterns.append("경쟁: 완성본/액자 강조 추정")
            if "키트" in c.title:
                patterns.append("경쟁: 키트 구성 노출 추정")
        patterns = list(dict.fromkeys(patterns)) or ["경쟁 이미지 패턴 데이터 부족"]

        bg = "어두움" if ("어두" in notes or "dark" in notes) else (
            "밝음" if ("밝" in notes or "bright" in notes) else "미상"
        )
        text = "과다" if ("텍스트" in notes and ("많" in notes or "길" in notes)) else (
            "적절" if "텍스트" in notes else "미상"
        )
        hand = "손" in notes or "hand" in notes
        zoom = "확대" if ("확대" in notes or "클로즈" in notes) else "보통/미상"
        color = "고채도" if ("채도" in notes or "네온" in notes) else "중립/미상"
        comp = "제품+구성" if ("구성" in notes or "키트" in notes) else "단일제품/미상"
        space = "부족" if ("가득" in notes or "빽빽" in notes) else "보통"
        attention = "분산" if text == "과다" else ("집중" if bg == "밝음" else "보통")

        improvements: list[str] = []
        if bg == "어두움":
            improvements.append("배경을 밝은 단색/나무톤으로 변경 → 시선 집중도↑")
        if text == "과다":
            improvements.append("OCR 가독: 썸네일 텍스트 4~8자로 축소 (핵심어 1개)")
        if not hand:
            improvements.append("손 등장 컷 1장 추가 → 실사용 신뢰·CTR↑")
        if zoom != "확대":
            improvements.append("제품 확대 비율 60%+ 구도로 재촬영")
        improvements.append("완성본 + 키트 풀셋 좌우 배치로 검색 카드 대비 강화")
        improvements.append("여백을 확보해 시선이 제품 중심으로 모이게")

        return ThumbnailAnalysis(
            background=bg,
            color=color,
            text_density=text,
            ocr_guess="(휴리스틱 — Vision OCR 미연결)",
            hand_present=hand,
            product_zoom=zoom,
            composition=comp,
            whitespace=space,
            attention=attention,
            improvements=improvements[:8],
            competitor_patterns=patterns,
            provider="heuristic",
        )


class VisionApiThumbnailProvider(ThumbnailProvider):
    """Placeholder — replace analyze() body with Vision API calls."""

    def __init__(self, api_client=None) -> None:
        self.api_client = api_client

    def analyze(self, bundle: CollectionBundle) -> ThumbnailAnalysis:
        # Fallback until API wired
        base = HeuristicThumbnailProvider().analyze(bundle)
        base.provider = "vision_api_pending"
        base.ocr_guess = "(Vision API 연결 시 OCR 결과 삽입)"
        return base


class ThumbnailIntelligence:
    def __init__(self, provider: ThumbnailProvider | None = None) -> None:
        self.provider = provider or HeuristicThumbnailProvider()

    def analyze(self, bundle: CollectionBundle) -> ThumbnailAnalysis:
        return self.provider.analyze(bundle)

    def to_image_insight(self, analysis: ThumbnailAnalysis) -> ImageInsight:
        return ImageInsight(
            competitor_patterns=analysis.competitor_patterns,
            mine_gaps=[
                f"배경:{analysis.background}",
                f"텍스트:{analysis.text_density}",
                f"손:{'있음' if analysis.hand_present else '없음'}",
                f"확대:{analysis.product_zoom}",
                f"시선:{analysis.attention}",
            ],
            improvements=analysis.improvements,
        )
