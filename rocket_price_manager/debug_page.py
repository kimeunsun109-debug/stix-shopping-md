# -*- coding: utf-8
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify?vendorInventoryId=16020715295"

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with sync_playwright() as p:
        page = p.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        page.goto(URL, timeout=120000)
        page.wait_for_timeout(15000)
        data = page.evaluate("""() => {
            const tabs = [...document.querySelectorAll('[class*=tab], .tab-view-header *, nav *')]
                .map(e => ({tag:e.tagName, text:(e.innerText||'').trim().slice(0,40), cls:(e.className||'').toString().slice(0,60)}))
                .filter(x => x.text && x.text.length < 40);
            const all = [...document.body.innerText.matchAll(/옵션[^\\n]{0,20}/g)].map(m => m[0]);
            return { url: location.href, tabs: tabs.slice(0,40), matches: all.slice(0,20), bodyStart: document.body.innerText.slice(0,2000) };
        }""")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        page.close()

if __name__ == "__main__":
    main()
