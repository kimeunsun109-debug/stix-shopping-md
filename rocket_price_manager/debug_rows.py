# -*- coding: utf-8
import json, sys
from playwright.sync_api import sync_playwright
URL = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify?vendorInventoryId=16020715295"
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with sync_playwright() as p:
        page = p.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        page.goto(URL, timeout=120000)
        page.wait_for_timeout(15000)
        rows = page.evaluate("""() => [...document.querySelectorAll('tr')]
            .map(tr => (tr.innerText||'').replace(/\\s+/g,' ').trim())
            .filter(t => t.includes('110ml') && t.includes('2개'))""")
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        page.close()
if __name__ == '__main__': main()
