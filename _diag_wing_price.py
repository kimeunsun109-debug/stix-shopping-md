# -*- coding: utf-8
"""Diagnose Wing price edit for rocket growth SKU."""
from __future__ import annotations

import json
import re
import time
from playwright.sync_api import sync_playwright

VID = "94705203391"
LIST = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/list"


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9233")
        page = browser.contexts[0].new_page()
        page.goto(LIST, wait_until="domcontentloaded", timeout=120000)
        time.sleep(2)
        try:
            page.get_by_text("초기화", exact=True).first.click(timeout=3000)
            time.sleep(1)
        except Exception:
            pass
        inp = page.locator("input[type='text'], input[type='search']").first
        inp.fill(VID)
        page.keyboard.press("Enter")
        time.sleep(4)

        body = page.evaluate("() => document.body.innerText || ''")
        links = page.evaluate(
            """() => [...document.querySelectorAll('a,button,span')]
            .map(e => ({tag:e.tagName, text:(e.innerText||'').trim().slice(0,60), href:e.href||''}))
            .filter(x => x.text && /수정|가격|판매|edit|price/i.test(x.text))
            .slice(0,40)"""
        )
        html_snip = page.evaluate(
            """() => {
              const rows = [...document.querySelectorAll('tr, [class*="row"], [class*="item"]')];
              return rows.map(r => r.innerText.slice(0,200)).filter(t => /B7000|10560|10,560|94705203391|판매가/.test(t)).slice(0,8);
            }"""
        )
        prices = re.findall(r"(\d{1,3}(?:,\d{3})*)", body[:8000])

        out = {
            "url": page.url,
            "total": re.search(r"총 (\d+)개", body),
            "prices_in_header": prices[:30],
            "row_snips": html_snip,
            "action_links": links,
            "body_snip": body[body.find("B7000") : body.find("B7000") + 1500] if "B7000" in body else body[:2000],
        }
        path = __file__.replace("_diag_wing_price.py", "_tmp_wing_diag.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2, default=str)
        print(path)
        page.close()


if __name__ == "__main__":
    main()
