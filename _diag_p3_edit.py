# -*- coding: utf-8
import json, time
from playwright.sync_api import sync_playwright
from item_winner.wing_apply import _click_option_edit, _dismiss_modals

URL = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify?vendorInventoryId=16020715295"
with sync_playwright() as pw:
    page = pw.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=120000)
    time.sleep(5)
    _dismiss_modals(page)
    ok = _click_option_edit(page, "110mlx2")
    time.sleep(2)
    data = page.evaluate("""() => {
      const cells = [...document.querySelectorAll('.option-pane-table-cell')];
      const inputs = [...document.querySelectorAll('input[type=text]')].filter(i => !i.disabled)
        .map(i => ({v: i.value, ctx: (i.closest('.option-pane-table-cell')?.innerText||'').slice(0,40)}));
      return {clicked: true, inputs: inputs.filter(x => /\\d/.test(x.v)).slice(0,20)};
    }""")
    data["click_ok"] = ok
    json.dump(data, open("item_winner/_diag_p3_edit.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
    page.close()
