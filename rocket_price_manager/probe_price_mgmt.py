# -*- coding: utf-8
"""가격관리 페이지에서 B7000 110ml×2 행 탐색."""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = (
    "https://wing.coupang.com/tenants/seller-price-management/"
    "?searchInputValue=B7000&searchInputType=KEYWORD"
)
OUT = Path(__file__).resolve().parent / "probe_results"


def main():
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        page = p.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        page.goto(URL, timeout=120000)
        page.wait_for_timeout(12000)

        body = page.locator("body").inner_text()
        rows = [r.strip() for r in body.split("\n") if "110ml" in r or "110" in r and "ml" in r]
        print("110ml rows:", rows[:20])

        data = page.evaluate(
            """() => {
            const rows = [];
            document.querySelectorAll('tr, [class*=row]').forEach(el => {
                const t = (el.innerText||'').replace(/\\s+/g,' ').trim();
                if (/110ml|110 ml|13,?900|13,?800|13,?200/.test(t) && t.length < 500)
                    rows.push(t);
            });
            const mods = [...document.querySelectorAll('a.ap-action-link')].map(a => ({
                text: a.innerText.trim(),
                row: (a.closest('tr')||a.parentElement?.parentElement)?.innerText?.replace(/\\s+/g,' ').slice(0,300)||''
            }));
            return { rows: [...new Set(rows)], modifyLinks: mods };
        }"""
        )
        print(json.dumps(data, ensure_ascii=False, indent=2))
        (OUT / "probe_price_mgmt_110x2.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        page.screenshot(path=str(OUT / "probe_price_mgmt.png"), full_page=True)
        page.close()


if __name__ == "__main__":
    main()
