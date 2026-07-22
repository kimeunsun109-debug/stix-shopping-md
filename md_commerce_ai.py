# -*- coding: utf-8 -*-
"""
STIX Commerce AI v7.0 CLI — AI MD Autonomous Operation Mode
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _commerce_from_args(args, data: dict | None = None):
    from commerce_ai.models import CommerceInput

    data = data or {}
    cm = data.get("commerce") or data.get("metrics") or {}

    def pick(*keys, cast=None, default=None):
        for k in keys:
            attr = k.replace("-", "_")
            if hasattr(args, attr):
                v = getattr(args, attr, None)
                if v is not None:
                    return cast(v) if cast else v
            if k in cm and cm[k] is not None:
                return cast(cm[k]) if cast else cm[k]
        return default

    return CommerceInput(
        revenue=pick("revenue", cast=int),
        profit=pick("profit", cast=int),
        cost=pick("cost", cast=int),
        units_sold=pick("units_sold", "units", cast=int),
        impressions=pick("impressions", cast=int),
        ctr=pick("ctr", cast=float),
        cvr=pick("cvr", cast=float),
        roas=pick("roas", cast=float),
        ad_spend=pick("ad_spend", cast=int),
        stock=pick("stock", cast=int),
        rank=pick("rank", cast=int),
        rank_yesterday=pick("rank_yesterday", cast=int),
        ctr_yesterday=pick("ctr_yesterday", cast=float),
        cvr_yesterday=pick("cvr_yesterday", cast=float),
    )


def main() -> int:
    p = argparse.ArgumentParser(description="STIX Commerce AI v7.0 — AI MD Autonomous")
    p.add_argument("--mode", choices=["cdp", "manual", "auto"], default="manual")
    p.add_argument(
        "--marketplace",
        default="coupang",
        choices=["coupang", "smartstore", "gmarket", "auction", "11st", "amazon"],
    )
    p.add_argument("--keyword", default="")
    p.add_argument("--input", default="")
    p.add_argument("--mine-title", default="")
    p.add_argument("--mine-url", default="")
    p.add_argument("--mine-brand", default="")
    p.add_argument("--cdp-port", type=int, default=0)
    p.add_argument("--titles", type=int, default=8)
    p.add_argument("--revenue", type=int, default=None)
    p.add_argument("--profit", type=int, default=None)
    p.add_argument("--cost", type=int, default=None)
    p.add_argument("--units-sold", type=int, default=None)
    p.add_argument("--impressions", type=int, default=None)
    p.add_argument("--ctr", type=float, default=None)
    p.add_argument("--cvr", type=float, default=None)
    p.add_argument("--roas", type=float, default=None)
    p.add_argument("--stock", type=int, default=None)
    p.add_argument("--rank", type=int, default=None)
    p.add_argument("--rank-yesterday", type=int, default=None)
    p.add_argument("--ctr-yesterday", type=float, default=None)
    p.add_argument("--cvr-yesterday", type=float, default=None)
    p.add_argument("--no-save", action="store_true")
    p.add_argument("--out", default="")
    p.add_argument("--dashboard", action="store_true")
    p.add_argument("--monitor", action="store_true")
    p.add_argument("--check-learning", action="store_true")
    p.add_argument("--check-verification", action="store_true")
    p.add_argument("--api", action="store_true", help="start REST API :8088")
    p.add_argument(
        "--web",
        action="store_true",
        help="start Operations Center http://localhost:3000/md",
    )
    p.add_argument(
        "--batch",
        type=int,
        nargs="?",
        const=100,
        default=None,
        help="batch-analyze N real catalog products (default 100)",
    )
    p.add_argument(
        "--schedule",
        action="store_true",
        help="run daily scheduler (08:00), optional --now",
    )
    p.add_argument(
        "--now",
        action="store_true",
        help="with --schedule: run one job immediately",
    )
    p.add_argument("--daily-report", action="store_true", help="AI MD Daily Report")
    p.add_argument("--weekly-report", action="store_true")
    p.add_argument("--monthly-report", action="store_true")
    p.add_argument(
        "--autonomous",
        action="store_true",
        help="run AI MD autonomous daily (use --batch N to include scan)",
    )
    p.add_argument("--catalog-stats", action="store_true")
    p.add_argument("--test", action="store_true", help="run unit tests")
    args = p.parse_args()

    if args.test:
        import unittest

        result = unittest.main(
            module=None,
            argv=["", "discover", "-s", "commerce_ai/tests", "-v"],
            exit=False,
        )
        return 0 if result.result.wasSuccessful() else 1

    if args.catalog_stats:
        from commerce_ai.ops_catalog import catalog_stats

        print(json.dumps(catalog_stats(), ensure_ascii=False, indent=2))
        return 0

    if args.daily_report:
        from commerce_ai.reports import ReportEngine

        r = ReportEngine().build_daily(save=True)
        print(r.text)
        return 0

    if args.weekly_report:
        from commerce_ai.reports import ReportEngine

        print(ReportEngine().build_weekly(save=True)["text"])
        return 0

    if args.monthly_report:
        from commerce_ai.reports import ReportEngine

        print(ReportEngine().build_monthly(save=True)["text"])
        return 0

    if args.autonomous:
        from commerce_ai.autonomous import run_autonomous_daily

        limit = int(args.batch) if args.batch is not None else 100
        result = run_autonomous_daily(
            batch_limit=limit, skip_batch=(args.batch is None)
        )
        print(result.get("daily_report_text") or "")
        print(f"\nboard: {result.get('board_path')}")
        return 0

    if args.batch is not None:
        from commerce_ai.batch_ops import run_batch

        summary = run_batch(limit=int(args.batch))
        print(json.dumps({k: v for k, v in summary.items() if k != "top_must_do"}, ensure_ascii=False, indent=2))
        print(f"\nreport: {summary.get('report_path')}")
        print(f"snapshots: {summary.get('snapshots_path')}")
        return 0

    if args.schedule:
        from commerce_ai.scheduler import run_forever

        run_forever(hour=8, minute=0, limit=100, now=args.now)
        return 0

    if args.web:
        from commerce_ai.api import main_web

        print("Operations Center: http://localhost:3000/md")
        main_web()
        return 0

    if args.api:
        from commerce_ai.api import main as api_main

        api_main()
        return 0

    if args.monitor:
        from commerce_ai.monitoring import SystemMonitor

        print(SystemMonitor().format_text())
        return 0

    if args.dashboard:
        from commerce_ai.dashboard import CommerceDashboard

        print(CommerceDashboard().format_text())
        return 0

    if args.check_verification:
        from commerce_ai.container import get_container

        c = get_container()
        assert c.verification is not None
        due = c.verification.due()
        metrics = c.verification.aggregate_metrics()
        print(
            f"success={metrics.success_rate} fail={metrics.fail_rate} "
            f"avgCTR={metrics.avg_ctr_delta_pct} avgCVR={metrics.avg_cvr_delta_pct}"
        )
        if not due:
            print("no verification checkpoints due")
            return 0
        for d in due:
            print(
                f"VERIFY D+{d.get('dueDays')} | {d.get('product_id')} | "
                f"{d.get('action')} | {d.get('recommendation_id')}"
            )
        return 0

    if args.check_learning:
        from commerce_ai.learning import CommerceLearningEngine

        due = CommerceLearningEngine().due_checkpoints()
        if not due:
            print("no learning checkpoints due")
            return 0
        for d in due:
            print(f"DUE {d.get('dueDays')}d | {d.get('productId')} | {d.get('actions')}")
        return 0

    from commerce_ai.pipeline import run_commerce
    from commerce_ai.stability.logging_setup import setup_logging

    setup_logging()

    data = {}
    if args.input and args.input.lower().endswith(".json"):
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))

    commerce = _commerce_from_args(args, data)

    if args.marketplace == "coupang":
        from seo_engine.collectors.marketplaces import CoupangCollector

        collector = CoupangCollector(
            mode=args.mode,
            keyword=args.keyword or data.get("keyword", ""),
            mine_url=args.mine_url,
            mine_title=args.mine_title,
            mine_brand=args.mine_brand,
            input_path=args.input or None,
            cdp_port=args.cdp_port,
        )
    else:
        from seo_engine.collectors.marketplaces import MARKETPLACE_COLLECTORS
        from seo_engine.models import ProductSnapshot

        cls = MARKETPLACE_COLLECTORS[args.marketplace]
        mine = None
        if args.mine_title or args.mine_url:
            mine = ProductSnapshot(
                title=args.mine_title, brand=args.mine_brand, url=args.mine_url
            )
        collector = cls(
            keyword=args.keyword or data.get("keyword", ""),
            mine=mine,
            path=args.input or None,
        )

    out = args.out
    if not out:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = str(ROOT / f"COMMERCE_AI_{stamp}.txt")

    try:
        _b, _r, report = run_commerce(
            collector,
            commerce=commerce,
            save=not args.no_save,
            report_path=out,
            title_variants=max(5, min(10, args.titles)),
        )
    except Exception as e:
        from commerce_ai.stability.errors import report_error

        report_error("cli", e, recoverable=False)
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    print(report)
    print(f"\nreport saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
