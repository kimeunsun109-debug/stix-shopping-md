# -*- coding: utf-8
import json, sys
from playwright.sync_api import sync_playwright
URL = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify?vendorInventoryId=16020715295"

def snap(page):
    return page.evaluate("""() => {
        return [...document.querySelectorAll('input')].filter(i => {
            const v = (i.value||'').replace(/,/g,'');
            return /^[0-9]+$/.test(v) && parseInt(v) >= 10000;
        }).map(i => ({v:i.value, d:i.disabled, vis:i.offsetWidth>0,
            near:(i.closest('[class*=row]')||i.parentElement?.parentElement)?.innerText?.replace(/\\s+/g,' ').slice(0,100)||''}));
    }""")

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with sync_playwright() as p:
        page = p.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        page.goto(URL, timeout=120000)
        page.wait_for_timeout(15000)
        page.locator(".option-pane-table-row").first.scroll_into_view_if_needed()
        print("before:", json.dumps(snap(page), ensure_ascii=False))

        # click first 수정 in option table body (like successful run)
        page.evaluate("""() => {
            const body = document.querySelector('.option-pane-table-body');
            const mod = body ? [...body.querySelectorAll('*')].find(e => (e.innerText||'').trim()==='수정') : null;
            if (mod) mod.click();
        }""")
        for sec in [2,5,8]:
            page.wait_for_timeout(sec*1000)
            print(f"after {sec}s:", json.dumps(snap(page), ensure_ascii=False))

        # try 110ml row modify
        page.evaluate("""() => {
            const rows = [...document.querySelectorAll('.option-pane-table-row')];
            const row = rows.find(r => r.innerText.includes('110ml × 2개'));
            const mod = row ? [...row.querySelectorAll('*')].find(e => (e.innerText||'').trim()==='수정') : null;
            if (mod) mod.click();
        }""")
        page.wait_for_timeout(5000)
        print("after 110 modify:", json.dumps(snap(page), ensure_ascii=False))
        page.screenshot(path="probe_results/edit_state.png", full_page=True)
        page.close()
main()
