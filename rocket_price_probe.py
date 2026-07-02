# -*- coding: utf-8
"""Wing / Coupang 상품페이지 DOM 프로브 — selector 수집용 (1회 실행)"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "probe_results"
OUT.mkdir(exist_ok=True)

COMPETITOR_URL = (
    "https://www.coupang.com/vp/products/9619525970"
    "?itemId=28724704542&vendorItemId=95622458581"
)
WING_LIST_URL = (
    "https://wing.coupang.com/vendor-inventory/list"
    "?searchKeywordType=ALL&searchKeywords=B7000&salesMethod=ALL"
    "&productStatus=ALL&locale=ko_KR&countPerPage=50&page=1"
)
CDP_PORTS = [9233, 9222]


def cdp_alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2):
            return True
    except Exception:
        return False


def dump_candidates(page, label: str) -> dict:
    """가격/판매자/입력 필드 후보 selector 수집"""
    data = page.evaluate(
        """() => {
        const out = { price: [], seller: [], inputs: [], buttons: [], links: [] };
        const priceRe = /[0-9,]+\\s*원|[0-9,]+원/;
        document.querySelectorAll('*').forEach(el => {
            const t = (el.innerText || '').trim().replace(/\\s+/g, ' ');
            if (t.length > 0 && t.length < 80 && priceRe.test(t)) {
                const sel = el.id ? '#' + CSS.escape(el.id)
                    : el.className && typeof el.className === 'string' && el.className.trim()
                    ? el.tagName.toLowerCase() + '.' + el.className.trim().split(/\\s+/).slice(0,2).join('.')
                    : el.tagName.toLowerCase();
                out.price.push({ sel, text: t.slice(0,60), tag: el.tagName });
            }
            if (/판매자|셀러|스토어|스팃|업체|vendor/i.test(t) && t.length < 120) {
                out.seller.push({ sel: el.tagName, text: t.slice(0,80) });
            }
        });
        document.querySelectorAll('input, textarea').forEach(el => {
            const ph = el.placeholder || '';
            const nm = el.name || '';
            const aria = el.getAttribute('aria-label') || '';
            const label = (ph + nm + aria).toLowerCase();
            if (/price|가격|판매|금액|원/.test(label) || /price|amount|sale/i.test(el.id||'')) {
                out.inputs.push({
                    tag: el.tagName, type: el.type, id: el.id, name: el.name,
                    placeholder: ph, aria: aria, class: (el.className||'').slice(0,80),
                    value: el.value
                });
            }
        });
        document.querySelectorAll('button, a, [role="button"]').forEach(el => {
            const t = (el.innerText || el.textContent || '').trim().replace(/\\s+/g,' ');
            if (/저장|수정|적용|확인|가격|편집|edit|save/i.test(t) && t.length < 30) {
                out.buttons.push({ tag: el.tagName, text: t, class: (el.className||'').slice(0,80), href: el.href||'' });
            }
        });
        document.querySelectorAll('a[href]').forEach(el => {
            const h = el.href || '';
            if (/modify|edit|inventory|product|vendor-inventory/.test(h)) {
                out.links.push({ text: (el.innerText||'').trim().slice(0,40), href: h.slice(0,120) });
            }
        });
        // dedupe
        const dedupe = (arr, key) => {
            const seen = new Set();
            return arr.filter(x => { const k = JSON.stringify(x[key]||x); if(seen.has(k)) return false; seen.add(k); return true; });
        };
        out.price = dedupe(out.price, 'text').slice(0, 30);
        out.seller = dedupe(out.seller, 'text').slice(0, 20);
        out.inputs = dedupe(out.inputs, 'id').slice(0, 30);
        out.buttons = dedupe(out.buttons, 'text').slice(0, 25);
        out.links = dedupe(out.links, 'href').slice(0, 25);
        return out;
    }"""
    )
    path = OUT / f"{label}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    page.screenshot(path=OUT / f"{label}.png", full_page=False)
    print(f"[{label}] saved {path}")
    return data


def main():
    port = next((p for p in CDP_PORTS if cdp_alive(p)), None)
    if not port:
        print("CDP 없음. start_chrome_for_md.bat 실행 후 재시도")
        return 1

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        ctx = browser.contexts[0]
        page = ctx.new_page()

        print("=== Competitor product page ===")
        page.goto(COMPETITOR_URL, timeout=90000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        comp = dump_candidates(page, "competitor")
        print("price samples:", [x["text"] for x in comp["price"][:8]])
        print("seller samples:", [x["text"] for x in comp["seller"][:5]])

        print("=== Wing inventory list ===")
        page.goto(WING_LIST_URL, timeout=90000, wait_until="domcontentloaded")
        page.wait_for_timeout(10000)
        wing_list = dump_candidates(page, "wing_list")
        print("body snippet:", page.locator("body").inner_text()[:400].replace("\n", " "))
        print("links:", [x["href"][:80] for x in wing_list["links"][:5]])

        # Wing 상품 수정 페이지 — 목록에서 첫 수정 링크 시도
        edit_href = None
        for link in wing_list.get("links", []):
            if "modify" in link.get("href", "") or "edit" in link.get("href", ""):
                edit_href = link["href"]
                break
        if not edit_href:
            # evaluate direct links
            edit_href = page.evaluate("""() => {
                const a = [...document.querySelectorAll('a[href]')].find(x =>
                    /modify|edit|registration-product|vendor-inventory\\/modify/.test(x.href));
                return a ? a.href : null;
            }""")

        if edit_href:
            print("=== Wing edit page ===", edit_href[:100])
            page.goto(edit_href, timeout=90000, wait_until="domcontentloaded")
            page.wait_for_timeout(12000)
            wing_edit = dump_candidates(page, "wing_edit")
            print("inputs:", wing_edit["inputs"][:10])
            print("buttons:", wing_edit["buttons"][:10])
        else:
            print("Wing 수정 링크를 찾지 못함 — wing_list.json / 스크린샷 확인 필요")

        page.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
