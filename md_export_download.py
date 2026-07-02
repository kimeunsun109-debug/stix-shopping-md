# -*- coding: utf-8 -*-
"""STIX MD - 셀러센터 상품목록 엑셀/CSV 자동 다운로드 (CDP 9233)"""
from __future__ import annotations

import re
import shutil
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from md_catalog_io import PLATFORM_FILES, SRC

OUT_DIR = Path(__file__).parent
TODAY = datetime.now().strftime("%Y-%m-%d")
CDP_PORTS = [9233, 9222]
DOWNLOAD_DIR = OUT_DIR / "_downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

PLATFORM_DOMAIN = {
    "coupang": "wing.coupang",
    "esm": "esmplus.com",
    "smartstore": "smartstore.naver.com",
    "11st": "soffice.11st",
    "cafe24": "cafe24.com",
}

# platform_key -> (시작 URL, 저장 파일명, iframe 여부)
EXPORT_TARGETS = {
    "coupang": (
        "https://wing.coupang.com/tenants/seller-web/vendor-inventory/list",
        PLATFORM_FILES["쿠팡"].name,
        False,
    ),
    "rocket": (
        "https://wing.coupang.com/tenants/seller-web/vendor-inventory/list?salesMethod=ROCKET_GROWTH",
        PLATFORM_FILES["로켓그로스"].name,
        False,
    ),
    "esm": (
        "https://www.esmplus.com/Home/v2/goods-manage",
        PLATFORM_FILES["지마켓/옥션"].name,
        True,
    ),
    "smartstore": (
        "https://sell.smartstore.naver.com/#/products/origin-list",
        PLATFORM_FILES["스마트스토어"].name,
        False,
    ),
    "11st": (
        "https://soffice.11st.co.kr/view/8006",
        PLATFORM_FILES["11번가"].name,
        True,
    ),
    "cafe24": (
        "https://escall.cafe24.com/disp/admin/shop1/product/productmanage",
        PLATFORM_FILES["카페24"].name,
        False,
    ),
}


def cdp_alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
            return bool(r.read())
    except Exception:
        return False


def find_cdp_port() -> int | None:
    for p in CDP_PORTS:
        if cdp_alive(p):
            return p
    return None


def get_page_for(ctx, key: str):
    domain = PLATFORM_DOMAIN.get(key, "")
    for pg in ctx.pages:
        if domain and domain in pg.url.lower():
            return pg
    return None


def dismiss_popups(page):
    for sel in ('button:has-text("확인")', 'button:has-text("닫기")', 'label:has-text("오늘")'):
        try:
            loc = page.locator(sel)
            for i in range(min(loc.count(), 3)):
                el = loc.nth(i)
                if el.is_visible():
                    el.click(timeout=2000)
        except Exception:
            pass


def get_target_frame(page, use_iframe: bool):
    if not use_iframe:
        return page
    for fr in page.frames:
        if any(x in (fr.url or "") for x in (
            "item.esmplus.com/goods/list",
            "SellProductAction",
            "SellProductList",
        )):
            return fr
    return page


def prepare_list_page(page, key: str, start_url: str, use_iframe: bool):
    dismiss_popups(page)
    domain = PLATFORM_DOMAIN.get(key.replace("rocket", "coupang"), "")
    if domain and domain not in page.url:
        page.goto(start_url, timeout=90000, wait_until="domcontentloaded")
        page.wait_for_timeout(8000)

    if key == "smartstore":
        if "#/products/origin-list" not in page.url:
            page.evaluate("() => { window.location.hash = '#/products/origin-list'; }")
            page.wait_for_timeout(10000)
    elif key == "esm":
        fr = get_target_frame(page, True)
        if "item.esmplus.com" not in (fr.url or ""):
            page.wait_for_timeout(5000)
        loc = fr.locator('button:has-text("검색")')
        for i in range(loc.count()):
            el = loc.nth(i)
            try:
                if el.is_visible() and el.inner_text(timeout=800).strip() == "검색":
                    el.click(timeout=5000)
                    page.wait_for_timeout(15000)
                    break
            except Exception:
                pass
    elif key == "11st":
        fr = get_target_frame(page, True)
        for sel in ('input[type="button"][value="검색"]', 'button:has-text("검색")'):
            try:
                loc = fr.locator(sel)
                for i in range(loc.count() - 1, -1, -1):
                    el = loc.nth(i)
                    if el.is_visible():
                        el.click(timeout=5000)
                        fr.wait_for_timeout(12000)
                        break
            except Exception:
                pass
    elif key == "cafe24":
        dismiss_popups(page)
        for sel in ('text=상품목록 전체보기', 'a:has-text("상품목록")'):
            try:
                link = page.locator(sel).first
                if link.count() and link.is_visible():
                    link.click(timeout=5000)
                    page.wait_for_timeout(8000)
                    break
            except Exception:
                pass
    page.wait_for_timeout(3000)
    return get_target_frame(page, use_iframe)


