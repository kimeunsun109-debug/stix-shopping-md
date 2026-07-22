# -*- coding: utf-8 -*-
"""
REST API + Web Operations Center for Commerce AI v6.

  python md_commerce_ai.py --web          # http://localhost:3000/md
  python md_commerce_ai.py --api          # http://localhost:8088 (API only)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from commerce_ai.container import get_container
from commerce_ai.models import CommerceInput, VerificationSnapshot
from commerce_ai.pipeline import run_commerce
from commerce_ai.stability.errors import report_error
from commerce_ai.stability.logging_setup import setup_logging

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import HTMLResponse, RedirectResponse
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore
    BaseModel = object  # type: ignore
    Field = None  # type: ignore
    HTTPException = Exception  # type: ignore
    HTMLResponse = None  # type: ignore
    RedirectResponse = None  # type: ignore
    Query = None  # type: ignore

WEB_MD = Path(__file__).resolve().parent / "web" / "md.html"


def create_app():
    if FastAPI is None:
        raise RuntimeError(
            "fastapi/uvicorn 미설치. pip install fastapi uvicorn 후 재시도하세요."
        )

    setup_logging()
    app = FastAPI(
        title="STIX Commerce AI",
        version="7.0.0",
        description="AI MD Autonomous Operation Mode",
    )

    class AnalyzeBody(BaseModel):
        marketplace: str = "coupang"
        mode: str = "manual"
        keyword: str = ""
        input_path: str | None = None
        mine_title: str | None = None
        commerce: dict[str, Any] = Field(default_factory=dict)
        save: bool = True

    class ApproveBody(BaseModel):
        plan_id: str
        step_id: str
        execute: bool = False
        plan: dict[str, Any]

    class VerifyBody(BaseModel):
        recommendation_id: str
        day: int
        rank: int | None = None
        ctr: float | None = None
        cvr: float | None = None
        revenue: int | None = None
        profit: int | None = None
        roas: float | None = None
        impressions: int | None = None
        conversions: int | None = None
        mark_final: bool = False

    @app.get("/")
    def root():
        return RedirectResponse("/md")

    @app.get("/md", response_class=HTMLResponse)
    def md_page():
        if not WEB_MD.exists():
            raise HTTPException(404, "md.html missing")
        return WEB_MD.read_text(encoding="utf-8")

    @app.get("/health")
    def health():
        h = get_container().monitor.health()
        return {"ok": h.ok, "version": "7.0.0", "monitor": h.to_dict()}

    @app.get("/dashboard")
    def dashboard():
        from commerce_ai.dashboard import CommerceDashboard

        dash = CommerceDashboard()
        return {"text": dash.format_text(), "ops": dash.to_ops_payload()}

    @app.get("/api/md/ops")
    def md_ops():
        from commerce_ai.dashboard import CommerceDashboard

        return CommerceDashboard().to_ops_payload()

    @app.get("/monitor")
    def monitor():
        return get_container().monitor.health().to_dict()

    @app.get("/catalog/stats")
    def catalog_stats():
        from commerce_ai.ops_catalog import catalog_stats as stats

        return stats()

    @app.get("/recommendations")
    def recommendations(limit: int = Query(40, ge=1, le=200)):
        from commerce_ai.dashboard import CommerceDashboard

        ops = CommerceDashboard().to_ops_payload()
        return {"items": (ops.get("today_tasks") or [])[:limit]}

    @app.get("/verification/due")
    def verification_due():
        assert get_container().verification is not None
        return {"due": get_container().verification.due()}

    @app.get("/verification/metrics")
    def verification_metrics():
        assert get_container().verification is not None
        return get_container().verification.aggregate_metrics().to_dict()

    @app.post("/api/md/batch")
    def batch_analyze(limit: int = Query(100, ge=1, le=500)):
        from commerce_ai.batch_ops import run_batch
        from commerce_ai.cache import clear_runtime_caches

        try:
            summary = run_batch(limit=limit)
            clear_runtime_caches()
            return summary
        except Exception as e:
            report_error("api.batch", e, recoverable=True)
            raise HTTPException(500, str(e)) from e

    @app.post("/api/md/daily")
    def md_daily(
        skip_batch: bool = Query(True),
        limit: int = Query(100, ge=1, le=500),
    ):
        from commerce_ai.autonomous import run_autonomous_daily

        try:
            return run_autonomous_daily(batch_limit=limit, skip_batch=skip_batch)
        except Exception as e:
            report_error("api.daily", e, recoverable=True)
            raise HTTPException(500, str(e)) from e

    @app.get("/api/md/report/daily")
    def report_daily():
        from commerce_ai.reports import ReportEngine

        return ReportEngine().build_daily(save=False).to_dict()

    @app.get("/api/md/report/weekly")
    def report_weekly():
        from commerce_ai.reports import ReportEngine

        return ReportEngine().build_weekly(save=False)

    @app.get("/api/md/report/monthly")
    def report_monthly():
        from commerce_ai.reports import ReportEngine

        return ReportEngine().build_monthly(save=False)

    @app.get("/api/md/self-eval")
    def self_eval():
        from commerce_ai.self_eval import SelfEvaluationEngine

        return SelfEvaluationEngine().evaluate().to_dict()

    @app.post("/analyze")
    def analyze(body: AnalyzeBody):
        from seo_engine.collectors.marketplaces import (
            MARKETPLACE_COLLECTORS,
            CoupangCollector,
        )
        from seo_engine.models import ProductSnapshot

        cm = body.commerce or {}
        commerce = CommerceInput(
            **{
                k: cm.get(k)
                for k in CommerceInput.__dataclass_fields__
                if k in cm
            }
        )
        try:
            if body.marketplace == "coupang":
                collector = CoupangCollector(
                    mode=body.mode,
                    keyword=body.keyword,
                    mine_title=body.mine_title or "",
                    input_path=body.input_path,
                )
            else:
                cls = MARKETPLACE_COLLECTORS.get(body.marketplace)
                if not cls:
                    raise HTTPException(400, f"unknown marketplace: {body.marketplace}")
                mine = (
                    ProductSnapshot(title=body.mine_title)
                    if body.mine_title
                    else None
                )
                collector = cls(
                    keyword=body.keyword, mine=mine, path=body.input_path
                )
            bundle, result, report = run_commerce(
                collector, commerce=commerce, save=body.save
            )
        except Exception as e:
            report_error("api.analyze", e, recoverable=True)
            raise HTTPException(500, str(e)) from e
        return {
            "report": report,
            "result": result.to_dict(),
            "bundle": {
                "keyword": bundle.keyword,
                "marketplace": bundle.marketplace,
                "product_id": bundle.mine.product_id,
                "title": bundle.mine.title,
            },
        }

    @app.post("/execution/approve")
    def approve(body: ApproveBody):
        from commerce_ai.models import ExecutionPlan, ExecutionStep

        c = get_container()
        steps = [
            ExecutionStep(**s) if isinstance(s, dict) else s
            for s in (body.plan.get("steps") or [])
        ]
        plan = ExecutionPlan(
            plan_id=body.plan.get("plan_id") or body.plan_id,
            product_id=body.plan.get("product_id", ""),
            marketplace=body.plan.get("marketplace", "coupang"),
            keyword=body.plan.get("keyword", ""),
            steps=steps,
            created_at=body.plan.get("created_at", ""),
            notes=body.plan.get("notes", ""),
        )
        try:
            assert c.execution is not None
            step = c.execution.approve_step(
                plan, body.step_id, execute=body.execute
            )
        except KeyError as e:
            raise HTTPException(404, str(e)) from e
        except Exception as e:
            report_error("api.execution", e, recoverable=True)
            raise HTTPException(500, str(e)) from e
        return {"step": step.to_dict(), "plan": plan.to_dict()}

    @app.get("/execution/plan/{product_id}")
    def execution_plan_for_product(product_id: str):
        """Latest pending actions for a product from snapshots (no auto mutate)."""
        from commerce_ai.batch_ops import load_recent_snapshots

        snaps = [
            s
            for s in load_recent_snapshots(1000)
            if str(s.get("product_id")) == product_id
        ]
        if not snaps:
            raise HTTPException(404, "no snapshot for product")
        last = snaps[-1]
        return {
            "product_id": product_id,
            "plan_id": last.get("plan_id"),
            "title": last.get("title"),
            "recommendations": last.get("recommendations") or [],
            "notes": "승인 후 /execution/approve 로 실행 (기본 dry-run)",
        }

    @app.post("/verification/checkpoint")
    def checkpoint(body: VerifyBody):
        c = get_container()
        assert c.verification is not None
        snap = VerificationSnapshot(
            day=body.day,
            rank=body.rank,
            ctr=body.ctr,
            cvr=body.cvr,
            revenue=body.revenue,
            profit=body.profit,
            roas=body.roas,
            impressions=body.impressions,
            conversions=body.conversions,
        )
        result = c.verification.record_checkpoint(
            body.recommendation_id,
            body.day,
            snap,
            mark_final=body.mark_final,
            sync_memory=True,
        )
        return {"result": result.to_dict() if result else None}

    class ABBody(BaseModel):
        recommendation_id: str
        metric: str = "CTR"
        value_a: float
        value_b: float
        day: int = 7

    @app.post("/verification/ab")
    def verification_ab(body: ABBody):
        """Record A/B outcome → Memory winner (no product mutation)."""
        c = get_container()
        assert c.verification is not None
        return c.verification.record_ab_result(
            body.recommendation_id,
            metric=body.metric,
            value_a=body.value_a,
            value_b=body.value_b,
            day=body.day,
            sync_memory=True,
        )

    return app


app = create_app() if FastAPI is not None else None


def main(host: str = "127.0.0.1", port: int = 8088) -> None:
    if FastAPI is None:
        print("pip install fastapi uvicorn")
        raise SystemExit(1)
    import uvicorn

    uvicorn.run(app, host=host, port=port, reload=False)


def main_web() -> None:
    """Operations center on :3000 — http://localhost:3000/md"""
    main(host="127.0.0.1", port=3000)


if __name__ == "__main__":
    main_web()
