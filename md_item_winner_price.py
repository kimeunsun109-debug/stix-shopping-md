# -*- coding: utf-8 -*-
"""Coupang Item Winner pricing strategy engine."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class PriceInput:
    label: str
    my_price: int
    competitor_price: int
    min_price: int
    is_winner: bool
    step: int = 10
    target_price: int | None = None
    note: str = ""


@dataclass
class PriceDecision:
    action: str  # HOLD | LOWER | RAISE
    current_price: int
    recommended_price: int
    reason: str


def decide(inp: PriceInput) -> PriceDecision:
    my = inp.my_price
    comp = inp.competitor_price
    floor = inp.min_price
    step = inp.step

    if inp.is_winner and my <= comp:
        return PriceDecision(
            action="HOLD",
            current_price=my,
            recommended_price=my,
            reason="이미 아이템위너이며 경쟁자 이하/동일 → 변경 없음 (규칙 1)",
        )

    if comp < my:
        candidate = comp - step
        if candidate < floor:
            return PriceDecision(
                action="HOLD",
                current_price=my,
                recommended_price=my,
                reason=(
                    f"경쟁자 {comp:,}원. 위너 확보가 {candidate:,}원 < 최소허용 {floor:,}원 "
                    f"→ 가격 유지 (규칙 3·최소 마진 보호)"
                ),
            )
        if candidate == my:
            return PriceDecision(
                action="HOLD",
                current_price=my,
                recommended_price=my,
                reason="이미 1단계 인하 상태 → 변경 없음 (규칙 5)",
            )
        return PriceDecision(
            action="LOWER",
            current_price=my,
            recommended_price=candidate,
            reason=f"경쟁자 {comp:,}원 → {candidate:,}원 1단계({step}원) 인하 (규칙 2)",
        )

    if comp > my:
        candidate = comp - step
        if candidate <= my:
            return PriceDecision(
                action="HOLD",
                current_price=my,
                recommended_price=my,
                reason=(
                    f"경쟁자 {comp:,}원. 위너 유지 최대가 {candidate:,}원 ≤ 현재가 → 유지 (규칙 4·5)"
                ),
            )
        candidate = max(candidate, floor)
        if inp.target_price:
            candidate = min(candidate, inp.target_price)
        return PriceDecision(
            action="RAISE",
            current_price=my,
            recommended_price=candidate,
            reason=f"경쟁자 {comp:,}원 인상 → 위너 유지 최대 {candidate:,}원 (규칙 4)",
        )

    if not inp.is_winner:
        candidate = my - step
        if candidate < floor:
            return PriceDecision(
                action="HOLD",
                current_price=my,
                recommended_price=my,
                reason=f"동가 {my:,}원·위너 아님. {candidate:,}원은 하한 미만 → 유지 (규칙 3)",
            )
        return PriceDecision(
            action="LOWER",
            current_price=my,
            recommended_price=candidate,
            reason=f"동가 {my:,}원·위너 아님 → {candidate:,}원 1단계 인하 (규칙 2)",
        )

    return PriceDecision(
        action="HOLD",
        current_price=my,
        recommended_price=my,
        reason="동가·위너 → 유지 (규칙 5)",
    )


def format_report(decisions: list[tuple[PriceInput, PriceDecision]], observed_at: str) -> str:
    lines = [
        "STIX 쿠팡 아이템위너 가격전략 리포트",
        f"관찰 시각: {observed_at}",
        "목표: 아이템위너 유지 + 이익 극대화",
        "=" * 72,
        "",
    ]
    urgent: list[str] = []
    for inp, dec in decisions:
        lines.extend(
            [
                f"[{inp.label}]",
                f"  내 가격       : {inp.my_price:,}원",
                f"  경쟁자 가격   : {inp.competitor_price:,}원",
                f"  최소허용가    : {inp.min_price:,}원",
                f"  아이템위너    : {'예' if inp.is_winner else '아니오/불명'}",
                f"  판단          : {dec.action}",
                f"  권장 가격     : {dec.recommended_price:,}원",
                f"  사유          : {dec.reason}",
            ]
        )
        if inp.note:
            lines.append(f"  참고          : {inp.note}")
        if dec.action != "HOLD":
            delta = dec.recommended_price - dec.current_price
            urgent.append(
                f"  ▶ {inp.label}: {dec.current_price:,} → {dec.recommended_price:,}원 ({delta:+,}원)"
            )
        lines.append("")

    lines.extend(["=" * 72, "[즉시 실행 권고 — Wing 승인 후 반영]", ""])
    if urgent:
        lines.extend(urgent)
    else:
        lines.append("  (금일 필수 변경 없음 — 모니터링 유지)")
    lines.extend(
        [
            "",
            "※ 상품 자동 수정 없음. Wing > 상품조회/수정 에서 반영하세요.",
            "※ 1·3번: 경쟁자 인하 시 10원 단위 추격. 2번: 경쟁 진입 우선.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    observed = datetime.now().strftime("%Y-%m-%d %H:%M")
    cases: list[PriceInput] = [
        PriceInput(
            label="1번 B7000 15ml×1 (vs 주식회사 빙고인터네셔널)",
            my_price=1650,
            competitor_price=1900,
            min_price=1290,
            is_winner=True,
            step=10,
            target_price=1500,
            note="동일 PDP 3판매자. 타판매자 1,260원 존재(하한 1,290원 미만 추격 불가). 빙고 하락 시 10원 단위 추격.",
        ),
        PriceInput(
            label="2번 B7000 15ml×3 (vs 온라인마켓) ★긴급",
            my_price=10560,
            competitor_price=10300,
            min_price=9790,
            is_winner=False,
            step=10,
            target_price=9990,
            note="로켓그로스 3개세트. 온라인마켓 10,300원 → 즉시 1단계 인하 필요.",
        ),
        PriceInput(
            label="3번 B7000 110ml×2 (vs 온라인마켓)",
            my_price=13800,
            competitor_price=13800,
            min_price=12490,
            is_winner=False,
            step=10,
            target_price=12990,
            note="동가 13,800원. 온라인마켓 하락 시 10원 단위 추격. 경쟁자<12,490원이면 유지만.",
        ),
    ]
    decisions = [(c, decide(c)) for c in cases]
    report = format_report(decisions, observed)
    out = Path(__file__).resolve().parent / f"MD_아이템위너_가격_{datetime.now():%Y-%m-%d}.txt"
    out.write_text(report, encoding="utf-8")
    print(out)
    print()
    print(report)


if __name__ == "__main__":
    main()