def click_export(target, key: str) -> bool:
    """엑셀/CSV 다운로드 버튼 클릭"""
    patterns = (
        'button:has-text("엑셀")',
        'a:has-text("엑셀")',
        'button:has-text("Excel")',
        'a:has-text("Excel")',
        'button:has-text("다운로드")',
        'a:has-text("다운로드")',
        'text=엑셀 다운로드',
        'text=엑셀다운로드',
        'text=대량 엑셀 다운로드',
        'text=CSV 다운로드',
        'text=전체 다운로드',
        'input[value*="엑셀"]',
        'input[value*="다운"]',
    )
    if key == "smartstore":
        patterns = (
            'button:has-text("엑셀 다운")',
            'a:has-text("엑셀")',
            'button:has-text("다운로드")',
            *patterns,
        )
    for sel in patterns:
        try:
            loc = target.locator(sel)
            for i in range(loc.count()):
                el = loc.nth(i)
                if not el.is_visible():
                    continue
                txt = ""
                try:
                    txt = (el.inner_text(timeout=1000) or el.get_attribute("value") or "").strip()
                except Exception:
                    pass
                if txt and any(x in txt for x in ("로그", "업로드", "양식", "샘플")):
                    continue
                el.click(timeout=8000)
                return True
        except Exception:
            pass
    return False


def save_download(download, dest: Path) -> bool:
    try:
        tmp = DOWNLOAD_DIR / download.suggested_filename
        download.save_as(str(tmp))
        time.sleep(1)
        if not tmp.exists() or tmp.stat().st_size < 500:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            backup = dest.with_suffix(dest.suffix + f".bak_{TODAY}")
            shutil.copy2(dest, backup)
        shutil.copy2(tmp, dest)
        tmp.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def export_platform(ctx, key: str) -> dict:
    start_url, filename, use_iframe = EXPORT_TARGETS[key]
    plat_key = "coupang" if key == "rocket" else key
    rec = {"key": key, "file": filename, "ok": False, "error": ""}

    page = get_page_for(ctx, plat_key)
    if not page:
        page = ctx.new_page()
        page.goto(start_url, timeout=90000, wait_until="domcontentloaded")
        page.wait_for_timeout(8000)

    try:
        target = prepare_list_page(page, key if key != "rocket" else "coupang", start_url, use_iframe)
        dest = SRC / filename

        with page.expect_download(timeout=45000) as dl_info:
            if not click_export(target, key):
                rec["error"] = "download button not found"
                return rec
        download = dl_info.value
        rec["ok"] = save_download(download, dest)
        if rec["ok"]:
            rec["path"] = str(dest)
            rec["size"] = dest.stat().st_size
        else:
            rec["error"] = "파일 저장 실패"
    except Exception as e:
        rec["error"] = str(e)[:200]
    return rec


def main():
    port = find_cdp_port()
    if not port:
        print("FAIL: CDP 9233 없음 — start_chrome_for_md.bat 실행 후 로그인하고 재시도")
        return 1

    SRC.mkdir(parents=True, exist_ok=True)
    print(f"CDP port {port}")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        ctx = browser.contexts[0]
        for key in EXPORT_TARGETS:
            print(f"  export {key}...")
            results.append(export_platform(ctx, key))
            time.sleep(2)

    print(f"\nfolder: {SRC}")
    for r in results:
        status = "OK" if r.get("ok") else "FAIL"
        err = r.get("error", "")
        if r.get("ok"):
            print(f"  [{status}] {r['key']} -> {r['file']} ({r.get('size', 0)} bytes)")
        else:
            print(f"  [{status}] {r['key']} -> {r['file']} | {err}")

    ok_n = sum(1 for r in results if r.get("ok"))
    print(f"\n완료: {ok_n}/{len(results)}")
    if ok_n:
        print("다음: python md_price_sales_analyze.py")
    return 0 if ok_n else 1


if __name__ == "__main__":
    raise SystemExit(main())
