# -*- coding: utf-8
import json, sys
from playwright.sync_api import sync_playwright

def probe(url, name):
    sys.stdout.reconfigure(encoding="utf-8")
    with sync_playwright() as p:
        page = p.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        page.goto(url, timeout=120000)
        page.wait_for_timeout(12000)
        rows = page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('tr,[class*=row]').forEach(el => {
                const t = (el.innerText||'').replace(/\\s+/g,' ').trim();
                if (/B7000|110ml.*2|13,?900|13,?800/.test(t) && t.length < 400) out.push(t);
            });
            return [...new Set(out)].slice(0,15);
        }""")
        print(name, json.dumps(rows, ensure_ascii=False, indent=2))
        page.close()

if __name__ == '__main__':
    probe("https://wing.coupang.com/tenants/seller-price-management/?searchInputValue=B7000&searchInputType=KEYWORD", "ALL")
    probe("https://wing.coupang.com/tenants/seller-price-management/?searchInputValue=B7000&searchInputType=KEYWORD&itemWinnerStatus=WIN", "WIN")
