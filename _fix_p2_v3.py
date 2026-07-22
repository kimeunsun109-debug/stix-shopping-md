# -*- coding: utf-8 -*-
"""Submit pending option price change on Wing modify page."""
from __future__ import annotations

import json
import re
import time
from playwright.sync_api import sync_playwright

VENDOR_INVENTORY_ID = "16020715295"
TARGET = 10290
MODIFY_URL = (
    "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify"
    f"?vendorInventoryId={VENDOR_INVENTORY_ID}"
)
LIST_URL = (
    "https://wing.coupang.com/tenants/seller-web/vendor-inventory/list"
    f"?searchKeywordType=ALL&searchKeywords={VENDOR_INVENTORY_ID}&exposureStatus=ALL"
)


def dismiss_modals(page) -> None:
    for _ in range(3):
        closed = False
        for sel in (
            "button:has-text('닫기')",
            "button:has-text('나중에')",
            "button:has-text('건너뛰기')",
            ".modal-close",
            "[class*='modal-close']",
        ):
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=400):
                    loc.click(timeout=2000)
                    time.sleep(0.4)
                    closed = True
            except Exception:
                pass
        if not closed:
            break
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass


def click_option_edit(page, option_hint: str) -> bool:
    page.evaluate("""() => {
      const el = [...document.querySelectorAll('*')].find(e => (e.innerText||'').includes('옵션 목록'));
      el?.scrollIntoView({block:'center'});
    }""")
    time.sleep(1)
    clicked = page.evaluate(
        """(hint) => {
      const cells = [...document.querySelectorAll('.option-pane-table-cell')];
      for (const cell of cells) {
        const t = cell.innerText || '';
        if (!t.includes(hint)) continue;
        const btn = cell.querySelector('button');
        if (btn) { btn.click(); return true; }
      }
      return false;
    }""",
        option_hint,
    )
    time.sleep(2)
    return bool(clicked)


def set_sale_price_in_row(page, price: int) -> bool:
    """Set 판매가 in opened inline option editor."""
    filled = page.evaluate(
        """(price) => {
      const cells = [...document.querySelectorAll('.option-pane-table-cell')];
      for (const cell of cells) {
        const t = cell.innerText || '';
        if (!/15\\s*ml.*3개/.test(t)) continue;
        const inputs = [...cell.querySelectorAll('input[type=text]')].filter(i => !i.disabled);
        // sale price is typically the 2nd numeric field after stock
        const nums = inputs.filter(i => /^[\\d,]+$/.test(i.value||''));
        for (const inp of nums) {
          const v = (inp.value||'').replace(/,/g,'');
          if (Number(v) >= 5000 && Number(v) <= 20000) {
            inp.focus();
            inp.value = String(price);
            inp.dispatchEvent(new Event('input', {bubbles:true}));
            inp.dispatchEvent(new Event('change', {bubbles:true}));
            inp.dispatchEvent(new Event('blur', {bubbles:true}));
            return true;
          }
        }
      }
      // fallback: any enabled input showing 10560 or 10290
      for (const inp of document.querySelectorAll('input')) {
        const v = (inp.value||'').replace(/,/g,'');
        if (!inp.disabled && /^\\d+$/.test(v) && Number(v) >= 9000 && Number(v) <= 12000) {
          inp.focus(); inp.value = String(price);
          inp.dispatchEvent(new Event('input', {bubbles:true}));
          inp.dispatchEvent(new Event('change', {bubbles:true}));
          return true;
        }
      }
      return false;
    }""",
        price,
    )
    return bool(filled)


def submit_modify_page(page) -> list[str]:
    steps: list[str] = []

    def click_btn_text(*labels: str) -> bool:
        for label in labels:
            ok = page.evaluate(
                """(label) => {
              for (const b of document.querySelectorAll('button')) {
                const t = (b.innerText||'').trim();
                if (t === label && b.offsetParent && !b.disabled) { b.click(); return true; }
              }
              return false;
            }""",
                label,
            )
            if ok:
                steps.append(label)
                time.sleep(2)
                return True
        return False

    click_btn_text("\uc801\uc6a9", "\ud655\uc778", "\uc800\uc7a5")
    click_btn_text("\uc218\uc815 \ubc0f \uac80\uc218 \uc694\uccad", "\uc218\uc815\uc644\ub8cc", "\uc800\uc7a5")

    for _ in range(5):
        if not click_btn_text(
            "\ud655\uc778",
            "\uc608",
            "\uc800\uc7a5",
            "\uc218\uc815 \ubc0f \uac80\uc218 \uc694\uccad",
        ):
            break
    return steps


def verify_list(page) -> str:
    page.goto(LIST_URL, wait_until="domcontentloaded", timeout=120000)
    time.sleep(4)
    body = page.evaluate("() => document.body.innerText || ''")
    if "10,290" in body:
        return "10290"
    if "10,560" in body:
        return "10560"
    return "unknown"


def main() -> None:
    result: dict = {}
    with sync_playwright() as pw:
        page = pw.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        page.goto(MODIFY_URL, wait_until="domcontentloaded", timeout=120000)
        time.sleep(5)
        dismiss_modals(page)

        result["edit_clicked"] = click_option_edit(page, "15ml \u00d7 3\uac1c")
        result["price_filled"] = set_sale_price_in_row(page, TARGET)
        time.sleep(1)
        result["submit_steps"] = submit_modify_page(page)
        time.sleep(5)
        result["after"] = verify_list(page)
        result["ok"] = result["after"] == "10290"
        page.close()

    with open("item_winner/_fix_p2_v3.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
