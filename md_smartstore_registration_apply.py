# -*- coding: utf-8 -*-
"""스마트스토어 등록정보(브랜드·태그) CDP 반영."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from md_smartstore_cdp import (
    apply_tags_via_edit,
    attach_dialog_handler,
    cleanup_cdp_tabs,
    get_work_page,
    search_product_exists,
)
from md_smartstore_reg_common import CDP, find_excel, load_selling_rows, tag_batch_failed_ids

BASE = Path(__file__).parent
LOG_PATH = BASE / f"smartstore_reg_apply_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"


def log_event(data: dict) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["tags", "check"], default="tags")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--start", type=int, default=0, help="0-based offset")
    parser.add_argument("--product-id", action="append", dest="product_ids")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--retry-failed", action="store_true", help="30건 배치 실패 17건 재시도")
    parser.add_argument("--extra-tags", default="", help="쉼표 구분 추가 태그")
    args = parser.parse_args()

    rows = load_selling_rows(find_excel())
    if args.retry_failed:
        idset = set(tag_batch_failed_ids(30))
        rows = [r for r in rows if r["product_id"] in idset]
    elif args.product_ids:
        idset = set(args.product_ids)
        rows = [r for r in rows if r["product_id"] in idset]
    else:
        rows = rows[args.start :]
        if args.limit:
            rows = rows[: args.limit]

    extra = [t.strip() for t in args.extra_tags.split(",") if t.strip()]
    print(f"대상 {len(rows)}건 | 로그: {LOG_PATH.name}")

    cleanup_cdp_tabs()
    ok = fail = 0
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(CDP, timeout=60000)
        page = get_work_page(browser)
        attach_dialog_handler(page)

        for i, row in enumerate(rows, 1):
            if args.mode == "check":
                exists = search_product_exists(page, row["product_id"])
                res = {"product_id": row["product_id"], "name": row["name"][:50], "exists": exists}
                log_event({"phase": "check", **res})
                print(f"[{i}/{len(rows)}] {row['product_id']} {'FOUND' if exists else 'MISSING'}")
                ok += int(exists)
                fail += int(not exists)
                continue

            res = apply_tags_via_edit(page, row, dry_run=args.dry_run, extra_tags=extra or None)
            log_event({"phase": "tags", **res})
            mark = "OK" if res.get("ok") else res.get("error", res.get("steps"))
            print(f"[{i}/{len(rows)}] {row['product_id']} {mark}")
            ok += int(res.get("ok", False))
            fail += int(not res.get("ok", False))

    print(f"완료: 성공 {ok} / 실패 {fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
