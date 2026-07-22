# -*- coding: utf-8 -*-
"""
Daily Ranking Monitor CLI

예)
  python md_seo_rank_monitor.py --product-id demo-stix-001 --keyword 보석십자수 --rank 11
  python md_seo_rank_monitor.py --product-id demo-stix-001 --keyword 보석십자수 --rank 11 --auto-recover --input seo_engine/samples/...
"""
from __future__ import annotations

import argparse
import sys
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
    p = argparse.ArgumentParser(description="SEO Ranking Monitor")
    p.add_argument("--product-id", required=True)
    p.add_argument("--keyword", required=True)
    p.add_argument("--rank", type=int, required=True)
    p.add_argument("--title", default="")
    p.add_argument("--auto-recover", action="store_true", help="하락 감지 시 Recovery 실행")
    p.add_argument("--input", default="", help="auto-recover 시 Mode B 입력")
    p.add_argument("--mine-title", default="")
    p.add_argument("--threshold", type=int, default=3, help="하락 N위 이상이면 알림")
    args = p.parse_args()

    from seo_engine.engines.ranking import RankingMonitor

    mon = RankingMonitor()
    # temporarily use threshold via detect after record
    result = mon.record(
        product_id=args.product_id,
        keyword=args.keyword,
        rank=args.rank,
        title=args.title,
        source="monitor",
    )
    print(f"저장: {result['path']}")
    print(f"기록: {result['record']}")

    alert = result.get("alert")
    # re-check with custom threshold
    hist = mon.latest(args.product_id, args.keyword)
    alert = mon.detect_drop(hist, threshold=args.threshold) or alert

    if not alert:
        print("순위 하락 없음")
        return 0

    print(f"[ALERT] {alert['message']}")
    if not args.auto_recover:
        print("자동 분석: --auto-recover --input ... 로 실행")
        return 0

    from seo_engine.collectors import ManualCollector
    from seo_engine.models import ProductSnapshot
    from seo_engine.pipeline import run_recovery

    mine = ProductSnapshot(
        title=args.mine_title or args.title or args.keyword,
        product_id=args.product_id,
    )
    collector = ManualCollector(
        keyword=args.keyword,
        mine=mine if not args.input else None,
        path=args.input or None,
    )
    out = ROOT / f"SEO_RECOVERY_auto_{args.product_id}.txt"
    _b, _r, report = run_recovery(
        collector,
        save=True,
        rank_before=alert.get("rankBefore"),
        rank_after=alert.get("rankAfter"),
        report_path=out,
    )
    print(report)
    print(f"리포트: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
