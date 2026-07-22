# -*- coding: utf-8 -*-
"""Self Evaluation — AI grades its own recommendation accuracy."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from commerce_ai.container import get_container
from commerce_ai.jsonl_util import read_jsonl
from commerce_ai.knowledge import KnowledgeEvolution
from commerce_ai.stability.logging_setup import get_logger

_log = get_logger("commerce_ai.self_eval")


@dataclass
class SelfEvaluation:
    total: int
    success: int
    fail: int
    pending: int
    accuracy_pct: float | None
    fail_reasons: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    next_adjustments: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SelfEvaluationEngine:
    def evaluate(self) -> SelfEvaluation:
        c = get_container()
        assert c.verification is not None
        vm = c.verification.aggregate_metrics()
        mem = c.memory
        ok = fail = pending = 0
        fail_notes: list[str] = []
        if mem.path.exists():
            for e in read_jsonl(mem.path):
                st = e.get("outcome")
                if st == "success":
                    ok += 1
                elif st == "fail":
                    fail += 1
                    fr = (
                        e.get("failureReason")
                        or e.get("outcomeNote")
                        or e.get("reason")
                    )
                    if fr:
                        fail_notes.append(str(fr)[:80])
                elif st == "pending":
                    pending += 1

        if vm.n_success + vm.n_fail > 0:
            ok, fail = vm.n_success, vm.n_fail
        total = ok + fail
        accuracy = round(ok / total * 100, 1) if total else None

        lessons = KnowledgeEvolution(mem.path).lessons_text(limit=6)
        adjustments: list[str] = []
        if accuracy is not None and accuracy < 70:
            adjustments.append("Confidence 임계값 상향 — 표본 부족 추천 억제")
        if fail_notes:
            adjustments.append("실패 원인 상위 패턴을 Priority 패널티에 반영")
        if vm.avg_ctr_delta_pct is not None and vm.avg_ctr_delta_pct < 0:
            adjustments.append("이미지/상품명 추천 비중 재검토 (CTR 평균 하락)")
        if not adjustments and accuracy and accuracy >= 80:
            adjustments.append("현재 전략 유지 — 성공 패턴 우선 재사용")

        uniq: list[str] = []
        seen: set[str] = set()
        for n in fail_notes:
            if n in seen:
                continue
            seen.add(n)
            uniq.append(n)
            if len(uniq) >= 8:
                break

        result = SelfEvaluation(
            total=total + pending,
            success=ok,
            fail=fail,
            pending=pending,
            accuracy_pct=accuracy,
            fail_reasons=uniq,
            lessons=lessons,
            next_adjustments=adjustments,
        )
        _log.info(
            "self_eval accuracy=%s success=%s fail=%s",
            accuracy,
            ok,
            fail,
        )
        return result
