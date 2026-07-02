# -*- coding: utf-8
import json, sys
from playwright.sync_api import sync_playwright
URL = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify?vendorInventoryId=16020715295"
LABEL = "110ml × 2개"

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with sync_playwright() as p:
        page = p.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        page.goto(URL, timeout=120000)
        page.wait_for_timeout(15000)
        page.locator(".option-pane-table-row").first.scroll_into_view_if_needed()
        # 옵션수정 버튼
        clicked = page.evaluate("""() => {
            for (const el of document.querySelectorAll('a,button,span')) {
                if ((el.innerText||'').trim() === '옵션수정') { el.click(); return '옵션수정'; }
            }
            return null;
        }""")
        print("clicked:", clicked)
        page.wait_for_timeout(3000)
        data = page.evaluate("""(label) => {
            const row = [...document.querySelectorAll('.option-pane-table-row, tr, [class*=row]')]
                .find(r => (r.innerText||'').includes(label) && (r.innerText||'').includes('13,900'));
            const enabled = [...document.querySelectorAll('input')].filter(i => {
                const v = (i.value||'').replace(/,/g,'');
                return v === '13900' && !i.disabled;
            });
            return {
                rowText: row ? row.innerText.replace(/\\s+/g,' ').slice(0,250) : null,
                enabled13900: enabled.length,
                enabledVals: enabled.map(i => i.value),
                btns: [...document.querySelectorAll('button,a')].map(b=>b.innerText.trim())
                    .filter(t => /저장|확인|수정|취소|적용/.test(t)).slice(0,20)
            };
        }""", LABEL)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        page.close()
main()
