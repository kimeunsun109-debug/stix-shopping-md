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
            if (btn) { row.scrollIntoView({block:'center'}); btn.click(); }
        }""", LABEL)
        page.wait_for_timeout(3000)
        data = page.evaluate("""(label) => {
            const row = [...document.querySelectorAll('.option-pane-table-row')]
                .find(r => (r.innerText||'').includes(label));
            return {
                rowHtml: row ? row.innerText.replace(/\\s+/g,' ').slice(0,300) : null,
                rowBtns: row ? [...row.querySelectorAll('button,a')].map(b=>({
                    t:b.innerText.trim(), vis:b.offsetWidth>0, cls:(b.className||'').toString().slice(0,60)
                })) : [],
                rowInputs: row ? [...row.querySelectorAll('input')].map(i=>({v:i.value,d:i.disabled,vis:i.offsetWidth>0})) : [],
            };
        }""", LABEL)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        page.screenshot(path="probe_results/row_edit_mode.png")
        page.close()
main()
