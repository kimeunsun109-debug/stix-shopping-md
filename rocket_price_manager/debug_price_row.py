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
        data = page.evaluate("""() => {
            const hits = [];
            document.querySelectorAll('*').forEach(el => {
                const t = (el.innerText||'').replace(/\\s+/g,' ').trim();
                if (t.includes('110ml × 2개') && t.includes('13,900') && t.length < 250 && el.children.length < 15) {
                    const mod = [...el.querySelectorAll('a,button,span')].filter(x => (x.innerText||'').trim()==='수정');
                    hits.push({tag:el.tagName, cls:(el.className||'').toString().slice(0,80), text:t, mods:mod.length});
                }
            });
            const body = document.body.innerText;
            const idx = body.indexOf('110ml × 2개');
            return { hits, snippet: body.slice(Math.max(0,idx-20), idx+200).replace(/\\n/g,' | ') };
        }""")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        page.close()
if __name__ == '__main__': main()
