# -*- coding: utf-8 -*-
"""AI MD Daily / Weekly / Monthly reports."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from commerce_ai.batch_ops import load_recent_snapshots
from commerce_ai.container import get_container
from commerce_ai.knowledge import KnowledgeEvolution
from commerce_ai.opportunity import OpportunityEngine
from commerce_ai.ops_catalog import catalog_stats
from commerce_ai.priority import PriorityEngine, PriorityTask
from commerce_ai.self_eval import SelfEvaluationEngine
from commerce_ai.stability.logging_setup import get_logger

HISTORY = Path(__file__).resolve().parent.parent / "commerce_history"
DAILY_DIR = HISTORY / "daily"
WEEKLY_DIR = HISTORY / "weekly"
MONTHLY_DIR = HISTORY / "monthly"
_log = get_logger("commerce_ai.reports")


@dataclass
class DailyReport:
    date: str
    analyzed_catalog: int
    analyzed_today: int
    urgent_count: int
    recommendation_count: int
    expected_revenue_lift: float
    expected_ctr_lift: float
    expected_cvr_lift: float
    top_tasks: list[dict[str, Any]] = field(default_factory=list)
    opportunities: int = 0
    self_accuracy: float | None = None
    text: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class ReportEngine:
    def build_daily(
        self,
        *,
        snapshots: list[dict] | None = None,
        save: bool = True,
    ) -> DailyReport:
        snaps = snapshots if snapshots is not None else load_recent_snapshots(800)
        today = datetime.now().strftime("%Y-%m-%d")
        today_snaps = [s for s in snaps if s.get("date") == today] or snaps[-200:]
        cat = catalog_stats()

        opps = OpportunityEngine().detect(today_snaps)
        c = get_container()
        due = c.verification.due() if c.verification else []
        tasks = PriorityEngine().rank(opps, verify_due=due, limit=40)
        urgent = [t for t in tasks if t.lane == "urgent"]
        work = [t for t in tasks if t.lane in {"urgent", "high", "normal"}]

        rev = self._avg([t.expected_revenue_lift for t in work[:20]])
        ctr = self._avg([t.expected_ctr_lift for t in work[:20]])
        cvr = self._avg([t.expected_cvr_lift for t in work[:20]])
        ev = SelfEvaluationEngine().evaluate()

        top = [t.to_dict() for t in work[:10]]
        report = DailyReport(
            date=today,
            analyzed_catalog=cat.get("total_valid") or 0,
            analyzed_today=len(today_snaps),
            urgent_count=len(urgent),
            recommendation_count=len(work),
            expected_revenue_lift=rev,
            expected_ctr_lift=ctr,
            expected_cvr_lift=cvr,
            top_tasks=top,
            opportunities=len(opps),
            self_accuracy=ev.accuracy_pct,
        )
        report.text = self._format_daily(report, tasks)
        if save:
            DAILY_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d")
            (DAILY_DIR / f"AI_MD_Daily_{stamp}.txt").write_text(
                report.text, encoding="utf-8"
            )
            (DAILY_DIR / f"AI_MD_Daily_{stamp}.json").write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return report

    def build_weekly(self, *, save: bool = True) -> dict[str, Any]:
        snaps = load_recent_snapshots(2000)
        since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        week = [s for s in snaps if (s.get("date") or "") >= since]
        ev = SelfEvaluationEngine().evaluate()
        lessons = KnowledgeEvolution().lessons_text(limit=8)

        grown = sorted(
            week, key=lambda s: -(s.get("commerce_score") or 0)
        )[:5]
        risky = sorted(week, key=lambda s: (s.get("seo_score") or 100))[:5]

        payload = {
            "period": "weekly",
            "from": since,
            "to": datetime.now().strftime("%Y-%m-%d"),
            "analyzed": len(week),
            "top_grown": [
                {
                    "product_id": s.get("product_id"),
                    "title": s.get("title"),
                    "commerce_score": s.get("commerce_score"),
                    "seo_score": s.get("seo_score"),
                }
                for s in grown
            ],
            "most_risky": [
                {
                    "product_id": s.get("product_id"),
                    "title": s.get("title"),
                    "seo_score": s.get("seo_score"),
                    "alerts": s.get("alerts") or [],
                }
                for s in risky
            ],
            "recommendation_success_rate": ev.accuracy_pct,
            "recommendation_fail_rate": (
                round(ev.fail / max(1, ev.success + ev.fail) * 100, 1)
                if (ev.success + ev.fail)
                else None
            ),
            "lessons": lessons,
            "next_week_strategy": ev.next_adjustments,
            "self_eval": ev.to_dict(),
        }
        payload["text"] = self._format_weekly(payload)
        if save:
            WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d")
            (WEEKLY_DIR / f"AI_MD_Weekly_{stamp}.txt").write_text(
                payload["text"], encoding="utf-8"
            )
            (WEEKLY_DIR / f"AI_MD_Weekly_{stamp}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        return payload

    def build_monthly(self, *, save: bool = True) -> dict[str, Any]:
        snaps = load_recent_snapshots(5000)
        since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        month = [s for s in snaps if (s.get("date") or "") >= since]
        ev = SelfEvaluationEngine().evaluate()
        patterns = [p.to_dict() for p in KnowledgeEvolution().discover()[:15]]
        c = get_container()
        vm = c.verification.aggregate_metrics() if c.verification else None

        avg = lambda key: (
            round(sum(s.get(key) or 0 for s in month) / len(month), 1) if month else 0
        )
        payload = {
            "period": "monthly",
            "from": since,
            "to": datetime.now().strftime("%Y-%m-%d"),
            "analyzed": len(month),
            "avg_commerce_score": avg("commerce_score"),
            "avg_revenue_score": avg("revenue_score"),
            "avg_seo_score": avg("seo_score"),
            "avg_ctr": (
                round(
                    sum(s["ctr"] for s in month if s.get("ctr")) 
                    / max(1, sum(1 for s in month if s.get("ctr"))),
                    4,
                )
                if any(s.get("ctr") for s in month)
                else None
            ),
            "avg_cvr": (
                round(
                    sum(s["cvr"] for s in month if s.get("cvr"))
                    / max(1, sum(1 for s in month if s.get("cvr"))),
                    4,
                )
                if any(s.get("cvr") for s in month)
                else None
            ),
            "verification": vm.to_dict() if vm else None,
            "ai_accuracy": ev.accuracy_pct,
            "memory_patterns": patterns,
            "memory_growth": ev.total,
            "golden_keyword_sample": self._golden_changes(month),
            "self_eval": ev.to_dict(),
        }
        payload["text"] = self._format_monthly(payload)
        if save:
            MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m")
            (MONTHLY_DIR / f"AI_MD_Monthly_{stamp}.txt").write_text(
                payload["text"], encoding="utf-8"
            )
            (MONTHLY_DIR / f"AI_MD_Monthly_{stamp}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        return payload

    def _golden_changes(self, snaps: list[dict]) -> list[dict]:
        by_pid: dict[str, list] = {}
        for s in snaps:
            by_pid.setdefault(str(s.get("product_id")), []).append(s)
        out = []
        for pid, hist in by_pid.items():
            if len(hist) < 2:
                continue
            a, b = hist[0], hist[-1]
            ga, gb = set(a.get("golden_keywords") or []), set(b.get("golden_keywords") or [])
            if ga != gb:
                out.append(
                    {
                        "product_id": pid,
                        "title": b.get("title"),
                        "added": sorted(gb - ga)[:5],
                        "removed": sorted(ga - gb)[:5],
                    }
                )
            if len(out) >= 15:
                break
        return out

    def _avg(self, xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 1) if xs else 0.0

    def _format_daily(self, r: DailyReport, tasks: list[PriorityTask]) -> str:
        lines = [
            "=" * 40,
            f"📅 {r.date}",
            "AI MD Daily Report",
            "=" * 40,
            "",
            f"오늘 분석 상품 (스냅샷)   {r.analyzed_today}개",
            f"카탈로그 유효 상품         {r.analyzed_catalog}개",
            f"긴급 수정                 {r.urgent_count}개",
            f"추천 작업                 {r.recommendation_count}개",
            f"기회(Opportunity)         {r.opportunities}개",
            f"예상 매출 증가            +{r.expected_revenue_lift}%",
            f"예상 CTR                  +{r.expected_ctr_lift}%",
            f"예상 CVR                  +{r.expected_cvr_lift}%",
        ]
        if r.self_accuracy is not None:
            lines.append(f"AI 추천 정확도            {r.self_accuracy}%")
        lines += ["", "오늘 가장 중요한 작업", ""]
        work = [t for t in tasks if t.lane in {"urgent", "high", "normal"}][:8]
        for i, t in enumerate(work, 1):
            mark = {"urgent": "🔴", "high": "🟠", "normal": "🟡"}.get(t.lane, "•")
            lines.append(
                f"{mark} {i}️⃣ {t.action} — {t.product_title[:36]}"
            )
            lines.append(
                f"    ROI {t.roi_score} | Conf {t.confidence:.0f}% | "
                f"매출 +{t.expected_revenue_lift}% | ~{t.effort_minutes}분"
            )
            if t.evidence:
                lines.append(f"    Evidence: {t.evidence[:70]}")
        lines.append("")
        lines.append("AI는 승인 없이 상품을 수정하지 않습니다.")
        lines.append("")
        return "\n".join(lines)

    def _format_weekly(self, p: dict) -> str:
        lines = [
            "=" * 40,
            f"AI MD Weekly Review ({p['from']} ~ {p['to']})",
            "=" * 40,
            f"분석 스냅샷: {p['analyzed']}",
            f"추천 성공률: {p.get('recommendation_success_rate')}%",
            f"추천 실패율: {p.get('recommendation_fail_rate')}%",
            "",
            "[가장 많이 성장한 상품]",
        ]
        for s in p.get("top_grown") or []:
            lines.append(
                f"  - Commerce {s.get('commerce_score')} | {str(s.get('title'))[:40]}"
            )
        lines.append("")
        lines.append("[가장 위험한 상품]")
        for s in p.get("most_risky") or []:
            lines.append(f"  - SEO {s.get('seo_score')} | {str(s.get('title'))[:40]}")
        lines.append("")
        lines.append("[이번 주 배운 내용]")
        for x in p.get("lessons") or ["(데이터 축적 중)"]:
            lines.append(f"  - {x}")
        lines.append("")
        lines.append("[다음 주 추천 전략]")
        for x in p.get("next_week_strategy") or []:
            lines.append(f"  - {x}")
        lines.append("")
        return "\n".join(lines)

    def _format_monthly(self, p: dict) -> str:
        lines = [
            "=" * 40,
            f"AI MD Monthly Report ({p['from']} ~ {p['to']})",
            "=" * 40,
            f"분석: {p['analyzed']}",
            f"Commerce Score 평균: {p['avg_commerce_score']}",
            f"Revenue Score 평균: {p['avg_revenue_score']}",
            f"SEO Score 평균: {p['avg_seo_score']}",
            f"CTR 평균: {p.get('avg_ctr')}",
            f"CVR 평균: {p.get('avg_cvr')}",
            f"AI 추천 성공률: {p.get('ai_accuracy')}%",
            f"Commerce Memory 성장(건): {p.get('memory_growth')}",
            "",
            "[Knowledge Patterns]",
        ]
        for pat in (p.get("memory_patterns") or [])[:10]:
            lines.append(
                f"  - {pat.get('pattern')} → {pat.get('metric')} "
                f"{pat.get('avg_lift_pct'):+}% (n={pat.get('n')})"
            )
        lines.append("")
        lines.append("[Golden Keyword 변화]")
        for g in (p.get("golden_keyword_sample") or [])[:8]:
            lines.append(
                f"  - {str(g.get('title'))[:36]} +{g.get('added')} -{g.get('removed')}"
            )
        lines.append("")
        return "\n".join(lines)
