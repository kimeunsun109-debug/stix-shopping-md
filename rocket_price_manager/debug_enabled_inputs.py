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
        page.evaluate("""(label) => {
            const row = [...document.querySelectorAll('.option-pane-table-row')]
                .find(r => (r.innerText||'').includes(label));
            const btn = row ? [...row.querySelectorAll('button')].find(b => (b.innerText||'').trim()==='수정') : null;
            if (btn) btn.click();
        }""", LABEL)
        page.wait_for_timeout(3000)
        data = page.evaluate("""() => {
            return [...document.querySelectorAll('input')].filter(i => !i.disabled && /^[0-9,]+$/.test(i.value))
                .map(i => ({
                    v: i.value,
                    cls: i.className,
                    near: (i.closest('.option-pane-table-row')||i.parentElement?.parentElement?.parentElement)?.innerText?.replace(/\\s+/g,' ').slice(0,100)||''
                }));
        }""")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        saves = page.evaluate("""() => [...document.querySelectorAll('button.sc-common-btn')]
            .map(b=>({t:b.innerText.trim(), vis:b.offsetWidth>0, rect:b.getBoundingClientRect()}))
            .filter(x=>x.t==='저장')""")
        print("saves:", json.dumps(saves, ensure_ascii=False, indent=2))
        page.close()
main()
