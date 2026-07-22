# -*- coding: utf-8 -*-
"""Shared tokenization utils (marketplace-agnostic)."""
from __future__ import annotations

import re
from collections import Counter

SEED_KEYWORDS = [
    "보석십자수",
    "십자수",
    "DIY",
    "diy",
    "키트",
    "캔버스",
    "액자",
    "액자형",
    "초보",
    "초보자",
    "취미",
    "집콕",
    "인테리어",
    "선물",
    "고양이",
    "꽃",
    "튤립",
    "해바라기",
    "어린이",
    "스티커",
    "비즈",
    "큐빅",
    "만들기",
    "도안",
    "완성",
    "스트레스",
    "집중력",
    "당일발송",
    "스팃스",
    "STIX",
    "접착제",
    "본드",
    "치약본드",
    "E6000",
    "B7000",
    "30x40",
    "40x50",
    "30cm",
    "40cm",
    "50cm",
]

STOPWORDS = {
    "및",
    "등",
    "개",
    "종",
    "세트",
    "옵션",
    "이상",
    "이하",
    "구매",
    "판매",
    "상품",
    "쿠팡",
    "배송",
    "무료",
    "포함",
    "증정",
    "택1",
    "의",
    "을",
    "를",
    "이",
    "가",
    "은",
    "는",
    "와",
    "과",
    "로",
    "으로",
}


def normalize(text: str) -> str:
    t = (text or "").replace("\u00a0", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def canonicalize(token: str) -> str:
    return "DIY" if token.lower() == "diy" else token


def extract_tokens(text: str) -> list[str]:
    text = normalize(text)
    found: list[str] = []
    lower = text.lower()
    for kw in SEED_KEYWORDS:
        if kw.lower() in lower or kw in text:
            found.append(canonicalize(kw))
    for m in re.findall(r"[A-Za-z0-9]{2,}|[가-힣]{2,}", text):
        if m in STOPWORDS or len(m) == 1:
            continue
        if m.isdigit() and m not in {"30", "40", "50"}:
            continue
        found.append(canonicalize(m))
    for m in re.findall(r"\d{2}\s*[xX×]\s*\d{2}", text):
        found.append(re.sub(r"\s*", "", m).lower().replace("×", "x").replace("X", "x"))
    # preserve order, drop duplicates (seed + regex overlap)
    return list(dict.fromkeys(found))


def token_counter(texts: list[str]) -> Counter[str]:
    c: Counter[str] = Counter()
    for t in texts:
        for u in set(extract_tokens(t)):
            c[canonicalize(u)] += 1
    return c


def importance_stars(freq: int, n_competitors: int) -> str:
    if n_competitors <= 0:
        return "★★★☆☆"
    ratio = freq / n_competitors
    if ratio >= 0.9:
        return "★★★★★"
    if ratio >= 0.7:
        return "★★★★☆"
    if ratio >= 0.4:
        return "★★★☆☆"
    if ratio >= 0.2:
        return "★★☆☆☆"
    return "★☆☆☆☆"


def stars_to_tier(stars: str) -> str:
    mapping = {
        "★★★★★": "must",
        "★★★★☆": "strong",
        "★★★☆☆": "recommend",
        "★★☆☆☆": "optional",
        "★☆☆☆☆": "delete",
    }
    return mapping.get(stars, "recommend")
