# -*- coding: utf-8
"""110ml×2 옵션 DOM 구조 프로브."""
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
        page.wait_for_timeout(15000)

        data = page.evaluate(
            """() => {
            const result = { inputs: [], labels: [], buttons: [], sections: [] };

            // all sc-common-input with context
            document.querySelectorAll('input.sc-common-input').forEach((inp, idx) => {
                let ctx = '';
                let p = inp;
                for (let d = 0; d < 8; d++) {
                    p = p.parentElement;
                    if (!p) break;
                    const t = (p.innerText || '').replace(/\\s+/g, ' ').trim();
                    if (t.length > 20 && t.length < 300) { ctx = t; break; }
                }
                result.inputs.push({
                    idx, val: inp.value, disabled: inp.disabled, readonly: inp.readOnly,
                    visible: inp.offsetWidth > 0, ctx: ctx.slice(0, 200)
                });
            });

            // elements containing 110ml × 2
            document.querySelectorAll('*').forEach(el => {
                const t = (el.innerText || '').replace(/\\s+/g, ' ').trim();
                if (t.includes('110ml') && t.includes('2개') && t.length < 400 && el.children.length < 8) {
                    result.labels.push({
                        tag: el.tagName,
                        cls: (el.className || '').toString().slice(0, 80),
                        text: t.slice(0, 200)
                    });
                }
            });

            // buttons/links with 수정
            document.querySelectorAll('button, a, span[role=button]').forEach(el => {
                const t = (el.innerText || '').trim();
                if (t === '수정' || t.includes('수정')) {
                    let row = '';
                    let p = el;
                    for (let d = 0; d < 10; d++) {
                        p = p.parentElement;
                        if (!p) break;
                        const rt = (p.innerText || '').replace(/\\s+/g, ' ').trim();
                        if (rt.length > 30 && rt.length < 500) { row = rt; break; }
                    }
                    result.buttons.push({
                        tag: el.tagName, text: t.slice(0, 40),
                        cls: (el.className || '').toString().slice(0, 80),
                        row: row.slice(0, 250)
                    });
                }
            });

            // item winner section
            document.querySelectorAll('[class*=item], [class*=winner], [class*=Item]').forEach(el => {
                const t = (el.innerText || '').replace(/\\s+/g, ' ').trim();
                if (/110ml|아이템|위너|13,?[89]00|13,?200/.test(t) && t.length < 600) {
                    result.sections.push({ cls: (el.className||'').toString().slice(0,80), text: t.slice(0,400) });
                }
            });

            return result;
        }"""
        )

        print(json.dumps(data, ensure_ascii=False, indent=2))
        (OUT / "probe_110x2_dom.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        page.screenshot(path=str(OUT / "probe_110x2_page.png"), full_page=True)
        page.close()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
