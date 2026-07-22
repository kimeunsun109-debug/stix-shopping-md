# -*- coding: utf-8 -*-
"""CVR Optimizer — hesitation → trust / FAQ / guarantee."""
from __future__ import annotations

from seo_engine.models import CollectionBundle, ReviewInsight


class CvrOptimizer:
    def optimize(
        self, bundle: CollectionBundle, review: ReviewInsight
    ) -> tuple[list[str], dict[str, str]]:
        tips = [
            "초보 난이도·소요시간 FAQ 추가 (구매 망설임 1순위)",
            "구성품 누락 불안 -> 구성 리스트+실 강화",
            "선물 포장/완성 후 액자 옵션 안내",
            "최근 후기 3개를 상단 신뢰 블록에 인용",
            "교환·품질 문의 경로를 FAQ 마지막에 명시",
        ]
        if review.complaints:
            tips.insert(0, f"불만 선대응: '{review.complaints[0]}' 관련 FAQ/보증 문구 추가")
        if review.gift_mentions:
            tips.append("선물 맥락 강조: 포장/카드/완성 사진 가이드")

        checklist = {
            "상품명": "핵심어 전진 배치 / 중복 제거",
            "브랜드": "스팃스 또는 등록 브랜드 포함",
            "카테고리": "쿠팡 카테고리·속성과 키워드 일치",
            "옵션명": "사이즈/구성이 옵션명에도 노출",
            "대표이미지": "검색 썸네일 CTR용 완성컷",
            "상세이미지": "상단 카피+장점+후기 흐름",
            "이미지텍스트": "이미지 안 문구에 핵심 키워드",
            "리뷰": "후기 키워드를 셀링포인트에 반영",
            "보증/FAQ": "난이도·구성·교환 불안 해소",
        }
        return tips, checklist
