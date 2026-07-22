# -*- coding: utf-8 -*-
"""Verification Engine — 1/7/14/30 + aggregate metrics → Memory."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from commerce_ai.jsonl_util import append_jsonl, read_jsonl, rewrite_jsonl
from commerce_ai.models import (
    VerificationMetrics,
    VerificationResult,
    VerificationSnapshot,
)
from commerce_ai.stability.errors import report_error
from commerce_ai.stability.logging_setup import get_logger
from commerce_ai.stability.resilience import safe_call

VERIFY_DIR = Path(__file__).resolve().parent.parent / "commerce_history"
VERIFY_PATH = VERIFY_DIR / "verifications.jsonl"
_log = get_logger("commerce_ai.verification")


class VerificationEngine:
    WINDOWS = (1, 7, 14, 30)

    def __init__(self, path: Path | None = None, memory=None) -> None:
        self.path = path or VERIFY_PATH
        self.memory = memory
        safe_call(
            lambda: self.path.parent.mkdir(parents=True, exist_ok=True),
            component="verification.mkdir",
            default=None,
        )

    def _rows(self, *, use_cache: bool = True) -> list[dict[str, Any]]:
        return read_jsonl(self.path, use_cache=use_cache)

    def open_case(
        self,
        *,
        recommendation_id: str,
        action: str,
        product_id: str,
        baseline: dict[str, Any],
        expected_lift: dict[str, float] | None = None,
        category: str = "",
    ) -> dict:
        case = {
            "opened_at": datetime.now().strftime("%Y-%m-%d"),
            "ts": datetime.now().isoformat(timespec="seconds"),
            "recommendation_id": recommendation_id,
            "action": action,
            "category": category,
            "product_id": product_id,
            "baseline": baseline,
            "expected_lift": expected_lift or {},
            "checkpoints": {str(d): None for d in self.WINDOWS},
            "status": "pending",
            "failure_reason": "",
        }

        def _write() -> None:
            append_jsonl(self.path, case)

        safe_call(_write, component="verification.open_case", default=None)
        _log.info(
            "verification.open_case id=%s product=%s",
            recommendation_id,
            product_id,
        )
        return case

    def due(self, today: datetime | None = None) -> list[dict]:
        today = today or datetime.now()
        due: list[dict] = []
        try:
            rows = self._rows()
        except OSError as e:
            report_error("verification.due", e, recoverable=True)
            return due
        for ev in rows:
            try:
                start = datetime.strptime(ev["opened_at"], "%Y-%m-%d")
            except Exception:
                continue
            cps = ev.get("checkpoints") or {}
            for d in self.WINDOWS:
                if cps.get(str(d)) is None and today.date() >= (
                    start + timedelta(days=d)
                ).date():
                    due.append({**ev, "dueDays": d})
        _log.debug("verification.due count=%s", len(due))
        return due

    def record_ab_result(
        self,
        recommendation_id: str,
        *,
        metric: str,
        value_a: float,
        value_b: float,
        day: int = 7,
        sync_memory: bool = True,
    ) -> dict:
        """
        Compare A vs B on a metric; store winner on verification case + Memory.
        Higher is better for CTR/CVR/revenue/ROAS; for rank, lower is better.
        """
        if not self.path.exists():
            return {"ok": False, "error": "no cases"}

        higher_better = metric.lower() not in {"rank"}
        if higher_better:
            if value_a > value_b * 1.02:
                winner = "A"
            elif value_b > value_a * 1.02:
                winner = "B"
            else:
                winner = "tie"
        else:
            if value_a < value_b * 0.98:
                winner = "A"
            elif value_b < value_a * 0.98:
                winner = "B"
            else:
                winner = "tie"

        lift_a = None
        lift_b = None
        base = min(value_a, value_b) or 1.0
        try:
            lift_a = round((value_a - base) / abs(base) * 100, 1)
            lift_b = round((value_b - base) / abs(base) * 100, 1)
        except Exception:
            pass

        def _update() -> dict:
            rows = read_jsonl(self.path, use_cache=False)
            found = False
            out: list[dict] = []
            for ev in rows:
                if ev.get("recommendation_id") == recommendation_id:
                    found = True
                    ev = dict(ev)
                    ev["ab"] = {
                        "day": day,
                        "metric": metric,
                        "value_a": value_a,
                        "value_b": value_b,
                        "winner": winner,
                    }
                    if winner == "A":
                        ev["status"] = "success"
                    elif winner == "B":
                        ev["status"] = "partial"
                        ev["failure_reason"] = "A/B에서 B 우세 — 가설 재검토"
                    else:
                        ev["status"] = "partial"
                        ev["failure_reason"] = "A/B 차이 미미"
                out.append(ev)
            if found:
                rewrite_jsonl(self.path, out)
            return {"ok": found, "winner": winner}

        result = safe_call(_update, component="verification.ab", default={"ok": False}) or {
            "ok": False
        }
        if sync_memory and self.memory is not None and result.get("ok"):
            safe_call(
                lambda: self.memory.record_ab_winner(
                    recommendation_id,
                    winner=winner,
                    metric=metric,
                    lift_a=lift_a,
                    lift_b=lift_b,
                    note=f"A={value_a} B={value_b} → {winner}",
                ),
                component="verification.ab_memory",
                default=None,
            )
        _log.info(
            "verification.ab id=%s winner=%s metric=%s",
            recommendation_id,
            winner,
            metric,
        )
        return {
            "ok": bool(result.get("ok")),
            "winner": winner,
            "metric": metric,
            "value_a": value_a,
            "value_b": value_b,
            "lift_a": lift_a,
            "lift_b": lift_b,
        }

    def record_checkpoint(
        self,
        recommendation_id: str,
        day: int,
        snapshot: VerificationSnapshot,
        *,
        mark_final: bool = False,
        sync_memory: bool = True,
    ) -> VerificationResult | None:
        if not self.path.exists():
            return None

        def _update() -> VerificationResult | None:
            rows = read_jsonl(self.path, use_cache=False)
            result: VerificationResult | None = None
            out: list[dict] = []
            for ev in rows:
                if ev.get("recommendation_id") == recommendation_id:
                    ev = dict(ev)
                    cps = dict(ev.get("checkpoints") or {})
                    cps[str(day)] = {
                        "day": snapshot.day,
                        "rank": snapshot.rank,
                        "ctr": snapshot.ctr,
                        "cvr": snapshot.cvr,
                        "revenue": snapshot.revenue,
                        "profit": snapshot.profit,
                        "roas": snapshot.roas,
                        "impressions": snapshot.impressions,
                        "conversions": snapshot.conversions,
                    }
                    ev["checkpoints"] = cps
                    if mark_final or day >= 30:
                        result = self._judge(ev)
                        ev["status"] = result.status
                        ev["failure_reason"] = result.failure_reason
                        ev["accuracy_notes"] = result.accuracy_notes
                    else:
                        provisional = self._judge(ev, provisional=True)
                        ev["status"] = provisional.status
                        ev["accuracy_notes"] = provisional.accuracy_notes
                        result = provisional
                out.append(ev)
            rewrite_jsonl(self.path, out)
            return result

        result = safe_call(_update, component="verification.checkpoint", default=None)
        if (
            sync_memory
            and self.memory is not None
            and result
            and result.status in {"success", "fail"}
        ):
            safe_call(
                lambda: self.memory.mark_outcome(
                    recommendation_id,
                    result.status,
                    note="; ".join(result.accuracy_notes[:3]),
                    failure_reason=result.failure_reason,
                ),
                component="verification.sync_memory",
                default=None,
            )
        _log.info(
            "verification.checkpoint id=%s day=%s status=%s",
            recommendation_id,
            day,
            getattr(result, "status", None),
        )
        return result

    def _judge(self, ev: dict, provisional: bool = False) -> VerificationResult:
        baseline = ev.get("baseline") or {}
        expected = ev.get("expected_lift") or {}
        cps = ev.get("checkpoints") or {}
        latest = None
        for d in ("30", "14", "7", "1"):
            if cps.get(d):
                latest = cps[d]
                break
        notes: list[str] = []
        status = "pending"
        fail = ""
        if latest:
            improved = 0
            checked = 0
            for key, label in (
                ("ctr", "CTR"),
                ("cvr", "CVR"),
                ("revenue", "매출"),
                ("roas", "ROAS"),
            ):
                b, a = baseline.get(key), latest.get(key)
                if b is None or a is None:
                    continue
                checked += 1
                try:
                    b, a = float(b), float(a)
                except (TypeError, ValueError):
                    continue
                exp = float(expected.get(key, 0) or 0)
                delta_pct = ((a - b) / abs(b) * 100) if b else 0
                if delta_pct > 0:
                    improved += 1
                    notes.append(f"{label} {delta_pct:+.1f}%")
                else:
                    notes.append(f"{label} {delta_pct:+.1f}% (기대 {exp:+.0f}%)")
            br, ar = baseline.get("rank"), latest.get("rank")
            if isinstance(br, int) and isinstance(ar, int):
                checked += 1
                if ar < br:
                    improved += 1
                    notes.append(f"순위 {br}->{ar}")
                else:
                    notes.append(f"순위 {br}->{ar} (미개선)")

            if checked == 0:
                status = "pending"
            elif improved >= max(1, checked // 2 + checked % 2):
                status = (
                    "success"
                    if not provisional or any(cps.get(str(d)) for d in (7, 14, 30))
                    else "partial"
                )
            else:
                status = "fail" if not provisional else "partial"
                fail = "핵심 KPI 미개선 — 가설 재검토 필요"
        return VerificationResult(
            recommendation_id=ev.get("recommendation_id", ""),
            action=ev.get("action", ""),
            product_id=ev.get("product_id", ""),
            status=status,
            baseline=baseline,
            checkpoints={
                k: VerificationSnapshot(**v) if isinstance(v, dict) else v
                for k, v in cps.items()
                if isinstance(v, dict)
            },
            accuracy_notes=notes,
            failure_reason=fail,
        )

    def success_fail_rates(
        self, product_id: str = ""
    ) -> tuple[float | None, float | None]:
        m = self.aggregate_metrics(product_id=product_id)
        return m.success_rate, m.fail_rate

    def aggregate_metrics(self, product_id: str = "") -> VerificationMetrics:
        if not self.path.exists():
            return VerificationMetrics()
        ok = fail = pending = 0
        ctr_ds: list[float] = []
        cvr_ds: list[float] = []
        roas_ds: list[float] = []
        rev_ds: list[float] = []
        try:
            rows = self._rows()
        except OSError as e:
            report_error("verification.metrics", e, recoverable=True)
            return VerificationMetrics()

        for ev in rows:
            if product_id and ev.get("product_id") != product_id:
                continue
            st = ev.get("status")
            if st == "success":
                ok += 1
            elif st == "fail":
                fail += 1
            elif st in {"pending", "partial", None}:
                pending += 1
            baseline = ev.get("baseline") or {}
            cps = ev.get("checkpoints") or {}
            latest = None
            for d in ("30", "14", "7", "1"):
                if cps.get(d):
                    latest = cps[d]
                    break
            if not latest:
                continue
            for key, bucket in (
                ("ctr", ctr_ds),
                ("cvr", cvr_ds),
                ("roas", roas_ds),
                ("revenue", rev_ds),
            ):
                b, a = baseline.get(key), latest.get(key)
                if b is None or a is None:
                    continue
                try:
                    b, a = float(b), float(a)
                except (TypeError, ValueError):
                    continue
                if b:
                    bucket.append((a - b) / abs(b) * 100)

        total = ok + fail
        return VerificationMetrics(
            success_rate=(ok / total) if total else None,
            fail_rate=(fail / total) if total else None,
            n_success=ok,
            n_fail=fail,
            n_pending=pending,
            avg_ctr_delta_pct=(sum(ctr_ds) / len(ctr_ds)) if ctr_ds else None,
            avg_cvr_delta_pct=(sum(cvr_ds) / len(cvr_ds)) if cvr_ds else None,
            avg_roas_delta_pct=(sum(roas_ds) / len(roas_ds)) if roas_ds else None,
            avg_revenue_delta_pct=(sum(rev_ds) / len(rev_ds)) if rev_ds else None,
        )
