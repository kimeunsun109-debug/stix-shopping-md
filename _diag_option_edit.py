# -*- coding: utf-8 -*-
"""Diagnose option-row price edit modal on Wing modify page."""
import json
import time
from playwright.sync_api import sync_playwright

URL = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify?vendorInventoryId=16020715295"

with sync_playwright() as pw:
    page = pw.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=120000)
    time.sleep(6)

    # scroll to option table
    page.evaluate("""() => {
      const el = [...document.querySelectorAll('*')].find(e => e.innerText?.includes('옵션 목록'));
      el?.scrollIntoView({block:'center'});
    }""")
    time.sleep(1)

    click_result = page.evaluate("""() => {
      const rows = [...document.querySelectorAll('tr, [class*="row"], div')];
      for (const row of rows) {
        const t = row.innerText || '';
        if (!/15\\s*ml.*3개|15ml × 3개/.test(t)) continue;
        if (!/10,?560/.test(t)) continue;
        if (t.length > 500) continue;
        const btns = [...row.querySelectorAll('button, a, span, div')].filter(
          b => (b.innerText||'').trim() === '수정'
        );
        if (btns.length) {
          btns[btns.length-1].click();
          return {clicked: true, rowText: t.slice(0,200), btnCount: btns.length};
        }
      }
      return {clicked: false};
    }""")
    time.sleep(3)

    after = page.evaluate("""() => {
      const inputs = [...document.querySelectorAll('input, textarea')].map(i => ({
        tag: i.tagName, type: i.type, value: i.value, disabled: i.disabled,
        ph: i.placeholder, visible: i.offsetParent !== null,
        ctx: (i.closest('tr,div,section,dialog,[role=dialog]')?.innerText||'').slice(0,150)
      }));
      const dialogs = [...document.querySelectorAll('[role=dialog], .modal, [class*=Modal], [class*=modal], [class*=popup]')]
        .map(d => ({cls: d.className?.slice?.(0,80), text: (d.innerText||'').slice(0,500)}));
      const buttons = [...document.querySelectorAll('button')].map(b => ({
        text: (b.innerText||'').trim().slice(0,30), disabled: b.disabled, visible: b.offsetParent !== null
      })).filter(b => b.text && b.visible);
      return {
        url: location.href,
        click: null,
        dialogs,
        enabled_inputs: inputs.filter(i => !i.disabled && i.type !== 'checkbox' && i.type !== 'radio' && i.type !== 'hidden'),
        visible_buttons: buttons.filter(b => /저장|확인|적용|수정|취소|완료/.test(b.text))
      };
    }""")
    after["click"] = click_result

    json.dump(after, open("item_winner/_diag_option_edit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    page.close()
print("done")
