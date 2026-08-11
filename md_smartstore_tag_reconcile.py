# -*- coding: utf-8 -*-
"""30건 테스트 배치 실패 17건 — CSV vs 스토어 검색 대조."""
from __future__ import annotations

import argparse
import urllib.request
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from md_smartstore_cdp import attach_dialog_handler, cleanup_cdp_tabs, get_work_page, search_product_exists
from md_smartstore_reg_common import CDP, TAG_BATCH_SUCCESS_IDS, find_excel, load_selling_rows

BASE = Path(__file__).parent
SUCCESS_IDS = TAG_BATCH_SUCCESS_IDS


def cdp_alive() -> bool:
    try:
        with urllib.request.urlopen(f"{CDP}/json/version", timeout=2) as r:
            return bool(r.read())
    except Exception:
        return False


def first_batch_ids(limit: int = 30) -> list[str]:
    rows = load_selling_rows(find_excel())
    return [r["product_id"] for r in rows[:limit]]


def reconcile_offline(batch_ids: list[str]) -> list[dict]:
    rows = {r["product_id"]: r for r in load_selling_rows(find_excel())}
    out = []
    for pid in batch_ids:
        r = rows.get(pid, {})
        out.append(
            {
                "product_id": pid,
                "name": r.get("name", ""),
                "brand": r.get("brand", ""),
                "category": r.get("category", ""),
                "prior_success": pid in SUCCESS_IDS,
                "store_found": None,
                "note": "",
            }
        )
    return out


def reconcile_live(items: list[dict]) -> list[dict]:
    cleanup_cdp_tabs()
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(CDP, timeout=60000)
        page = get_work_page(browser)
        attach_dialog_handler(page)
        for item in items:
            item["store_found"] = search_product_exists(page, item["product_id"])
            if item["prior_success"]:
                item["note"] = "이전 태그 반영 성공"
            elif item["store_found"]:
                item["note"] = "스토어 존재 — 태그 미반영(재시도 필요)"
            else:
                item["note"] = "스토어 검색 없음 — 엑셀 판매중과 불일치"
    return items


def write_report(items: list[dict], path: Path) -> None:
    failed = [i for i in items if not i.get("prior_success")]
    missing = [i for i in failed if i.get("store_found") is False]
    found_not_done = [i for i in failed if i.get("store_found") is True]

    lines = [
        f"스마트스토어 30건 배치 대조 보고서 — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"CDP 검색: {'실행' if any(i.get('store_found') is not None for i in items) else '미실행(오프라인)'}",
        "",
        f"배치 30건 | 이전 성공 {len(SUCCESS_IDS)} | 이전 실패 {30 - len(SUCCESS_IDS)}",
        f"스토어 미검색: {len(missing)} | 스토어 존재·미반영: {len(found_not_done)}",
        "",
        "=" * 72,
        "[이전 실패 17건]",
    ]
    for i in failed:
        sf = i.get("store_found")
        sf_txt = "있음" if sf else ("없음" if sf is False else "미확인")
        lines += [
            "",
            f"  {i['product_id']} | 스토어:{sf_txt}",
            f"    {i['name'][:60]}",
            f"    {i.get('note','')}",
        ]

    lines += ["", "=" * 72, "[전체 30건 요약]"]
    for i in items:
        tag = "성공" if i["prior_success"] else "실패"
        sf = i.get("store_found")
        sf_txt = "O" if sf else ("X" if sf is False else "?")
        lines.append(f"  {i['product_id']} | {tag} | 스토어:{sf_txt} | {i['name'][:40]}")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="CDP로 스토어 검색 실행")
    args = parser.parse_args()

    batch = first_batch_ids(30)
    items = reconcile_offline(batch)
    if args.live and cdp_alive():
        items = reconcile_live(items)
    else:
        for i in items:
            if i["prior_success"]:
                i["note"] = "이전 태그 반영 성공"
            else:
                i["note"] = "이전 자동화 실패 — CDP --live 로 재확인"

    out = BASE / f"MD_스마트스토어_30건대조_{datetime.now().strftime('%Y%m%d')}.txt"
    write_report(items, out)
    print(f"저장: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
