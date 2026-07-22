# -*- coding: utf-8 -*-
"""Detail Page Generator — problem → empathy → benefits → reviews → how-to → FAQ → CTA."""
from __future__ import annotations

from seo_engine.engines.gap import GapReport
from seo_engine.models import CollectionBundle, ReviewInsight


class DetailPageGenerator:
    STRUCTURE = [
        "문제 제기",
        "공감",
        "핵심 장점",
        "실사용 후기",
        "사용방법",
        "FAQ",
        "구매 CTA",
    ]

    def generate(
        self,
        bundle: CollectionBundle,
        review: ReviewInsight,
        gap: GapReport,
    ) -> tuple[str, str, list[str], list[str]]:
        """Returns (headline_copy, full_detail, selling_points, structure)."""
        selling = review.advantages[:10]
        while len(selling) < 10:
            for d in (
                "초보도 쉽게 가능",
                "집중력 향상",
                "선물 추천",
                "스트레스 해소",
                "인테리어 효과",
                "완성 만족감",
                "아이와 함께",
                "집콕 취미",
                "구성품 알참",
                "가성비",
            ):
                if d not in selling:
                    selling.append(d)
                if len(selling) >= 10:
                    break

        theme_candidates = [
            k
            for k in gap.missing
            if k in {"집콕", "취미", "인테리어", "액자형", "선물", "초보", "집중력"}
        ]
        theme = (
            theme_candidates[0]
            if theme_candidates
            else (gap.missing[0] if gap.missing else (selling[0] if selling else "취미용 DIY"))
        )
        p1, p2 = selling[0], selling[1] if len(selling) > 1 else "예쁘게 완성"
        title = bundle.mine.title[:40]

        headline = "\n".join(
            [
                "[문제] 집에서도 제대로 된 취미를 시작하기 어려우셨나요?",
                f"[공감] 바쁜 일상 속에서도 '{theme}'(으)로 나만의 시간을 갖고 싶은 분들이 많습니다.",
                f"[핵심] {title} - {p1}, {p2}.",
                "[신뢰] 실제 구매 후기에서 가장 많이 언급된 포인트 중심으로 구성했습니다.",
                "[CTA] 지금 구성품 확인하고, 오늘부터 천천히 완성해보세요.",
            ]
        )

        complaints_faq = review.complaints[:3] or ["난이도", "구성", "배송"]
        faq_lines = []
        for c in complaints_faq:
            faq_lines.append(f"Q. {c}이(가) 걱정돼요\nA. 구성·난이도·사용 팁을 상세에 명시했습니다. 초보 기준 가이드를 따라가면 됩니다.")

        review_lines = review.advantages[:3]
        full = "\n\n".join(
            [
                "## 1. 문제 제기\n집에서도 제대로 된 취미를 시작하기 어려우셨나요?",
                f"## 2. 공감\n'{theme}'로 나만의 시간을 갖고 싶은 분들이 많습니다.",
                "## 3. 핵심 장점\n" + "\n".join(f"- {s}" for s in selling[:6]),
                "## 4. 실사용 후기\n" + "\n".join(f"- {r}" for r in review_lines),
                "## 5. 사용방법\n1) 구성품 확인\n2) 도안/키트 준비\n3) 차근차근 부착\n4) 완성 후 액자/전시",
                "## 6. FAQ\n" + "\n\n".join(faq_lines),
                f"## 7. 구매 CTA\n{title} - 지금 구성 확인하고 시작해보세요.",
            ]
        )
        return headline, full, selling[:10], list(self.STRUCTURE)
