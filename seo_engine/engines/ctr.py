# -*- coding: utf-8 -*-
"""CTR Optimizer — thumbnail, first line, first screen."""
from __future__ import annotations

from seo_engine.engines.keyword_extractor import ExtractedKeyword
from seo_engine.models import CollectionBundle


class CtrOptimizer:
    def optimize(
        self,
        bundle: CollectionBundle,
        extracted: list[ExtractedKeyword],
    ) -> tuple[list[str], list[str]]:
        core = [e.keyword for e in extracted[:5]]
        ctr = [
            "대표이미지: 완성본+키트 구성이 한 장에 보이게 (검색 썸네일 대비 강화)",
            f"상품명 앞 15자 안에 핵심어 배치 예: {' '.join(core[:3]) or bundle.keyword}",
            "검색 카드용 첫 문장에 후기 키워드(쉬움/선물/예쁨) 1개 삽입",
            "배경 노이즈 줄이고 제품 대비 강화 (단색/밝은 배경 우선)",
            "첫 화면(모바일): 문제 한 줄 + 핵심 장점 2개 + 후기 한 줄만",
        ]
        dwell = [
            "스토리: 고민 -> 선택 이유 -> 만드는 과정 -> 완성 장면 -> 후기",
            "스크롤마다 '지금 어디까지 왔는지' 미니 헤더",
            "중간 CTA는 사용방법 직전/직후 1회만 (과다 CTA는 이탈)",
            "실사용 사진 3장 이상: 손 등장 컷 1장 포함 시 신뢰↑",
        ]
        return ctr, dwell
