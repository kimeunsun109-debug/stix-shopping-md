# -*- coding: utf-8
"""Explore Wing 가격관리 menu."""
import json, time
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    page = pw.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
    page.goto("https://wing.coupang.com/tenants/seller-web/vendor-inventory/list", timeout=120000)
    time.sleep(2)
    # click 가격관리 in sidebar
    try:
        page.get_by_text("가격관리", exact=True).first.click(timeout=5000)
        time.sleep(4)
    except Exception as e:
        pass
    data = page.evaluate("""() => ({
      url: location.href,
      body: (document.body.innerText||'').slice(0,5000),
      links: [...document.querySelectorAll('a')].map(a=>a.href).filter(h=>h.includes('price')||h.includes('Price')).slice(0,20)
    })""")
    json.dump(data, open("_tmp_wing_price_menu.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
    page.close()
print("done")
