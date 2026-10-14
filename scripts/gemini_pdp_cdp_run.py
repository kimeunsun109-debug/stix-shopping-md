#!/usr/bin/env python3
"""Attach to logged-in Chrome via CDP (9222/9233) and run Gemini 4-panel PDP batch."""
from __future__ import annotations

import argparse
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

import importlib.util

_ROOT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "gemini_pdp_4split_batch", _ROOT / "gemini_pdp_4split_batch.py"
)
_batch = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(_batch)
OUT_ROOT = _batch.OUT_ROOT
build_prompt = _batch.build_prompt
infer_category = _batch.infer_category

CDP_PORTS = (9222, 9233, 9223)


def probe_cdp(cdp_url: str | None) -> str:
    if cdp_url:
        urllib.request.urlopen(f"{cdp_url.rstrip('/')}/json/version", timeout=3)
        return cdp_url.rstrip("/")
    for port in CDP_PORTS:
        url = f"http://127.0.0.1:{port}"
        try:
            urllib.request.urlopen(f"{url}/json/version", timeout=2)
            return url
        except Exception:
            continue
    raise SystemExit(
        "CDP Chrome 없음. 9222로 remote-debugging Chrome 실행 후 재시도.\n"
        "예: start_chrome_for_md.bat 또는 --remote-debugging-port=9222"
    )


def pick_gemini_page(browser):
    for ctx in browser.contexts:
        for page in ctx.pages:
            if "gemini.google.com" in (page.url or ""):
                return page
    page = browser.contexts[0].new_page()
    page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=120_000)
    time.sleep(3)
    return page


def login_ok(page) -> bool:
    body = page.inner_text("body")
    return not ("Meet Gemini" in body and "Sign in" in body)


def generate_one(page, product: str, thumb: Path, out_dir: Path) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt(product, infer_category(product))
    (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    page.bring_to_front()
    try:
        page.get_by_role("link", name="Images").click(timeout=5000)
        time.sleep(1.5)
    except PlaywrightTimeout:
        try:
            page.get_by_text("Images", exact=False).first.click(timeout=4000)
            time.sleep(1.5)
        except PlaywrightTimeout:
            pass
    if thumb.is_file():
        try:
            page.locator('input[type="file"]').first.set_input_files(str(thumb))
            time.sleep(2)
        except PlaywrightTimeout:
            print(f"WARN: upload skip — {thumb}", file=sys.stderr)
    box = page.locator("textarea, div[contenteditable=true]").first
    box.click(timeout=15_000)
    box.fill(prompt)
    page.keyboard.press("Enter")
    time.sleep(50)
    page.screenshot(path=str(out_dir / "result_screenshot.png"), full_page=True)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp", default="", help="CDP base URL e.g. http://127.0.0.1:9222")
    ap.add_argument("--product", required=True)
    ap.add_argument("--thumb", type=Path, default=Path())
    ap.add_argument("--login-check", action="store_true")
    args = ap.parse_args()

    base = probe_cdp(args.cdp or None)
    print("cdp:", base)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(base)
        page = pick_gemini_page(browser)
        ok = login_ok(page)
        shot = OUT_ROOT / "cdp_login_check.png"
        OUT_ROOT.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(shot), full_page=True)
        print("screenshot:", shot)
        print("logged_in:", ok)
        if args.login_check:
            return 0 if ok else 1
        if not ok:
            return 1
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in args.product)[:80]
        out_dir = OUT_ROOT / safe
        generate_one(page, args.product, args.thumb, out_dir)
        print("output:", out_dir)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
