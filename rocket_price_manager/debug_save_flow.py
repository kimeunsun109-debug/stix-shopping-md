# -*- coding: utf-8
import json, sys
from playwright.sync_api import sync_playwright
URL = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify?vendorInventoryId=16020715295"
LABEL = "110ml × 2개"
NEW = "13800"

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with sync_playwright() as p:
        page = p.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        page.goto(URL, timeout=120000)
        page.wait_for_timeout(15000)
        page.locator(".option-pane-table-row").first.scroll_into_view_if_needed()

        page.evaluate("""(label) => {
            const row = [...document.querySelectorAll('.option-pane-table-row')]
                .find(r => (r.innerText||'').includes(label));
            const btn = row ? [...row.querySelectorAll('button')].find(b => (b.innerText||'').trim()==='수정') : null;
            if (btn) btn.click();
        }""", LABEL)
        page.wait_for_timeout(3000)

        page.evaluate("""([label, price]) => {
            const row = [...document.querySelectorAll('.option-pane-table-row')]
                .find(r => (r.innerText||'').includes(label));
            const inp = row ? [...row.querySelectorAll('input')].find(i => i.value.replace(/,/g,'')==='13900' && !i.disabled) : null;
            if (inp) { inp.value = price; inp.dispatchEvent(new Event('input',{bubbles:true})); inp.dispatchEvent(new Event('change',{bubbles:true})); }
        }""", [LABEL, NEW])

        btns = page.evaluate("""() => [...document.querySelectorAll('button,a')]
            .map(b => ({t:(b.innerText||'').trim(), cls:(b.className||'').toString().slice(0,80), vis:b.offsetWidth>0}))
            .filter(x => x.t && /저장|확인|취소|수정/.test(x.t))""")
        print("buttons after edit:", json.dumps(btns[:25], ensure_ascii=False, indent=2))

        # click 저장 near option table
        saved = page.evaluate("""() => {
            for (const b of document.querySelectorAll('button')) {
                if ((b.innerText||'').trim() !== '저장') continue;
                const near = (b.closest('.option-pane-table-body') || b.closest('[class*=option]') || b.parentElement);
                if (near) { b.click(); return 'option 저장'; }
            }
            return null;
        }""")
        print("saved:", saved)
        page.wait_for_timeout(3000)
        row = page.evaluate("""(label) => {
            const r = [...document.querySelectorAll('.option-pane-table-row')]
                .find(x => (x.innerText||'').includes(label));
            return r ? r.innerText.replace(/\\s+/g,' ').trim() : null;
        }""", LABEL)
        print("row after save:", row)
        page.close()
main()
