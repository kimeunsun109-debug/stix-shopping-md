# -*- coding: utf-8
import json, time
from playwright.sync_api import sync_playwright

URL = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify?vendorInventoryId=16020715295"
with sync_playwright() as pw:
    page = pw.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=120000)
    time.sleep(6)
    data = page.evaluate("""() => {
      const cells = [...document.querySelectorAll('.option-pane-table-cell')];
      return {
        count: cells.length,
        rows: cells.map(c => (c.innerText||'').slice(0,120)),
        has110: cells.some(c => (c.innerText||'').includes('110ml')),
        bodyHasOption: (document.body.innerText||'').includes('옵션 목록')
      };
    }""")
    json.dump(data, open("item_winner/_diag_p3_rows.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
    page.close()
print(json.dumps(data, ensure_ascii=False))
