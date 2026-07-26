# -*- coding: utf-8
"""Item winner pricing rules — shared by report and monitor.

2026-07-26 정책 (사용자):
- 상대보다 10원 더 내리지 않음 (언더컷 금지)
- 동률 → HOLD (30분 주기 체크만)
- 상대가 더 낮음 → 상대 가격에 맞춤 (match)
"""
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
    defend_winner_only: bool = False
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
                    f"유지가 {hold:,}원 — 경쟁자 {comp:,}원, 인하 시에만 맞춤 (언더컷 금지)"
                ),
            )
        # 경쟁자가 유지가 아래로 내림 → 상대가에 맞춤 (floor 이상)
        if comp < floor:
            return PriceDecision(
                action="HOLD",
                current_price=my,
                recommended_price=my,
                reason=(
                    f"경쟁자 {comp:,}원 < 최소허용 {floor:,}원 → 맞춤 불가, 유지"
                ),
            )
        if comp == my:
            return PriceDecision(
                action="HOLD",
                current_price=my,
                recommended_price=my,
                reason="동률 — 가격조정 없음 (30분 체크만)",
            )
        return PriceDecision(
            action="LOWER" if comp < my else "RAISE",
            current_price=my,
            recommended_price=comp,
            reason=f"경쟁자 {comp:,}원 → 동가 맞춤 (언더컷 금지)",
        )

    if inp.defend_winner_only:
        if inp.is_winner:
            return PriceDecision(
                action="HOLD",
                current_price=my,
                recommended_price=my,
                reason=f"아이템위너 유지 중 ({my:,}원) → 변경 없음 (위너 방어 모드)",
            )
        # 위너 상실 — 상대가에 맞춤 (언더컷 금지), floor 이상만
        if comp < floor:
            return PriceDecision(
                action="HOLD",
                current_price=my,
                recommended_price=my,
                reason=(
                    f"위너 아님. 맞춤가 {comp:,}원 < 마지노선 {floor:,}원 "
                    f"→ 가격 유지 (위너 방어 모드)"
                ),
            )
        if comp >= my:
            return PriceDecision(
                action="HOLD",
                current_price=my,
                recommended_price=my,
                reason=(
                    f"위너 아님. 경쟁자 {comp:,}원 ≥ 현재가 — 가격 요인 아님 "
                    f"→ 유지 (위너 방어 모드)"
                ),
            )
        return PriceDecision(
            action="LOWER",
            current_price=my,
            recommended_price=comp,
            reason=(
                f"위너 상실. 경쟁자 {comp:,}원 → 동가 맞춤 탈환 "
                f"(마지노선 {floor:,}원 이상, 언더컷 금지)"
            ),
        )

    # 동률 → 무조건 HOLD (위너 여부 무관)
    if my == comp:
        return PriceDecision(
            action="HOLD",
            current_price=my,
            recommended_price=my,
            reason="동률 — 가격조정 없음 (30분 체크만)",
        )

    if inp.is_winner and my < comp:
        return PriceDecision(
            action="HOLD",
            current_price=my,
            recommended_price=my,
            reason="이미 아이템위너이며 경쟁자보다 낮음 → 변경 없음",
        )

    if comp < my:
        if comp < floor:
            return PriceDecision(
                action="HOLD",
                current_price=my,
                recommended_price=my,
                reason=(
                    f"경쟁자 {comp:,}원 < 최소허용 {floor:,}원 → 맞춤 불가, 유지"
                ),
            )
        return PriceDecision(
            action="LOWER",
            current_price=my,
            recommended_price=comp,
            reason=f"경쟁자 {comp:,}원 → 동가 맞춤 (언더컷 금지)",
        )

    # comp > my — 경쟁자가 더 비쌈. 위너면 유지, 아니면 인상 여지 없음(맞춤은 인하만)
    return PriceDecision(
        action="HOLD",
        current_price=my,
        recommended_price=my,
        reason=f"경쟁자 {comp:,}원 > 현재가 → 인하 불필요, 유지",
    )
