# -*- coding: utf-8
"""B7000 행 '수정' 클릭 후 편집 UI 프로브 (CDP 9233)."""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "probe_results"
URL = (
    "https://wing.coupang.com/tenants/seller-price-management/"
    "?searchInputValue=B7000&searchInputType=KEYWORD"
)


def main():
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9233")
        page = browser.contexts[0].new_page()
        page.goto(URL, timeout=90000)
        page.wait_for_timeout(12000)

        search = page.locator('input[placeholder*="등록상품명"]')
        if search.count():
            search.first.fill("B7000")
            page.keyboard.press("Enter")
            page.wait_for_timeout(8000)

        rows_text = page.locator("body").inner_text()
        print("has B7000", "B7000" in rows_text)
        print("has 110ml", "110ml" in rows_text)
        print("has 로켓", "로켓" in rows_text)

        # 모든 수정 링크와 인접 행 텍스트
        mods = page.locator("a.ap-action-link", has_text="수정")
        print("modify links", mods.count())
        samples = []
        for i in range(min(mods.count(), 5)):
            link = mods.nth(i)
            row_text = link.evaluate(
                """el => {
                const row = el.closest('tr') || el.closest('[class*="row"]') || el.parentElement?.parentElement;
                return row ? row.innerText.replace(/\\s+/g,' ').trim().slice(0,250) : '';
            }"""
            )
            samples.append(row_text)
            print(i, row_text[:120])

        # 110ml 포함 행의 수정 클릭
        target_idx = None
        for i in range(mods.count()):
            row_text = mods.nth(i).evaluate(
                """el => {
                const row = el.closest('tr') || el.closest('[class*="row"]');
                return row ? row.innerText : '';
            }"""
            )
            if "110ml" in row_text and "B7000" in row_text:
                target_idx = i
                break

        if target_idx is None:
            for i in range(mods.count()):
                row_text = mods.nth(i).evaluate(
                    """el => {
                    const row = el.closest('tr') || el.closest('[class*="row"]');
                    return row ? row.innerText : '';
                }"""
                )
                if "B7000" in row_text:
                    target_idx = i
                    break

        if target_idx is not None:
            print("click modify index", target_idx)
            mods.nth(target_idx).click()
            page.wait_for_timeout(6000)

        data = page.evaluate(
            """() => {
            const modals = [...document.querySelectorAll('.wing-modal,[role=dialog]')]
              .filter(m => m.getBoundingClientRect().width > 0)
              .map(m => ({ cls: m.className, text: (m.innerText||'').slice(0,1000) }));
            const inputs = [...document.querySelectorAll('input, textarea')]
              .filter(el => el.getBoundingClientRect().width > 0)
              .map(el => ({
                type: el.type, val: el.value, ph: el.placeholder||'',
                cls: (el.className||'').toString().slice(0,160), id: el.id||'',
                parent: (el.closest('tr')||el.parentElement)?.innerText?.replace(/\\s+/g,' ').slice(0,160)||''
              }));
            const buttons = [...document.querySelectorAll('button, a.ap-action-link')]
              .map(el => ({ tag: el.tagName, text: (el.innerText||'').trim().slice(0,40),
                cls: (el.className||'').toString().slice(0,160) }))
              .filter(b => b.text && /저장|확인|적용|취소|수정/.test(b.text));
            return { url: location.href, modals, inputs, buttons, rowSamples: [] };
        }"""
        )
        data["rowSamples"] = samples
        data["clickedIndex"] = target_idx

        out = OUT / "wing_b7000_edit.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        page.screenshot(path=OUT / "wing_b7000_edit.png", full_page=True)
        print("saved", out)
        print(json.dumps(data, ensure_ascii=False, indent=2)[:5000])
        page.close()


if __name__ == "__main__":
    main()
