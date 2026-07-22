# -*- coding: utf-8
"""Fix p2 price via Wing 상품수정 flow."""
from __future__ import annotations

import json
import re
import time
from playwright.sync_api import sync_playwright

VID = "94705203391"
TARGET = 10290
LIST = (
    "https://wing.coupang.com/tenants/seller-web/vendor-inventory/list"
    f"?searchKeywordType=ALL&searchKeywords={VID}&exposureStatus=ALL"
)


def main() -> None:
    result = {"ok": False, "steps": []}
    with sync_playwright() as pw:
        page = pw.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        page.goto(LIST, wait_until="domcontentloaded", timeout=120000)
        time.sleep(4)
        body0 = page.evaluate("() => document.body.innerText || ''")
        result["steps"].append(f"list price: {'10,560' in body0}")
        if "총 0개" in body0 and "총 1개" not in body0:
            page.locator("input[type='text']").first.fill(VID)
            page.keyboard.press("Enter")
            time.sleep(4)

        # 상품수정 click
        page.get_by_text("상품수정", exact=True).first.click(timeout=10000)
        time.sleep(5)
        result["steps"].append(f"edit url: {page.url}")

        body1 = page.evaluate("() => document.body.innerText || ''")
        result["steps"].append(f"has 10560: {'10,560' in body1 or '10560' in body1}")

        # find sale price inputs for options containing 15ml and 3
        filled = page.evaluate(
            """(target) => {
          const inputs = [...document.querySelectorAll('input')];
          let changed = 0;
          for (const inp of inputs) {
            const ctx = (inp.closest('tr,div,section')?.innerText || '').slice(0,300);
            if (!/15\s*ml|15ml/i.test(ctx) || !/3/.test(ctx)) continue;
            if (inp.disabled || inp.type === 'hidden') continue;
            const v = (inp.value||'').replace(/,/g,'');
            if (/^\\d+$/.test(v) && Number(v) >= 1000) {
              inp.focus();
              inp.value = String(target);
              inp.dispatchEvent(new Event('input', {bubbles:true}));
              inp.dispatchEvent(new Event('change', {bubbles:true}));
              changed++;
            }
          }
          if (changed) return {changed, mode:'option-match'};
          // fallback: all numeric sale-like inputs >=5000
          for (const inp of inputs) {
            if (inp.disabled || inp.type === 'hidden') continue;
            const ctx = (inp.closest('tr,div')?.innerText || '').slice(0,120);
            if (!/판매|가격|price/i.test(ctx + inp.placeholder + inp.name)) continue;
            const v = (inp.value||'').replace(/,/g,'');
            if (/^\\d+$/.test(v) && Number(v) >= 5000) {
              inp.focus(); inp.value = String(target);
              inp.dispatchEvent(new Event('input', {bubbles:true}));
              inp.dispatchEvent(new Event('change', {bubbles:true}));
              changed++;
            }
          }
          return {changed, mode:'fallback'};
        }""",
            TARGET,
        )
        result["fill"] = filled
        time.sleep(1)

        saved = False
        for label in ("수정완료", "저장", "적용", "확인"):
            try:
                page.get_by_role("button", name=re.compile(label)).first.click(timeout=4000)
                time.sleep(3)
                saved = True
                result["steps"].append(f"clicked {label}")
                break
            except Exception:
                try:
                    page.get_by_text(re.compile(f"^{label}$")).first.click(timeout=3000)
                    time.sleep(3)
                    saved = True
                    result["steps"].append(f"clicked text {label}")
                    break
                except Exception:
                    continue

        if saved:
            # confirm dialogs
            for label in ("확인", "저장", "예"):
                try:
                    page.get_by_role("button", name=re.compile(label)).first.click(timeout=2000)
                    time.sleep(2)
                    result["steps"].append(f"confirm {label}")
                except Exception:
                    pass

        time.sleep(3)
        page.goto(LIST, wait_until="domcontentloaded", timeout=120000)
        time.sleep(3)
        body2 = page.evaluate("() => document.body.innerText || ''")
        m = re.search(r"10,290|10290", body2)
        result["verified_10290"] = bool(m)
        result["still_10560"] = "10,560" in body2
        result["ok"] = result["verified_10290"] and not result.get("still_10560", True)
        result["price_snip"] = body2[body2.find("B7000") : body2.find("B7000") + 800] if "B7000" in body2 else ""

        with open("item_winner/_fix_p2_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        page.close()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
