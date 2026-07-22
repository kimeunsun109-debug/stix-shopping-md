# -*- coding: utf-8 -*-
"""AB Test Engine v3 — labeled A/B/C comparison with reasons."""
from __future__ import annotations

from seo_engine.models import TitleVariant


class AbTestEngine:
    def compare(
        self, variants: list[TitleVariant]
    ) -> tuple[TitleVariant | None, list[str], list[str]]:
        """Returns (best, ab_summary_lines, recommendation_reasons)."""
        if not variants:
            return None, ["비교할 상품명 후보 없음"], []
        ranked = sorted(variants, key=lambda v: -v.composite)
        best = ranked[0]
        labels = "ABCDEFGHIJ"
        lines = ["[AB Test 비교]"]
        for i, v in enumerate(ranked[:10]):
            lab = labels[i] if i < len(labels) else str(i + 1)
            mark = " << 추천" if i == 0 else ""
            lines.append(
                f"  {lab}) SEO {v.seo_score:.0f} | CTR {v.ctr_score:.0f} | "
                f"CVR {v.cvr_score:.0f} | 노출 {v.exposure_score:.0f} | "
                f"종합 {v.composite:.0f}{mark}"
            )
            lines.append(f"     {v.title}")
        lines.append(
            "운영 팁: 상위 2안을 7일 단위로 교체 A/B 후 Ranking Monitor로 승자 확정"
        )
        reasons = [f"추천 상품명: {best.title}"]
        reasons.extend(best.reasons)
        if len(ranked) > 1:
            gap = best.composite - ranked[1].composite
            reasons.append(
                f"2안 대비 종합 +{gap:.1f}점 "
                f"(SEO {best.seo_score:.0f} vs {ranked[1].seo_score:.0f})"
            )
        return best, lines, reasons
