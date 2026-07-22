# -*- coding: utf-8 -*-
"""Image Analyzer — competitor thumbnail patterns vs mine (heuristic + notes)."""
from __future__ import annotations

from seo_engine.models import CollectionBundle, ImageInsight


class ImageAnalyzer:
    """
    Without ML vision API, uses:
      - image URL / count signals
      - image_notes (Mode B free text)
      - competitor title cues (액자형, 완성, 키트 등)
    Extensible: swap in vision model later without changing pipeline.
    """

    def analyze(self, bundle: CollectionBundle) -> ImageInsight:
        comps = bundle.competitors[:5]
        patterns: list[str] = []
        with_img = sum(1 for c in comps if c.image_urls)
        patterns.append(f"상위 {len(comps)}개 중 대표이미지 URL 확보 {with_img}건")

        cue_titles = " ".join(c.title for c in comps)
        if "액자" in cue_titles:
            patterns.append("경쟁: 액자/완성본 강조 썸네일 비중 높음")
        if "키트" in cue_titles or "구성" in cue_titles:
            patterns.append("경쟁: 키트 구성품이 한 장에 보이는 구도 추정")
        if any("손" in (c.image_notes or "") or "hand" in (c.image_notes or "").lower() for c in comps):
            patterns.append("경쟁: 손 등장 컷 사용")

        multi = sum(1 for c in comps if len(c.image_urls) >= 3)
        if multi:
            patterns.append(f"경쟁 {multi}개: 상세/추가 이미지 3장+")

        mine_gaps: list[str] = []
        improvements: list[str] = []
        if not bundle.mine.image_urls and not bundle.mine.image_notes:
            mine_gaps.append("내 대표이미지 정보 없음 (URL 또는 image_notes 입력 권장)")
            improvements.append("완성본 클로즈업 + 키트 풀셋을 좌우 배치한 대표컷 제작")
        else:
            improvements.append("배경: 밝은 단색/나무톤으로 제품 대비 확보")
            improvements.append("구도: 제품 확대 비율 60%+, 여백에 짧은 텍스트(초보/구성) 1줄")
            improvements.append("텍스트 길이: 썸네일에서 읽히는 4~8자 이내")
            improvements.append("손 등장: 1장 포함 시 실사용 신뢰↑ (과다 사용 금지)")
            improvements.append("색감: 채도 과한 네온 지양, 완성 작품 색이 돋보이게")

        notes = (bundle.mine.image_notes or "").lower()
        if notes:
            if "어두" in notes or "dark" in notes:
                mine_gaps.append("내 이미지 노트: 어두운 배경")
                improvements.insert(0, "배경을 밝게 바꿔 CTR 개선")
            if "텍스트" in notes and ("많" in notes or "길" in notes):
                mine_gaps.append("이미지 텍스트 과다")
                improvements.insert(0, "텍스트 길이 축소 (핵심 키워드 1개만)")

        if not improvements:
            improvements = [
                "완성본+키트 동시 노출",
                "밝은 배경 + 제품 확대",
                "짧은 혜택 텍스트 1줄",
            ]

        return ImageInsight(
            competitor_patterns=patterns or ["경쟁 이미지 패턴 데이터 부족"],
            mine_gaps=mine_gaps or ["치명적 이미지 갭 없음 (추가 실측 권장)"],
            improvements=improvements[:8],
        )
