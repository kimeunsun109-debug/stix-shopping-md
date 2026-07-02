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
        page.evaluate("""(label) => {
            const row = [...document.querySelectorAll('.option-pane-table-row')]
                .find(r => (r.innerText||'').includes(label));
            const btn = row ? [...row.querySelectorAll('button')].find(b => (b.innerText||'').trim()==='수정') : null;
            if (btn) btn.click();
        }""", LABEL)
        page.wait_for_timeout(3000)

        page.evaluate("""(price) => {
            const inp = [...document.querySelectorAll('input')].find(i => i.value.replace(/,/g,'')==='13900' && !i.disabled);
            if (inp) { inp.value=price; inp.dispatchEvent(new Event('input',{bubbles:true})); inp.dispatchEvent(new Event('change',{bubbles:true})); }
        }""", NEW)

        btns = page.evaluate("""() => [...document.querySelectorAll('button,a')]
            .map(b=>({t:b.innerText.trim(), vis:b.offsetWidth>0, cls:(b.className||'').toString().slice(0,70)}))
            .filter(x=>x.vis && /저장|확인|취소|적용/.test(x.t))""")
        print("visible btns:", json.dumps(btns, ensure_ascii=False, indent=2))

        # try clicking visible 확인 in option area
        for sel in ['button.sc-common-btn', 'button.wing-web-component']:
            r = page.evaluate("""(sel) => {
                for (const b of document.querySelectorAll(sel)) {
                    const t = (b.innerText||'').trim();
                    if ((t==='확인'||t==='저장') && b.offsetWidth>0) {
                        b.click(); return t + ' ' + sel;
                    }
                }
                return null;
            }""", sel)
            if r: print("clicked:", r)
            page.wait_for_timeout(2000)

        row = page.evaluate("""(label) => {
            const r = [...document.querySelectorAll('.option-pane-table-row')]
                .find(x => (x.innerText||'').includes(label));
            return r ? r.innerText.replace(/\\s+/g,' ').trim() : null;
        }""", LABEL)
        print("row:", row)
        page.close()
main()
