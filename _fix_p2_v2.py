# -*- coding: utf-8
"""Set option sale price on Wing modify page."""
from __future__ import annotations

import json
import re
import time
from playwright.sync_api import sync_playwright

VENDOR_INVENTORY_ID = "16020715295"
OPTION_KEY = "15ml × 3개"
TARGET = 10290
MODIFY_URL = (
    "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify"
    f"?vendorInventoryId={VENDOR_INVENTORY_ID}"
)


def set_option_price(page, option_key: str, price: int) -> dict:
    page.goto(MODIFY_URL, wait_until="domcontentloaded", timeout=120000)
    time.sleep(5)

    # option table row
    row = page.locator("tr, [class*='option'], [class*='row']").filter(
        has_text=re.compile(re.escape(option_key.split("×")[0].strip()))
    ).filter(has_text=re.compile("3개")).first
    row.scroll_into_view_if_needed(timeout=10000)
    row.get_by_text("수정", exact=True).last.click(timeout=10000)
    time.sleep(2)

    # modal / inline inputs for sale price
    filled = False
    for inp in page.locator("input").all():
        try:
            val = inp.input_value(timeout=500)
            num = val.replace(",", "")
            if num in ("10560", "10,560") or (num.isdigit() and 10000 <= int(num) <= 11000):
                inp.click()
                inp.fill(str(price))
                filled = True
                break
        except Exception:
            continue

    if not filled:
        # try any visible numeric input near 판매가
        page.locator("input").filter(has=page.locator("xpath=..")).first
        for label in ("판매가", "할인"):
            try:
                loc = page.get_by_text(label).locator("xpath=following::input[1]")
                loc.fill(str(price), timeout=3000)
                filled = True
                break
            except Exception:
                pass

    saved = False
    for label in ("저장", "확인", "적용", "수정완료"):
        try:
            page.get_by_role("button", name=re.compile(label)).first.click(timeout=3000)
            time.sleep(2)
            saved = True
        except Exception:
            continue

    # page-level save
    for label in ("수정완료", "저장"):
        try:
            page.get_by_role("button", name=re.compile(label)).first.click(timeout=3000)
            time.sleep(2)
            saved = True
        except Exception:
            pass

    return {"filled": filled, "saved": saved, "url": page.url}


def verify_list_price(page) -> str:
    url = (
        "https://wing.coupang.com/tenants/seller-web/vendor-inventory/list"
        f"?searchKeywordType=ALL&searchKeywords={VENDOR_INVENTORY_ID}&exposureStatus=ALL"
    )
    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    time.sleep(3)
    body = page.evaluate("() => document.body.innerText || ''")
    if "10,290" in body or "10290" in body:
        return "10290"
    if "10,560" in body:
        return "10560"
    m = re.search(r"(\d{1,3}(?:,\d{3})*)원", body[body.find("B7000") : body.find("B7000") + 500] if "B7000" in body else body)
    return m.group(1) if m else "unknown"


def main() -> None:
    result = {}
    with sync_playwright() as pw:
        page = pw.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        result["apply"] = set_option_price(page, OPTION_KEY, TARGET)
        time.sleep(3)
        result["after"] = verify_list_price(page)
        result["ok"] = result["after"] in ("10290", "10,290")
        page.close()
    with open("item_winner/_fix_p2_v2.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
