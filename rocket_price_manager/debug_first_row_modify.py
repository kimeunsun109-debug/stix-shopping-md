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
        # first row modify (15ml)
        page.evaluate("""() => {
            const row = document.querySelector('.option-pane-table-row');
            const mod = [...row.querySelectorAll('*')].find(e => (e.innerText||'').trim()==='수정');
            if (mod) mod.click();
        }""")
        page.wait_for_timeout(3000)
        data = page.evaluate("""(label) => {
            const row = [...document.querySelectorAll('.option-pane-table-row')]
                .find(r => (r.innerText||'').includes(label));
            return {
                targetRowInputs: row ? [...row.querySelectorAll('input')].map(i=>({v:i.value,d:i.disabled})) : [],
                enabled13900: [...document.querySelectorAll('input')].filter(i=>i.value.replace(/,/g,'')==='13900').map(i=>({v:i.value,d:i.disabled})),
                overlay: (document.querySelector('[data-layer=\"modalView\"]')||{}).innerText?.replace(/\\s+/g,' ').slice(0,300)||null
            };
        }""", LABEL)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        page.close()
main()
