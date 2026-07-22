# -*- coding: utf-8
"""Item winner pricing rules — shared by report and monitor."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PriceInput:
    label: str
    my_price: int
    competitor_price: int
    min_price: int
    is_winner: bool
    step: int = 10
    target_price: int | None = None
    hold_price: int | None = None
    reactive_lower_only: bool = False
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

    if inp.reactive_lower_only and inp.hold_price is not None:
        hold = inp.hold_price
        if my < hold and comp >= hold:
            return PriceDecision(
                action="RAISE",
                current_price=my,
                recommended_price=hold,
                reason=f"유지가 {hold:,}원 복원 (경쟁자 {comp:,}원 ≥ 유지가)",
            )
        if comp >= hold:
            return PriceDecision(
                action="HOLD",
                current_price=my,
                recommended_price=hold if my != hold else my,
                reason=(
                    f"유지가 {hold:,}원 — 경쟁자 {comp:,}원, 인하 시에만 추격 (사용자 지시)"
                ),
            )
        candidate = comp - step
        if candidate < floor:
            return PriceDecision(
                action="HOLD",
                current_price=my,
                recommended_price=my,
                reason=(
                    f"경쟁자 {comp:,}원. 추격가 {candidate:,}원 < 최소허용 {floor:,}원 → 유지"
                ),
            )
        if candidate == my:
            return PriceDecision(
                action="HOLD",
                current_price=my,
                recommended_price=my,
                reason="경쟁자 인하 추격 완료 → 변경 없음",
            )
        return PriceDecision(
            action="LOWER",
            current_price=my,
            recommended_price=candidate,
            reason=f"경쟁자 {comp:,}원 인하 → {candidate:,}원 추격 ({step}원 단계)",
        )

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
                    f"→ 가격 유지 (규칙 3)"
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
