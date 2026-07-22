# -*- coding: utf-8
"""Click Wing row actions and capture edit page."""
import json, re, time
from playwright.sync_api import sync_playwright

VID = "94705203391"
with sync_playwright() as pw:
    page = pw.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
    page.goto("https://wing.coupang.com/tenants/seller-web/vendor-inventory/list", timeout=120000)
    time.sleep(2)
    page.get_by_text("초기화", exact=True).first.click(timeout=3000)
    time.sleep(1)
    page.locator("input[type='text']").first.fill(VID)
    page.keyboard.press("Enter")
    time.sleep(4)
    before = page.evaluate("() => document.body.innerText.slice(0,5000)")
    # try 판매가 column inline edit or dropdown
    clicked = False
    for label in ["판매가", "가격 수정", "판매가 수정", "수정"]:
        try:
            page.get_by_text(label, exact=False).first.click(timeout=2000)
            clicked = True
            time.sleep(3)
            break
        except Exception:
            pass
    after = page.evaluate("""() => ({
      url: location.href,
      body: (document.body.innerText||'').slice(0,6000),
      inputs: [...document.querySelectorAll('input')].map(i=>({v:i.value, ph:i.placeholder, dis:i.disabled, type:i.type})).slice(0,25)
    })""")
    json.dump({"clicked": clicked, "before_has_10560": "10,560" in before or "10560" in before, "after": after},
              open("_tmp_wing_click.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
    page.close()
print("done")
