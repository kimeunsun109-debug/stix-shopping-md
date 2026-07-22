# -*- coding: utf-8 -*-
"""Knowledge Evolution — mine Commerce Memory for reusable patterns."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from commerce_ai.jsonl_util import read_jsonl
from commerce_ai.memory import MEMORY_PATH
from commerce_ai.stability.logging_setup import get_logger

_log = get_logger("commerce_ai.knowledge")


@dataclass
class KnowledgePattern:
    pattern: str
    context: str
    outcome: str  # success tendency
    metric: str
    avg_lift_pct: float
    n: int
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class KnowledgeEvolution:
    """Find recurring success/fail patterns from Memory KB."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or MEMORY_PATH

    def discover(self, *, min_n: int = 3) -> list[KnowledgePattern]:
        if not self.path.exists():
            return []
        buckets: dict[str, list[dict]] = defaultdict(list)
        for e in read_jsonl(self.path):
            if e.get("outcome") not in {"success", "fail"}:
                continue
            action = e.get("action") or e.get("category") or "unknown"
            kb = e.get("kb") or {}
            season = kb.get("season") or "all"
            band = kb.get("priceBand") or "unknown"
            market = kb.get("marketplace") or e.get("marketplace") or "all"
            traits = list(kb.get("imageTraits") or [])[:2]
            keys = [
                f"action:{action}",
                f"action:{action}|season:{season}",
                f"action:{action}|price:{band}",
                f"action:{action}|market:{market}",
            ]
            for t in traits:
                keys.append(f"trait:{t}|action:{action}")
            blob = f"{e.get('reason','')} {e.get('action','')}"
            for token in ("DIY", "집콕", "빨간", "밝은", "주말", "할인", "액자"):
                if token in blob:
                    keys.append(f"signal:{token}|action:{action}")
            for k in keys:
                buckets[k].append(e)

        patterns: list[KnowledgePattern] = []
        for key, rows in buckets.items():
            if len(rows) < min_n:
                continue
            ok = sum(1 for r in rows if r.get("outcome") == "success")
            fail = sum(1 for r in rows if r.get("outcome") == "fail")
            n = ok + fail
            if n < min_n:
                continue
            rate = ok / n
            lifts = [
                r.get("ctrDeltaPct")
                for r in rows
                if r.get("outcome") == "success" and r.get("ctrDeltaPct") is not None
            ]
            metric = "CTR"
            if not lifts:
                lifts = [
                    r.get("cvrDeltaPct")
                    for r in rows
                    if r.get("outcome") == "success" and r.get("cvrDeltaPct") is not None
                ]
                metric = "CVR"
            if not lifts:
                lifts = [
                    r.get("revenueDeltaPct")
                    for r in rows
                    if r.get("outcome") == "success"
                    and r.get("revenueDeltaPct") is not None
                ]
                metric = "revenue"
            avg = sum(lifts) / len(lifts) if lifts else 0.0
            outcome = (
                "always_up" if rate >= 0.75 else ("mixed" if rate >= 0.45 else "risky")
            )
            label = key.replace("|", " · ").replace("action:", "").replace("signal:", "")
            patterns.append(
                KnowledgePattern(
                    pattern=label,
                    context=key,
                    outcome=outcome,
                    metric=metric,
                    avg_lift_pct=round(avg, 1),
                    n=n,
                    confidence=round(min(95.0, 50 + rate * 40 + min(n, 20)), 1),
                )
            )
        patterns.sort(key=lambda p: (-p.confidence, -p.n))
        _log.debug("knowledge.discover patterns=%s", len(patterns))
        return patterns[:40]

    def lessons_text(self, limit: int = 8) -> list[str]:
        out = []
        for p in self.discover()[:limit]:
            if p.outcome == "always_up":
                out.append(
                    f"{p.pattern} → 주로 {p.metric} 상승 "
                    f"(평균 {p.avg_lift_pct:+.0f}%, n={p.n})"
                )
            elif p.outcome == "risky":
                out.append(f"{p.pattern} → 실패 경향 (n={p.n}) — 신중 적용")
            else:
                out.append(f"{p.pattern} → 혼재 (성공 혼합, n={p.n})")
        return out
