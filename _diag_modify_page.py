# -*- coding: utf-8
import json, time
from playwright.sync_api import sync_playwright

URL = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify?vendorInventoryId=16020715295"
with sync_playwright() as pw:
    page = pw.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=120000)
    time.sleep(6)
    data = page.evaluate("""() => {
      const inputs = [...document.querySelectorAll('input, textarea')].map(i => ({
        tag: i.tagName, type: i.type, value: i.value, ph: i.placeholder,
        name: i.name, id: i.id, disabled: i.disabled,
        ctx: (i.closest('tr,div,label')?.innerText||'').slice(0,100)
      }));
      const texts = (document.body.innerText||'');
      return {
        url: location.href,
        has10560: /10,560|10560/.test(texts),
        has159ml: /15ml|15 ml/i.test(texts),
        input_count: inputs.length,
        inputs: inputs.filter(i => i.value || /가격|판매|price|10560|10,560/.test(i.ctx+i.value)),
        body_snip: texts.includes('15') ? texts.slice(texts.indexOf('15'), texts.indexOf('15')+2000) : texts.slice(0,3000)
      };
    }""")
    json.dump(data, open("_tmp_wing_modify.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
    page.close()
print("done")
