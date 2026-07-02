# -*- coding: utf-8
import json, sys
from playwright.sync_api import sync_playwright
URL = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify?vendorInventoryId=16020715295"
LABEL = "110ml × 2개"

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with sync_playwright() as p:
        page = p.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        page.goto(URL, timeout=120000)
        page.wait_for_timeout(15000)
        page.locator(".option-pane-table-row").first.scroll_into_view_if_needed()

        mods = page.evaluate("""(label) => {
            const row = [...document.querySelectorAll('.option-pane-table-row')]
                .find(r => (r.innerText||'').includes(label));
            if (!row) return [];
            return [...row.querySelectorAll('a,button,span')].filter(e => (e.innerText||'').trim()==='수정')
                .map((el,i) => ({
                    i,
                    tag: el.tagName,
                    cls: (el.className||'').toString().slice(0,100),
                    parent: (el.parentElement?.innerText||'').replace(/\\s+/g,' ').slice(0,120)
                }));
        }""", LABEL)
        print("mods:", json.dumps(mods, ensure_ascii=False, indent=2))

        for idx in range(len(mods)):
            page.goto(URL, timeout=120000)
            page.wait_for_timeout(12000)
            page.locator(".option-pane-table-row").first.scroll_into_view_if_needed()
            page.evaluate("""([label, idx]) => {
                const row = [...document.querySelectorAll('.option-pane-table-row')]
                    .find(r => (r.innerText||'').includes(label));
                const mods = row ? [...row.querySelectorAll('a,button,span')]
                    .filter(e => (e.innerText||'').trim()==='수정') : [];
                if (mods[idx]) mods[idx].click();
            }""", [LABEL, idx])
            page.wait_for_timeout(4000)
            state = page.evaluate("""() => {
                const en = [...document.querySelectorAll('input')].filter(i => !i.disabled && /^[0-9,]+$/.test(i.value) && parseInt(i.value.replace(/,/g,''))>=10000);
                return { idx: en.length, vals: en.map(i=>i.value) };
            }""")
            print(f"click mod[{idx}] -> enabled:", state)
        page.close()
main()
