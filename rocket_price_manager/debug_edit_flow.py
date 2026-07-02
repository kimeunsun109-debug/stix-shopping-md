# -*- coding: utf-8
import json, sys
from playwright.sync_api import sync_playwright
URL = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify?vendorInventoryId=16020715295"
LABEL = "110ml × 2개"

def click_text(page, text):
    return page.evaluate("""(text) => {
        for (const el of document.querySelectorAll('a,button,span')) {
            if ((el.innerText||'').trim() === text) { el.click(); return true; }
        }
        return false;
    }""", text)

def dump(page):
    return page.evaluate("""(label) => {
        const row = [...document.querySelectorAll('.option-pane-table-row')]
            .find(r => (r.innerText||'').includes(label));
        return {
            row: row ? row.innerText.replace(/\\s+/g,' ').slice(0,200) : null,
            inputs: row ? [...row.querySelectorAll('input')].map(i=>({v:i.value,d:i.disabled})) : [],
            allEnabledPrices: [...document.querySelectorAll('input')].filter(i=>{
                const v=(i.value||'').replace(/,/g,'');
                return /^[0-9]+$/.test(v)&&parseInt(v)>=10000&&!i.disabled;
            }).map(i=>({v:i.value, near:(i.closest('.option-pane-table-row')||i.parentElement)?.innerText?.slice(0,80)||''}))
        };
    }""", LABEL)

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with sync_playwright() as p:
        page = p.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        page.goto(URL, timeout=120000)
        page.wait_for_timeout(15000)
        page.locator(".option-pane-table-row").first.scroll_into_view_if_needed()

        print("1 after load:", json.dumps(dump(page), ensure_ascii=False))
        click_text(page, "옵션수정")
        page.wait_for_timeout(2000)
        print("2 after 옵션수정:", json.dumps(dump(page), ensure_ascii=False))

        click_text(page, "확인")
        page.wait_for_timeout(2000)
        print("3 after 확인:", json.dumps(dump(page), ensure_ascii=False))

        page.evaluate("""(label) => {
            const row = [...document.querySelectorAll('.option-pane-table-row')]
                .find(r => (r.innerText||'').includes(label));
            if (!row) return;
            const mod = [...row.querySelectorAll('*')].find(e => (e.innerText||'').trim()==='수정');
            if (mod) mod.click();
        }""", LABEL)
        page.wait_for_timeout(3000)
        print("4 after row 수정:", json.dumps(dump(page), ensure_ascii=False))
        page.close()
main()
