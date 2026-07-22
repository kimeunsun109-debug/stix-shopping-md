# -*- coding: utf-8 -*-
"""Commerce Dashboard v6 — Operations Center."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from commerce_ai.cache import CACHE

HISTORY = Path(__file__).resolve().parent.parent / "commerce_history"
SEO_HISTORY = Path(__file__).resolve().parent.parent / "seo_history"


class CommerceDashboard:
    """운영 센터 — today / week / month + scores + pending + alerts."""

    def format_text(self) -> str:
        cached = CACHE.get("dashboard", "main")
        if cached is not None:
            return cached
        text = self._build()
        CACHE.set("dashboard", "main", text, ttl_sec=60.0)
        return text

    def to_ops_payload(self) -> dict:
        """Structured payload for web Operations Center (/md)."""
        cached = CACHE.get("dashboard", "ops_payload")
        if cached is not None:
            return cached
        from commerce_ai.batch_ops import load_recent_snapshots
        from commerce_ai.container import get_container
        from commerce_ai.ops_catalog import catalog_stats
        from commerce_ai.stability.logging_setup import get_logger

        _log = get_logger("commerce_ai.dashboard")
        c = get_container()
        assert c.verification is not None
        vm = c.verification.aggregate_metrics()
        due = c.verification.due()
        health = c.monitor.health()
        period = self._period_scores()
        snaps = load_recent_snapshots(800)
        _log.debug("dashboard.to_ops_payload snaps=%s due=%s", len(snaps), len(due))
        today = datetime.now().strftime("%Y-%m-%d")
        today_snaps = [s for s in snaps if s.get("date") == today] or snaps[-200:]

        rank_drops = []
        ctr_drops = []
        cvr_drops = []
        golden_changes = []
        must_do = []
        expected_revenue = []

        # from snapshots
        by_pid: dict[str, list] = {}
        for s in snaps:
            by_pid.setdefault(str(s.get("product_id")), []).append(s)
        for pid, hist in by_pid.items():
            if len(hist) < 2:
                continue
            a, b = hist[-2], hist[-1]
            if (a.get("seo_score") or 0) - (b.get("seo_score") or 0) >= 10:
                rank_drops.append(
                    {
                        "product_id": pid,
                        "title": b.get("title"),
                        "from": a.get("seo_score"),
                        "to": b.get("seo_score"),
                        "kind": "seo_drop",
                    }
                )
            ca, cb = a.get("ctr"), b.get("ctr")
            if ca and cb and cb < ca * 0.9:
                ctr_drops.append(
                    {
                        "product_id": pid,
                        "title": b.get("title"),
                        "from": ca,
                        "to": cb,
                    }
                )
            va, vb = a.get("cvr"), b.get("cvr")
            if va and vb and vb < va * 0.9:
                cvr_drops.append(
                    {
                        "product_id": pid,
                        "title": b.get("title"),
                        "from": va,
                        "to": vb,
                    }
                )
            ga = set(a.get("golden_keywords") or [])
            gb = set(b.get("golden_keywords") or [])
            if ga != gb and (ga or gb):
                golden_changes.append(
                    {
                        "product_id": pid,
                        "title": b.get("title"),
                        "added": sorted(gb - ga)[:5],
                        "removed": sorted(ga - gb)[:5],
                    }
                )

        # SEO history rank drops
        if SEO_HISTORY.exists():
            for path in sorted(SEO_HISTORY.glob("*.json")):
                if path.name.startswith("learning"):
                    continue
                try:
                    recs = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if not isinstance(recs, list) or not recs:
                    continue
                last = recs[-1]
                rb, ra = last.get("rankBefore"), last.get("rankAfter")
                if isinstance(rb, int) and isinstance(ra, int) and ra - rb >= 5:
                    rank_drops.insert(
                        0,
                        {
                            "product_id": last.get("productId"),
                            "title": last.get("title"),
                            "from": rb,
                            "to": ra,
                            "kind": "rank_drop",
                        },
                    )

        for s in today_snaps:
            for r in s.get("recommendations") or []:
                if r.get("must_do_today"):
                    must_do.append(
                        {
                            "product_id": s.get("product_id"),
                            "title": s.get("title"),
                            "action": r.get("action"),
                            "confidence": r.get("confidence"),
                            "evidence": r.get("evidence"),
                            "expected_effect": r.get("expected_effect"),
                            "expected_impact": r.get("expected_impact"),
                            "risk": r.get("risk"),
                            "effort_minutes": r.get("effort_minutes"),
                            "commerce_score": s.get("commerce_score"),
                            "revenue_score": s.get("revenue_score"),
                        }
                    )
                if r.get("revenue_lift_pct"):
                    expected_revenue.append(
                        {
                            "product_id": s.get("product_id"),
                            "title": s.get("title"),
                            "action": r.get("action"),
                            "revenue_lift_pct": r.get("revenue_lift_pct"),
                            "lift_pct": r.get("lift_pct"),
                        }
                    )

        must_do.sort(key=lambda x: -(x.get("confidence") or 0))
        expected_revenue.sort(key=lambda x: -(x.get("revenue_lift_pct") or 0))

        avg_commerce = (
            round(
                sum(s.get("commerce_score") or 0 for s in today_snaps) / len(today_snaps),
                1,
            )
            if today_snaps
            else period.get("commerce_score")
        )
        avg_revenue = (
            round(
                sum(s.get("revenue_score") or 0 for s in today_snaps) / len(today_snaps),
                1,
            )
            if today_snaps
            else period.get("revenue_score")
        )

        from commerce_ai.opportunity import OpportunityEngine
        from commerce_ai.priority import PriorityEngine
        from commerce_ai.reports import ReportEngine
        from commerce_ai.self_eval import SelfEvaluationEngine

        opps = OpportunityEngine().detect(today_snaps)
        tasks = PriorityEngine().rank(opps, verify_due=due, limit=50)
        board = {
            "urgent": [t.to_dict() for t in tasks if t.lane == "urgent"],
            "high": [t.to_dict() for t in tasks if t.lane == "high"],
            "normal": [t.to_dict() for t in tasks if t.lane == "normal"],
            "verify": [t.to_dict() for t in tasks if t.lane == "verify"],
            "done": [],
        }
        # prefer priority board as today_tasks
        today_board_tasks = [
            t.to_dict()
            for t in tasks
            if t.lane in {"urgent", "high", "normal"}
        ][:40]
        # attach A/B + evidence from latest snapshots (action-centric)
        ab_index: dict[str, dict] = {}
        for s in today_snaps:
            for r in s.get("recommendations") or []:
                key = f"{s.get('product_id')}|{r.get('action')}"
                ab_index[key] = r
        for t in today_board_tasks:
            key = f"{t.get('product_id')}|{t.get('action')}"
            src = ab_index.get(key) or {}
            if src.get("ab_test"):
                t["ab_test"] = src["ab_test"]
            if src.get("evidence") and not t.get("evidence"):
                t["evidence"] = src["evidence"]
            if src.get("failure_risk"):
                t["failure_risk"] = src["failure_risk"]
            if src.get("expected_impact"):
                t["expected_impact"] = src["expected_impact"]
        for lane in board.values():
            for t in lane:
                key = f"{t.get('product_id')}|{t.get('action')}"
                src = ab_index.get(key) or {}
                if src.get("ab_test"):
                    t["ab_test"] = src["ab_test"]
                if src.get("failure_risk"):
                    t["failure_risk"] = src["failure_risk"]
        daily = ReportEngine().build_daily(snapshots=today_snaps, save=False)
        self_eval = SelfEvaluationEngine().evaluate()

        payload = {
            "version": "7.0",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "catalog": catalog_stats(),
            "scores": {
                "commerce_score": avg_commerce,
                "revenue_score": avg_revenue,
                "recommendation_success_rate": vm.success_rate,
                "recommendation_fail_rate": vm.fail_rate,
                "recommendation_accuracy": self_eval.accuracy_pct,
                "avg_ctr_delta_pct": vm.avg_ctr_delta_pct,
                "avg_cvr_delta_pct": vm.avg_cvr_delta_pct,
                "avg_roas_delta_pct": vm.avg_roas_delta_pct,
                "expected_revenue_lift_avg": daily.expected_revenue_lift,
                "expected_ctr_lift_avg": daily.expected_ctr_lift,
                "expected_cvr_lift_avg": daily.expected_cvr_lift,
            },
            "period": period,
            "health": health.to_dict(),
            "board": board,
            "daily_report": daily.to_dict(),
            "self_evaluation": self_eval.to_dict(),
            "today_tasks": today_board_tasks or must_do[:40],
            "urgent": board["urgent"]
            + [{"type": "rank_drop", **x} for x in rank_drops[:10]],
            "rank_drops": rank_drops[:20],
            "ctr_drops": ctr_drops[:20],
            "cvr_drops": cvr_drops[:20],
            "golden_keyword_changes": golden_changes[:20],
            "expected_effects": expected_revenue[:30],
            "snapshots_today": len(today_snaps),
            "snapshots_total": len(snaps),
            "verification_due": [
                {
                    "recommendation_id": d.get("recommendation_id"),
                    "action": d.get("action"),
                    "product_id": d.get("product_id"),
                    "dueDays": d.get("dueDays"),
                }
                for d in due[:30]
            ],
        }
        CACHE.set("dashboard", "ops_payload", payload, ttl_sec=60.0)
        return payload

    def _build(self) -> str:
        from commerce_ai.container import get_container

        c = get_container()
        assert c.verification is not None
        vm = c.verification.aggregate_metrics()
        due = c.verification.due()
        health = c.monitor.health()

        period = self._period_scores()

        lines = [
            "=" * 72,
            "STIX Commerce AI v6.0 - Operations Center",
            "=" * 72,
            "",
            "[시스템]",
            f"  Health: {'OK' if health.ok else 'DEGRADED'} | "
            f"errors(24h): {health.error_count_24h}",
            "",
            "[핵심 지표]",
            f"  Commerce Score (최근): {period['commerce_score']}",
            f"  Revenue Score (최근): {period['revenue_score']}",
            f"  Recommendation Accuracy: "
            + (
                f"{vm.success_rate*100:.0f}%"
                if vm.success_rate is not None
                else "(데이터 없음)"
            ),
            f"  Verification Success Rate: "
            + (
                f"{vm.success_rate*100:.0f}% ({vm.n_success}ok/{vm.n_fail}fail)"
                if vm.success_rate is not None
                else f"(pending {vm.n_pending})"
            ),
            f"  Avg CTR Δ: {self._fmt_pct(vm.avg_ctr_delta_pct)} | "
            f"CVR Δ: {self._fmt_pct(vm.avg_cvr_delta_pct)} | "
            f"ROAS Δ: {self._fmt_pct(vm.avg_roas_delta_pct)}",
            "",
            "[기간 성과]",
            f"  오늘  분석 {period['today']}건 | 추천 기록 {period['today_mem']}건",
            f"  이번주 분석 {period['week']}건 | 추천 기록 {period['week_mem']}건",
            f"  이번달 분석 {period['month']}건 | 추천 기록 {period['month_mem']}건",
            "",
            "[Pending Actions / Urgent Alerts]",
        ]

        tasks: list[str] = []
        for d in due[:8]:
            tasks.append(
                f"  - [VERIFY D+{d.get('dueDays')}] {d.get('action')} "
                f"({d.get('product_id')})"
            )

        for f in health.findings[:5]:
            if f.severity in {"warn", "critical"}:
                tasks.insert(
                    0,
                    f"  - [{f.severity.upper()}] {f.component}: {f.message} x{f.count}",
                )

        learn = HISTORY / "learning_events.jsonl"
        if learn.exists():
            for line in learn.read_text(encoding="utf-8").splitlines()[-5:]:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                acts = ", ".join((e.get("actions") or [])[:3])
                tasks.append(
                    f"  - [PLAN] {e.get('productId')} "
                    f"SEO{e.get('seoScore')} Rev{e.get('revenueScore')} | {acts}"
                )

        if SEO_HISTORY.exists():
            for path in sorted(SEO_HISTORY.glob("*.json")):
                if path.name.startswith("learning"):
                    continue
                try:
                    recs = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if not isinstance(recs, list) or not recs:
                    continue
                last = recs[-1]
                rb, ra = last.get("rankBefore"), last.get("rankAfter")
                if isinstance(rb, int) and isinstance(ra, int) and ra - rb >= 5:
                    tasks.insert(
                        0,
                        f"  - [CRITICAL] {last.get('productId')} 순위 급락 {rb}->{ra}",
                    )

        if not tasks:
            tasks.append("  - 긴급 없음 — 일일 Commerce 분석 유지")
        lines.extend(tasks)

        lines.append("")
        lines.append("[Top Opportunities]")
        opps = self._top_opportunities()
        lines.extend(opps or ["  - (추천 이력 없음 — 분석을 실행하세요)"])

        lines.append("")
        lines.append("[오늘 하지 않아도 되는 작업]")
        lines.append("  - FAQ/상세 카피 보강 (신뢰도 중간 구간) — 여유 시")
        lines.append("  - 광고 미세조정 — SEO 복구 후")

        lines.append("")
        lines.append("[상품 현황]")
        lines.append(f"  {'위험':8} {'SEO':>4} {'순위':>4} {'Δ':>4}  상품")
        items = []
        if SEO_HISTORY.exists():
            for path in sorted(SEO_HISTORY.glob("*.json")):
                if path.name.startswith("learning"):
                    continue
                try:
                    recs = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if not isinstance(recs, list) or not recs:
                    continue
                last = recs[-1]
                seo = last.get("seoScore") or 0
                risk = "low"
                if seo < 50:
                    risk = "high"
                elif seo < 65:
                    risk = "medium"
                rb, ra = last.get("rankBefore"), last.get("rankAfter")
                delta = "-"
                if isinstance(rb, int) and isinstance(ra, int):
                    d = ra - rb
                    delta = f"{d:+d}"
                    if d >= 5:
                        risk = "critical"
                items.append(
                    f"  {risk:8} {seo:>4} {str(ra or rb or '-'):>4} {delta:>4}  "
                    f"{last.get('productId')} | {str(last.get('title') or '')[:36]}"
                )
        lines.extend(items[:40] or ["  (이력 없음)"])

        mem = HISTORY / "commerce_memory.jsonl"
        if mem.exists():
            lines.append("")
            lines.append("[Commerce Memory KB — 최근 성공/실패]")
            for line in mem.read_text(encoding="utf-8").splitlines()[-8:]:
                try:
                    e = json.loads(line)
                    kb = e.get("kb") or {}
                    lines.append(
                        f"  - [{e.get('outcome','?')}] {e.get('action')} | "
                        f"{kb.get('marketplace','')} {kb.get('season','')} "
                        f"{kb.get('priceBand','')} | {e.get('reason','')[:36]}"
                    )
                except Exception:
                    pass

        lines.append("")
        return "\n".join(lines)

    def _fmt_pct(self, v: float | None) -> str:
        if v is None:
            return "-"
        return f"{v:+.1f}%"

    def _period_scores(self) -> dict:
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        learn = HISTORY / "learning_events.jsonl"
        mem = HISTORY / "commerce_memory.jsonl"

        def count_since(path: Path, since) -> int:
            if not path.exists():
                return 0
            n = 0
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    e = json.loads(line)
                    d = datetime.strptime(
                        (e.get("date") or e.get("opened_at") or "")[:10],
                        "%Y-%m-%d",
                    ).date()
                except Exception:
                    continue
                if d >= since:
                    n += 1
            return n

        commerce_score = revenue_score = "-"
        if learn.exists():
            try:
                last = json.loads(
                    [ln for ln in learn.read_text(encoding="utf-8").splitlines() if ln.strip()][-1]
                )
                snap = last.get("snapshot") or {}
                commerce_score = snap.get("commerce_score", "-")
                revenue_score = last.get("revenueScore", "-")
            except Exception:
                pass

        return {
            "today": count_since(learn, today),
            "week": count_since(learn, week_ago),
            "month": count_since(learn, month_ago),
            "today_mem": count_since(mem, today),
            "week_mem": count_since(mem, week_ago),
            "month_mem": count_since(mem, month_ago),
            "commerce_score": commerce_score,
            "revenue_score": revenue_score,
        }

    def _top_opportunities(self) -> list[str]:
        mem = HISTORY / "commerce_memory.jsonl"
        if not mem.exists():
            return []
        pending = []
        for line in reversed(mem.read_text(encoding="utf-8").splitlines()):
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("outcome") != "pending":
                continue
            pending.append(
                f"  - {e.get('action')} | {e.get('productId')} | "
                f"{e.get('reason','')[:40]}"
            )
            if len(pending) >= 5:
                break
        return pending
