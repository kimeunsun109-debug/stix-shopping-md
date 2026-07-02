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
            for (const row of document.querySelectorAll('.option-pane-table-row')) {
                if ((row.innerText||'').includes(label)) {
                    row.scrollIntoView({block:'center'});
                    const mod = [...row.querySelectorAll('*')].find(e => (e.innerText||'').trim()==='수정');
                    if (mod) mod.click();
                    break;
                }
            }
        }""", LABEL)
        page.wait_for_timeout(3000)
        data = page.evaluate("""() => {
            const modal = document.querySelector('[data-layer=\"modalView\"]');
            const row = [...document.querySelectorAll('.option-pane-table-row')]
                .find(r => r.innerText.includes('110ml × 2개') && r.innerText.includes('13'));
            return {
                modalText: modal ? modal.innerText.replace(/\\s+/g,' ').slice(0,500) : null,
                rowText: row ? row.innerText.replace(/\\s+/g,' ').slice(0,300) : null,
                rowInputs: row ? [...row.querySelectorAll('input')].map(i=>({v:i.value, dis:i.disabled})) : [],
                modalInputs: modal ? [...modal.querySelectorAll('input')].map(i=>({v:i.value, dis:i.disabled})) : [],
                rowBtns: row ? [...row.querySelectorAll('button,a')].map(b=>b.innerText.trim()).filter(Boolean) : [],
                modalBtns: modal ? [...modal.querySelectorAll('button,a')].map(b=>b.innerText.trim()).filter(Boolean) : [],
            };
        }""")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        page.screenshot(path="probe_results/after_modify_click.png")
        page.close()
main()
