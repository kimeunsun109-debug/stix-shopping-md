# -*- coding: utf-8 -*-
"""Review Analyzer — advantages, complaints, emotions, purchase reasons."""
from __future__ import annotations

from collections import Counter

from seo_engine.models import CollectionBundle, ReviewInsight

_THEME_MAP: list[tuple[str, str, list[str]]] = [
    ("adv", "초보도 쉽게 가능", ["초보", "쉬", "간단", "입문", "처음"]),
    ("adv", "완성 만족감", ["완성", "뿌듯", "성취", "예쁘게"]),
    ("adv", "인테리어 효과", ["인테리어", "예쁘", "장식", "벽", "액자"]),
    ("adv", "선물 추천", ["선물", "생일", "크리스마스", "부모님"]),
    ("adv", "집중력 향상", ["집중", "몰입", "시간 가는"]),
    ("adv", "스트레스 해소", ["스트레스", "힐링", "편안", "안정"]),
    ("adv", "구성품 알참", ["구성", "포함", "충분", "펜", "트레이"]),
    ("adv", "가성비", ["가성비", "저렴", "가격", "괜찮"]),
    ("adv", "아이와 함께", ["아이", "어린이", "자녀", "가족"]),
    ("adv", "집콕 취미", ["집콕", "취미", "심심", "하루"]),
    ("complaint", "난이도 높음", ["어렵", "힘들", "복잡", "오래"]),
    ("complaint", "구성 부족", ["부족", "모자라", "빠져", "누락"]),
    ("complaint", "도안 불만", ["도안이 흐릿", "도안 안", "흐릿", "안 보여"]),
    ("complaint", "배송/포장", ["배송", "파손", "포장"]),
    ("return", "단순변심/반품", ["반품", "환불", "교환", "취소"]),
    ("return", "품질 이슈 반품", ["불량", "하자", "깨짐", "오염"]),
    ("return", "설명과 다름", ["다르", "기대", "사진과"]),
    ("emotion", "만족/기쁨", ["만족", "좋아", "최고", "행복", "감동"]),
    ("emotion", "아쉬움", ["아쉽", "별로", "실망"]),
    ("purchase", "취미 시작", ["취미", "시작", "해보고"]),
    ("purchase", "인테리어 목적", ["인테리어", "꾸미", "벽"]),
    ("purchase", "선물용", ["선물", "드렸", "줬"]),
    ("repurchase", "재구매/추가", ["또 샀", "재구매", "추가", "다른 도안"]),
    ("gift", "선물 맥락", ["선물", "부모님", "친구", "연인"]),
    ("place", "집/거실", ["집", "거실", "방", "책상"]),
    ("place", "카페/매장", ["카페", "매장", "사무실"]),
]


class ReviewAnalyzer:
    def analyze(self, bundle: CollectionBundle) -> ReviewInsight:
        reviews = list(bundle.mine.reviews)
        for c in bundle.competitors:
            reviews.extend(c.reviews[:8])
        blob_list = reviews or [bundle.mine.detail_text or ""]
        blob = " ".join(blob_list)

        buckets: dict[str, list[str]] = {
            "adv": [],
            "complaint": [],
            "return": [],
            "emotion": [],
            "purchase": [],
            "repurchase": [],
            "gift": [],
            "place": [],
        }
        raw: Counter[str] = Counter()
        for kind, label, keys in _THEME_MAP:
            hit = sum(blob.count(k) for k in keys)
            if hit:
                raw[label] = hit
                if label not in buckets[kind]:
                    buckets[kind].append(label)

        # defaults if sparse
        if not buckets["adv"]:
            buckets["adv"] = ["초보도 쉽게 가능", "완성 만족감", "선물 추천"]

        return ReviewInsight(
            advantages=buckets["adv"][:10],
            complaints=buckets["complaint"][:8],
            emotions=buckets["emotion"][:6],
            purchase_reasons=buckets["purchase"][:8],
            repurchase_reasons=buckets["repurchase"][:6],
            gift_mentions=buckets["gift"][:6],
            usage_places=buckets["place"][:6],
            return_reasons=buckets["return"][:6],
            raw_themes=dict(raw.most_common(30)),
        )
