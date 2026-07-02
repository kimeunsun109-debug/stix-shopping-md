# -*- coding: utf-8
"""modify 페이지 옵션별 가격 탭 프로브."""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = (
    "https://wing.coupang.com/tenants/seller-web/"
    "vendor-inventory/modify?vendorInventoryId=16020715295"
)
OUT = Path(__file__).resolve().parent / "probe_results"


def main():
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        page = p.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        page.goto(URL, timeout=120000)
        page.wait_for_timeout(10000)

        # 옵션별 가격 탭 클릭
        tab = page.locator("text=옵션별 가격").first
        if tab.count():
            tab.click()
            page.wait_for_timeout(8000)

        data = page.evaluate(
            """() => {
            const inputs = [...document.querySelectorAll('input.sc-common-input')].map((inp, idx) => {
                let ctx = '';
                let p = inp;
                for (let d = 0; d < 10; d++) {
                    p = p.parentElement;
                    if (!p) break;
                    const t = (p.innerText||'').replace(/\\s+/g,' ').trim();
                    if (t.length > 15 && t.length < 250) { ctx = t; break; }
                }
                return {
                    idx, val: inp.value, disabled: inp.disabled,
                    visible: inp.offsetWidth > 0, ctx: ctx.slice(0, 180)
                };
            }).filter(x => /^[0-9,]+$/.test((x.val||'').replace(/,/g,'')) && parseInt(x.val.replace(/,/g,'')) >= 1000);

            const rows = [];
            document.querySelectorAll('tr').forEach(tr => {
                const t = (tr.innerText||'').replace(/\\s+/g,' ').trim();
                if (/110ml|판매가|15ml/.test(t) && t.length < 300) rows.push(t);
            });
            return { inputs, rows: rows.slice(0, 20) };
        }"""
        )
        print(json.dumps(data, ensure_ascii=False, indent=2))
        (OUT / "probe_option_price_tab.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        page.screenshot(path=str(OUT / "probe_option_price_tab.png"), full_page=True)
        page.close()


if __name__ == "__main__":
    main()
