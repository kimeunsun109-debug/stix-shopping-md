# -*- coding: utf-8 -*-
"""
STIX AI - Coupang SEO Recovery Engine v3.0 CLI

Mode: cdp | manual | auto
Marketplace: coupang | smartstore | gmarket | auction | 11st | amazon
"""
from __future__ import annotations

import argparse
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


def main() -> int:
    p = argparse.ArgumentParser(description="SEO Recovery Engine v3.0")
    p.add_argument("--mode", choices=["cdp", "manual", "auto"], default="manual")
    p.add_argument(
        "--marketplace",
        default="coupang",
        choices=["coupang", "smartstore", "gmarket", "auction", "11st", "amazon"],
    )
    p.add_argument("--keyword", default="")
    p.add_argument("--mine-url", default="")
    p.add_argument("--mine-title", default="")
    p.add_argument("--mine-brand", default="")
    p.add_argument("--mine-detail", default="")
    p.add_argument("--input", default="")
    p.add_argument("--competitors", nargs="*", default=[])
    p.add_argument("--reviews", nargs="*", default=[])
    p.add_argument("--top-n", type=int, default=5)
    p.add_argument("--cdp-port", type=int, default=0)
    p.add_argument("--rank-before", type=int, default=None)
    p.add_argument("--rank-after", type=int, default=None)
    p.add_argument("--ctr", type=float, default=None)
    p.add_argument("--cvr", type=float, default=None)
    p.add_argument("--ctr-before", type=float, default=None)
    p.add_argument("--ctr-after", type=float, default=None)
    p.add_argument("--cvr-before", type=float, default=None)
    p.add_argument("--cvr-after", type=float, default=None)
    p.add_argument("--titles", type=int, default=8)
    p.add_argument("--no-save", action="store_true")
    p.add_argument("--out", default="")
    p.add_argument("--check-learning", action="store_true")
    p.add_argument("--dashboard", action="store_true", help="dashboard")
    args = p.parse_args()

    if args.dashboard:
        from seo_engine.engines.dashboard import Dashboard

        print(Dashboard().format_text())
        return 0

    if args.check_learning:
        from seo_engine.engines.learning import SelfLearningEngine

        due = SelfLearningEngine().due_checkpoints()
        if not due:
            print("no learning checkpoints due")
            return 0
        for d in due:
            print(
                f"DUE {d.get('dueDays')}d | {d.get('productId')} | {d.get('keyword')} | "
                f"date {d.get('date')} | rankBefore={d.get('rankBefore')}"
            )
        return 0

    from seo_engine.pipeline import run_recovery as _run

    comps = [{"title": t, "rank": i} for i, t in enumerate(args.competitors, 1)]

    if args.marketplace == "coupang":
        from seo_engine.collectors.marketplaces import CoupangCollector

        collector = CoupangCollector(
            mode=args.mode,
            keyword=args.keyword,
            mine_url=args.mine_url,
            mine_title=args.mine_title,
            mine_brand=args.mine_brand,
            mine_detail=args.mine_detail,
            reviews=list(args.reviews),
            competitors=comps,
            input_path=args.input or None,
            top_n=args.top_n,
            cdp_port=args.cdp_port,
        )
    else:
        from seo_engine.collectors.marketplaces import MARKETPLACE_COLLECTORS
        from seo_engine.models import ProductSnapshot

        cls = MARKETPLACE_COLLECTORS[args.marketplace]
        mine = None
        if args.mine_title or args.mine_url:
            mine = ProductSnapshot(
                title=args.mine_title,
                brand=args.mine_brand,
                detail_text=args.mine_detail,
                url=args.mine_url,
                reviews=list(args.reviews),
            )
        collector = cls(
            keyword=args.keyword,
            mine=mine,
            competitors=comps,
            path=args.input or None,
        )

    out = args.out
    if not out:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = str(ROOT / f"SEO_RECOVERY_{stamp}.txt")

    n_titles = max(5, min(10, args.titles))
    try:
        _bundle, _result, report = _run(
            collector,
            save=not args.no_save,
            rank_before=args.rank_before,
            rank_after=args.rank_after,
            ctr=args.ctr,
            cvr=args.cvr,
            ctr_before=args.ctr_before,
            ctr_after=args.ctr_after,
            cvr_before=args.cvr_before,
            cvr_after=args.cvr_after,
            report_path=out,
            title_variants=n_titles,
        )
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    print(report)
    print(f"\nreport saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
