# -*- coding: utf-8 -*-
"""Commerce Memory — Knowledge Base (success/fail with context matching)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from commerce_ai.jsonl_util import append_jsonl, read_jsonl, rewrite_jsonl
from commerce_ai.models import KnowledgeContext
from commerce_ai.stability.errors import report_error
from commerce_ai.stability.logging_setup import get_logger
from commerce_ai.stability.resilience import safe_call

MEMORY_DIR = Path(__file__).resolve().parent.parent / "commerce_history"
MEMORY_PATH = MEMORY_DIR / "commerce_memory.jsonl"
_log = get_logger("commerce_ai.memory")

_CATEGORY_HINTS = {
    "title": ("상품명", "title"),
    "image": ("대표이미지", "이미지", "image"),
    "price": ("가격", "price"),
    "faq": ("FAQ", "faq"),
    "detail": ("상세", "detail"),
    "keyword": ("Keyword", "키워드", "keyword"),
    "ad": ("광고", "ad"),
    "stock": ("재고", "stock"),
    "review": ("리뷰", "review"),
    "seo": ("SEO", "순위 급락", "seo"),
}

_SEASON_MONTHS = {
    "spring": (3, 4, 5),
    "summer": (6, 7, 8),
    "autumn": (9, 10, 11),
    "winter": (12, 1, 2),
}


def current_season(month: int | None = None) -> str:
    m = month or datetime.now().month
    for name, months in _SEASON_MONTHS.items():
        if m in months:
            return name
    return "all"


def price_band(price: int | float | None) -> str:
    if price is None:
        return "unknown"
    p = float(price)
    if p < 10000:
        return "under_10k"
    if p < 30000:
        return "10k_30k"
    if p < 100000:
        return "30k_100k"
    return "over_100k"


class CommerceMemory:
    """Knowledge Base — stores contextual outcomes and retrieves similar wins."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or MEMORY_PATH
        safe_call(
            lambda: self.path.parent.mkdir(parents=True, exist_ok=True),
            component="memory.mkdir",
            default=None,
        )

    def entries(self) -> list[dict[str, Any]]:
        """Cached JSONL rows (mtime-invalidated)."""
        return read_jsonl(self.path)

    def record(
        self,
        *,
        product_id: str,
        marketplace: str,
        keyword: str,
        action: str,
        reason: str,
        metrics_before: dict | None = None,
        metrics_after: dict | None = None,
        tags: list[str] | None = None,
        category: str = "",
        outcome: str = "pending",
        recommendation_id: str = "",
        context: KnowledgeContext | None = None,
        failure_reason: str = "",
        image_traits: list[str] | None = None,
        review_traits: list[str] | None = None,
        product_category: str = "",
        price: int | float | None = None,
    ) -> dict:
        before = metrics_before or {}
        after = metrics_after or {}
        ctx = context or KnowledgeContext(
            category=product_category or category,
            marketplace=marketplace,
            season=current_season(),
            price_band=price_band(price if price is not None else before.get("price")),
            image_traits=image_traits or [],
            review_traits=review_traits or [],
        )

        def delta_pct(key: str) -> float | None:
            b, a = before.get(key), after.get(key)
            if b is None or a is None:
                return None
            try:
                b, a = float(b), float(a)
            except (TypeError, ValueError):
                return None
            if b == 0:
                return None
            return round((a - b) / abs(b) * 100, 1)

        ctr_d = delta_pct("ctr")
        cvr_d = delta_pct("cvr")
        rev_d = delta_pct("revenue")
        if outcome == "pending" and any(x is not None for x in (ctr_d, cvr_d, rev_d)):
            pos = sum(1 for x in (ctr_d, cvr_d, rev_d) if x is not None and x > 0)
            neg = sum(1 for x in (ctr_d, cvr_d, rev_d) if x is not None and x < 0)
            if pos > neg:
                outcome = "success"
            elif neg > pos:
                outcome = "fail"

        entry = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "ts": datetime.now().isoformat(timespec="seconds"),
            "productId": product_id,
            "marketplace": marketplace,
            "keyword": keyword,
            "action": action,
            "category": category,
            "reason": reason,
            "tags": tags or [],
            "outcome": outcome,
            "recommendationId": recommendation_id,
            "failureReason": failure_reason,
            "ctrDeltaPct": ctr_d,
            "cvrDeltaPct": cvr_d,
            "revenueDeltaPct": rev_d,
            "rankBefore": before.get("rank"),
            "rankAfter": after.get("rank"),
            "rankDelta": (
                (before["rank"] - after["rank"])
                if isinstance(before.get("rank"), int)
                and isinstance(after.get("rank"), int)
                else None
            ),
            "dwellDeltaPct": delta_pct("dwell"),
            "kb": {
                "productCategory": ctx.category,
                "marketplace": ctx.marketplace or marketplace,
                "season": ctx.season or current_season(),
                "priceBand": ctx.price_band or price_band(price),
                "imageTraits": ctx.image_traits,
                "reviewTraits": ctx.review_traits,
            },
        }
        try:
            append_jsonl(self.path, entry)
            _log.debug("memory.record %s %s", category or action, outcome)
        except OSError as e:
            report_error("memory.record", e, recoverable=True)
        return entry

    def mark_outcome(
        self,
        recommendation_id: str,
        outcome: str,
        *,
        note: str = "",
        failure_reason: str = "",
        metrics_after: dict | None = None,
    ) -> int:
        if not self.path.exists():
            return 0

        def _rewrite() -> int:
            n = 0
            rows = read_jsonl(self.path, use_cache=False)
            out: list[dict] = []
            for e in rows:
                if e.get("recommendationId") == recommendation_id:
                    e = dict(e)
                    e["outcome"] = outcome
                    if note:
                        e["outcomeNote"] = note
                    if failure_reason:
                        e["failureReason"] = failure_reason
                    if metrics_after:
                        e["metricsAfter"] = metrics_after
                    n += 1
                out.append(e)
            if n:
                rewrite_jsonl(self.path, out)
            return n

        result = safe_call(_rewrite, component="memory.mark_outcome", default=0)
        return int(result or 0)

    def action_stats(
        self, category: str, rows: list[dict[str, Any]] | None = None
    ) -> dict:
        hints = _CATEGORY_HINTS.get(category, (category,))
        ok = fail = 0
        data = rows if rows is not None else self.entries()
        if not data:
            return {"n": 0, "success_rate": 0.5, "ok": 0, "fail": 0}
        for e in data:
            blob = f"{e.get('category','')} {e.get('action','')}".lower()
            if not any(h.lower() in blob for h in hints):
                continue
            if e.get("outcome") == "success":
                ok += 1
            elif e.get("outcome") == "fail":
                fail += 1
        n = ok + fail
        rate = (ok / n) if n else 0.5
        return {"n": n, "success_rate": rate, "ok": ok, "fail": fail}

    def find_similar_successes(
        self,
        *,
        action_category: str,
        context: KnowledgeContext,
        limit: int = 27,
        prefer_recent_days: int = 90,
        rows: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Prefer matching context + recent successes."""
        data = rows if rows is not None else self.entries()
        if not data:
            return []
        hints = _CATEGORY_HINTS.get(action_category, (action_category,))
        scored: list[tuple[float, dict]] = []
        now = datetime.now()
        for e in data:
            if e.get("outcome") != "success":
                continue
            blob = f"{e.get('category','')} {e.get('action','')}".lower()
            if not any(h.lower() in blob for h in hints):
                continue
            kb = e.get("kb") or {}
            score = 0.0
            if kb.get("marketplace") == (context.marketplace or ""):
                score += 3
            if kb.get("season") == (context.season or current_season()):
                score += 2
            if kb.get("priceBand") == (context.price_band or ""):
                score += 2
            if context.category and kb.get("productCategory") == context.category:
                score += 3
            img = set(kb.get("imageTraits") or [])
            if img and set(context.image_traits) & img:
                score += 1
            rev = set(kb.get("reviewTraits") or [])
            if rev and set(context.review_traits) & rev:
                score += 1
            try:
                ts = datetime.fromisoformat(str(e.get("ts") or e.get("date") or ""))
                age = (now - ts).days
                if age <= 14:
                    score += 4
                elif age <= 30:
                    score += 3
                elif age <= prefer_recent_days:
                    score += 1.5
            except ValueError:
                pass
            if e.get("abWinner"):
                score += 1.5
            scored.append((score, e))
        scored.sort(key=lambda x: (-x[0], x[1].get("ts", "")))
        return [e for _, e in scored[:limit]]

    def evidence_for(
        self,
        action_category: str,
        context: KnowledgeContext | None = None,
        *,
        rows: list[dict[str, Any]] | None = None,
        similar: list[dict[str, Any]] | None = None,
        hist: dict | None = None,
    ) -> tuple[str, float | None]:
        """Return (evidence text, avg CTR lift). Optional precomputed rows/similar/hist."""
        ctx = context or KnowledgeContext(season=current_season())
        data = rows if rows is not None else self.entries()
        if similar is None:
            similar = self.find_similar_successes(
                action_category=action_category, context=ctx, limit=50, rows=data
            )
        if hist is None:
            hist = self.action_stats(action_category, rows=data)
        if similar:
            recent = similar[:34]
            ctrs = [
                e["ctrDeltaPct"]
                for e in recent
                if e.get("ctrDeltaPct") is not None
            ]
            avg_ctr = sum(ctrs) / len(ctrs) if ctrs else None
            ab_n = sum(1 for e in recent if e.get("abWinner"))
            return (
                f"최근 {len(recent)}개 성공 사례"
                + (f" (A/B 승자 {ab_n}건 포함)" if ab_n else "")
                + (
                    f" · 유사조건 평균 CTR {avg_ctr:+.0f}%"
                    if avg_ctr is not None
                    else " · 유사조건 우선"
                ),
                avg_ctr,
            )
        if hist["n"] > 0:
            return (
                f"과거 {hist['n']}건 중 성공 {hist['ok']}건 "
                f"(성공률 {hist['success_rate']*100:.0f}%)",
                None,
            )
        return ("유사 성공 사례 부족 — 기본 휴리스틱 사용", None)

    def record_ab_winner(
        self,
        recommendation_id: str,
        *,
        winner: str,
        metric: str,
        lift_a: float | None = None,
        lift_b: float | None = None,
        note: str = "",
    ) -> int:
        if not self.path.exists():
            return 0

        def _rewrite() -> int:
            n = 0
            rows = read_jsonl(self.path, use_cache=False)
            out: list[dict] = []
            for e in rows:
                if e.get("recommendationId") == recommendation_id:
                    e = dict(e)
                    e["abWinner"] = winner
                    e["abMetric"] = metric
                    e["abLiftA"] = lift_a
                    e["abLiftB"] = lift_b
                    e["outcome"] = "success" if winner in {"A", "B"} else e.get("outcome")
                    if note:
                        e["outcomeNote"] = note
                    n += 1
                out.append(e)
            if n:
                rewrite_jsonl(self.path, out)
            return n

        return int(safe_call(_rewrite, component="memory.ab_winner", default=0) or 0)

    def lessons(self, product_id: str = "", limit: int = 12) -> list[str]:
        notes: list[str] = []
        for e in reversed(self.entries()):
            if product_id and e.get("productId") != product_id:
                continue
            outcome = e.get("outcome") or "pending"
            bits = [f"[{outcome}]", e.get("action", ""), e.get("reason", "")[:50]]
            for k, label in (
                ("ctrDeltaPct", "CTR"),
                ("cvrDeltaPct", "CVR"),
                ("revenueDeltaPct", "매출"),
                ("dwellDeltaPct", "체류"),
            ):
                if e.get(k) is not None:
                    bits.append(f"{label} {e[k]:+.0f}%")
            if e.get("failureReason"):
                bits.append(f"실패원인:{e['failureReason'][:40]}")
            notes.append(" | ".join(b for b in bits if b))
            if len(notes) >= limit:
                break
        return notes
