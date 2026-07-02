# -*- coding: utf-8
"""B7000 110ml×2 판매가 13,800원 변경."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = (
    "https://wing.coupang.com/tenants/seller-web/"
    "vendor-inventory/modify?vendorInventoryId=16020715295"
)
NEW_PRICE = "13800"
LABEL = "110ml \u00d7 2\uac1c"
OUT = Path(__file__).resolve().parent / "probe_results"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)

    with sync_playwright() as p:
        page = p.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
        page.goto(URL, timeout=120000)
        page.wait_for_timeout(15000)
        page.locator(".option-pane-table-row").first.scroll_into_view_if_needed()

        # 1) 행 수정 버튼
        mod = page.evaluate(
            """(label) => {
            const row = [...document.querySelectorAll('.option-pane-table-row')]
                .find(r => (r.innerText||'').includes(label));
            const btn = row ? [...row.querySelectorAll('button')]
                .find(b => (b.innerText||'').trim() === '수정') : null;
            if (!btn) return null;
            btn.click();
            return row.innerText.replace(/\\s+/g,' ').slice(0,120);
        }""",
            LABEL,
        )
        print("modify:", mod)
        page.wait_for_timeout(3000)

        # 2) 판매가 13,900 → 13,800
        price = page.evaluate(
            """(newPrice) => {
            const inputs = [...document.querySelectorAll('input')].filter(
                i => !i.disabled && i.value.replace(/,/g,'') === '13900'
            );
            if (!inputs.length) return { error: '13900 input not found' };
            for (const inp of inputs) {
                const old = inp.value;
                inp.focus();
                inp.value = newPrice;
                inp.dispatchEvent(new Event('input', {bubbles: true}));
                inp.dispatchEvent(new Event('change', {bubbles: true}));
            }
            return { count: inputs.length, new: newPrice };
        }""",
            NEW_PRICE,
        )
        print("price:", price)
        page.wait_for_timeout(1000)

        # 3) 옵션 편집 패널 저장 (visible wuic-button 저장)
        row_save = page.evaluate(
            """() => {
            for (const b of document.querySelectorAll('button.wing-web-component.wuic-button')) {
                if ((b.innerText||'').trim() === '저장' && b.offsetWidth > 0) {
                    b.click();
                    return true;
                }
            }
            return false;
        }"""
        )
        print("row panel save:", row_save)
        page.wait_for_timeout(3000)

        # 4) 페이지 저장
        page.evaluate(
            """() => {
            const b = document.querySelector('button.fs-unmask');
            if (b) { b.scrollIntoView({block:'center'}); b.click(); }
        }"""
        )
        page.wait_for_timeout(3000)
        final = page.evaluate(
            """() => {
            for (const b of document.querySelectorAll('button.wing-modal-confirm-trigger, button.wuic-button')) {
                if ((b.innerText||'').trim() === '확인' && b.offsetWidth > 0) {
                    b.click(); return true;
                }
            }
            return false;
        }"""
        )
        print("page confirm:", final)
        page.wait_for_timeout(10000)

        # 5) 검증 — 페이지 새로고침
        page.reload(timeout=120000)
        page.wait_for_timeout(15000)
        verify = page.evaluate(
            """(label) => {
            const row = [...document.querySelectorAll('.option-pane-table-row')]
                .find(r => (r.innerText||'').includes(label));
            return row ? row.innerText.replace(/\\s+/g,' ').trim() : 'not found';
        }""",
            LABEL,
        )
        print("verify:", verify)
        page.screenshot(path=str(OUT / "110x2_done.png"), full_page=True)
        page.close()
        ok = "13,800" in verify or "13800" in verify
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
