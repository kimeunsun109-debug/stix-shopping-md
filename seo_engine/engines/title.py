# -*- coding: utf-8 -*-
"""Title Optimizer + scoring for SEO / CTR / CVR."""
from __future__ import annotations

from seo_engine.engines.gap import GapReport
from seo_engine.engines.keyword_extractor import ExtractedKeyword
from seo_engine.keywords import extract_tokens, normalize
from seo_engine.models import CollectionBundle, TitleVariant


class TitleOptimizer:
    def generate(
        self,
        bundle: CollectionBundle,
        extracted: list[ExtractedKeyword],
        gap: GapReport,
        *,
        n: int = 8,
    ) -> list[TitleVariant]:
        core = [e.keyword for e in extracted if e.coverage_ratio >= 0.4][:8]
        must = gap.missing[:5]
        brand = bundle.mine.brand or ("스팃스" if "스팃스" in bundle.mine.title else "스팃스")
        orig = [t for t in extract_tokens(bundle.mine.title) if t not in gap.delete_candidates]

        front: list[str] = []
        for k in must + core:
            if k.lower() not in " ".join(front).lower() and k not in {"스팃스", "STIX"}:
                front.append(k)
            if len(front) >= 6:
                break

        pools: list[list[str]] = [
            front[:8] + ([brand] if brand else []) + orig[:3],
            (front[:2] or ["DIY"]) + front[2:6] + [brand] + must[:2],
            [x for x in front if x != brand][:6] + [brand] + ["초보"] ,
            front[:5] + (["선물", "집콕"] if "선물" not in front else ["인테리어"]),
            front[:4] + [brand] + (["액자형"] if "액자" in " ".join(must + core) else ["키트"]),
            core[:3] + must[:2] + [brand] + orig[:2],
            front[:3] + ["취미", "DIY"] + [brand],
            must[:3] + core[:3] + [brand],
            front[:5] + ["완성", brand],
            [bundle.keyword] + front[:4] + [brand] if bundle.keyword else front[:6] + [brand],
        ]

        variants: list[TitleVariant] = []
        seen: set[str] = set()
        for parts in pools:
            title = self._join(parts)
            if not title or title in seen:
                continue
            seen.add(title)
            variants.append(self._score(title, bundle, extracted, gap, brand))
            if len(variants) >= n:
                break

        while len(variants) < min(5, n):
            fallback = self._join(front[:5] + [brand])
            if fallback not in seen:
                seen.add(fallback)
                variants.append(self._score(fallback, bundle, extracted, gap, brand))
            else:
                break

        variants.sort(key=lambda v: -v.composite)
        return variants

    def _join(self, parts: list[str], max_len: int = 52) -> str:
        out: list[str] = []
        for p in parts:
            p = normalize(str(p))
            if not p or p in out:
                continue
            cand = (" ".join(out + [p])).strip()
            if len(cand) <= max_len:
                out.append(p)
        return " ".join(out)

    def _score(
        self,
        title: str,
        bundle: CollectionBundle,
        extracted: list[ExtractedKeyword],
        gap: GapReport,
        brand: str,
    ) -> TitleVariant:
        tokens = set(extract_tokens(title))
        core = [e for e in extracted if e.coverage_ratio >= 0.4]
        hit = sum(1 for e in core if e.keyword in tokens)
        coverage = hit / max(len(core), 1)

        # SEO: front-load + coverage + length
        front15 = title[:15]
        front_hits = sum(1 for e in core[:3] if e.keyword in front15)
        seo = 40 + coverage * 40 + front_hits * 5
        if 25 <= len(title) <= 50:
            seo += 8
        if brand and brand in title:
            seo += 5
        if any(d in title for d in gap.delete_candidates[:5]):
            seo -= 5
        seo = max(0, min(100, seo))

        # CTR: readable, benefit words, not too long
        benefit = sum(1 for w in ("초보", "선물", "집콕", "인테리어", "완성", "액자") if w in title)
        ctr = 45 + benefit * 6 + front_hits * 4
        if len(title) > 55:
            ctr -= 10
        if len(title) < 20:
            ctr -= 5
        ctr = max(0, min(100, ctr))

        # CVR proxy: trust/clarity tokens
        cvr = 50 + (5 if brand in title else 0)
        cvr += 4 if any(w in title for w in ("초보", "키트", "구성")) else 0
        cvr += 3 if any(w in title for w in ("액자", "도안", "캔버스")) else 0
        cvr += coverage * 20
        cvr = max(0, min(100, cvr))

        impressions = 0.3 + coverage * 0.5 + front_hits * 0.05
        purchase = 0.02 + (cvr / 100) * 0.06
        exposure = min(100.0, impressions * 100 + front_hits * 8 + coverage * 20)
        composite = seo * 0.4 + ctr * 0.25 + cvr * 0.2 + exposure * 0.15

        reasons = []
        for e in core[:5]:
            if e.keyword in front15:
                reasons.append(
                    f"'{e.keyword}'를 앞쪽에 배치하여 검색 일치율 증가 "
                    f"(검색량 {getattr(e, 'search_volume', '중간')})"
                )
        for m in gap.missing[:3]:
            if m in tokens:
                reasons.append(f"유실 키워드 '{m}' 복구로 노출 회복 기대")
        if coverage >= 0.7:
            reasons.append("핵심 키워드 커버리지 양호")
        if benefit:
            reasons.append("CTR 유도 키워드(초보/선물/집콕 등) 포함")
        if brand in title and title.find(brand) >= 10:
            reasons.append(f"브랜드 '{brand}'를 중후반에 배치해 검색어 우선순위 확보")
        elif brand in title:
            reasons.append(f"브랜드 '{brand}' 포함")
        for d in gap.delete_candidates[:2]:
            if d not in title:
                reasons.append(f"노이즈 키워드 '{d}' 제거로 가독성/관련성 개선")
        if not reasons:
            reasons.append("기본 SEO 구조 적용")

        return TitleVariant(
            title=title,
            seo_score=round(seo, 1),
            ctr_score=round(ctr, 1),
            cvr_score=round(cvr, 1),
            expected_impressions=round(impressions, 3),
            expected_purchase_rate=round(purchase, 4),
            composite=round(composite, 1),
            reasons=reasons[:6],
            exposure_score=round(exposure, 1),
        )
