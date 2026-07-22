# -*- coding: utf-8 -*-
"""Dump option table DOM + test row edit click."""
import json
import re
import time
from playwright.sync_api import sync_playwright

URL = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify?vendorInventoryId=16020715295"

def dismiss_modals(page):
    for sel in [
        "button:has-text('닫기')",
        "button:has-text('나중에')",
        "button:has-text('건너뛰기')",
        ".modal-close",
        "[class*='modal-close']",
        "button:has-text('취소')",
    ]:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=500):
                loc.click(timeout=2000)
                time.sleep(0.5)
        except Exception:
            pass
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass

with sync_playwright() as pw:
    page = pw.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=120000)
    time.sleep(6)
    dismiss_modals(page)
    time.sleep(1)

    dom = page.evaluate("""() => {
      const hits = [];
      const all = [...document.querySelectorAll('*')];
      for (const el of all) {
        const t = (el.innerText||'').trim();
        if (!t || t.length > 300) continue;
        if (/15\\s*ml.*3개/.test(t) && /10,?560/.test(t) && /수정/.test(t)) {
          hits.push({
            tag: el.tagName,
            cls: (el.className||'').toString().slice(0,80),
            text: t.slice(0,250),
            childTags: [...el.children].map(c=>c.tagName).slice(0,10)
          });
        }
      }
      const editBtns = [...document.querySelectorAll('button,a,span,div')]
        .filter(e => (e.innerText||'').trim() === '수정' && e.offsetParent)
        .map(e => ({
          tag: e.tagName,
          cls: (e.className||'').toString().slice(0,60),
          parentText: (e.parentElement?.innerText||'').slice(0,120)
        }));
      return {hits: hits.slice(0,10), editBtns: editBtns.slice(0,8)};
    }""")

    # click first edit btn whose parent mentions 15ml and 3개
    clicked = False
    for i, btn in enumerate(dom.get("editBtns", [])):
        if re.search(r"15\s*ml.*3개|15ml × 3", btn.get("parentText", "")):
            try:
                page.locator("button, a, span, div").filter(
                    has_text=re.compile("^수정$")
                ).nth(i).click(timeout=5000)
                clicked = True
                break
            except Exception:
                pass

    if not clicked:
        # fallback: first visible 수정 near 옵션 목록
        page.get_by_text("옵션 목록").scroll_into_view_if_needed()
        page.locator("button").filter(has_text=re.compile("^수정$")).first.click(timeout=5000)
        clicked = True

    time.sleep(3)
    after = page.evaluate("""() => {
      const inputs = [...document.querySelectorAll('input')].filter(i => !i.disabled && i.type==='text')
        .map(i => ({value: i.value, ph: i.placeholder, ctx: (i.closest('tr,div')?.innerText||'').slice(0,120)}));
      const body = (document.body.innerText||'');
      return {
        clicked: true,
        inputs,
        has10290field: inputs.some(i => /10,?560|10560/.test(i.value)),
        bodyNear: body.includes('판매가') ? body.slice(body.indexOf('판매가')-50, body.indexOf('판매가')+400) : ''
      };
    }""")
    after["dom"] = dom
    after["clicked"] = clicked

    json.dump(after, open("item_winner/_diag_option_dom.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    page.close()
print("done")
