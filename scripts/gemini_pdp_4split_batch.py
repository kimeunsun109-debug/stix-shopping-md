#!/usr/bin/env python3
"""
Gemini 웹(이미지 생성)으로 STIX 상세페이지 4분할 합성 이미지 배치 제작.

사전 조건:
  1) Playwright + Chrome
  2) gemini.google.com 에 Google 계정 로그인 (persistent profile)

사용 예:
  python3 scripts/gemini_pdp_4split_batch.py --login-check
  python3 scripts/gemini_pdp_4split_batch.py --manifest queue.csv --limit 3
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import urllib.request

DEFAULT_PROFILE = Path("/tmp/stix-chrome-gemini-profile")
OUT_ROOT = Path("/opt/cursor/artifacts/gemini-pdp-output")
CDP_PORTS = (9222, 9233, 9223)

PANEL_HINTS = (
    "제품 구성·패키지(구성품 전체)",
    "제품 질감·디테일 클로즈업",
    "실제 사용·작업 과정",
    "완성·인테리어·활용 장면",
)


def build_prompt(product_name: str, category_hint: str = "") -> str:
    panels = "\n".join(f"  ({i}) {h}" for i, h in enumerate(PANEL_HINTS, 1))
    return f"""쇼핑몰 상세페이지용 2x2 4분할 합성 이미지, 정사각 1024x1024, 흰 배경, 프리미엄 상업 촬영.

상품: {product_name}
{('카테고리/특성: ' + category_hint) if category_hint else ''}

첨부 썸네일과 동일한 제품만 사용. 제품 형태·색·비율·로고·구성 변경 금지.
4칸 내용:
{panels}

한글 라벨은 짧게 가능. Gemini 워터마크·별 마크·AI 로고·UI 오버레이 절대 금지.
과장 광고 문구 없음."""


def infer_category(name: str) -> str:
    n = name.lower()
    rules = [
        (r"보석십자수|비즈", "보석십자수 DIY — 구성품·작업·완성작"),
        (r"자수실|dmc|앵커|보빈", "자수실 세트 — 색상·보빈·정리"),
        (r"원단|아이다|14ct|18ct|쯔바이|금사|은사", "십자수 원단 — 질감·메탈릭·수놓기"),
        (r"도구|핀셋|펜|케이스|정리함", "자수 부자재·도구 — 구성·사용"),
        (r"프랑스자수|패키지|풀키트", "프랑스자수 키트 — 입문·구성"),
    ]
    for pat, hint in rules:
        if re.search(pat, name, re.I):
            return hint
    return "공예/DIY 취미용품 — 실사 상품 촬영 스타일"


def probe_cdp_url(cdp: str | None) -> str:
    if cdp:
        url = cdp.rstrip("/")
        urllib.request.urlopen(f"{url}/json/version", timeout=3)
        return url
    for port in CDP_PORTS:
        url = f"http://127.0.0.1:{port}"
        try:
            urllib.request.urlopen(f"{url}/json/version", timeout=2)
            return url
        except Exception:
            continue
    raise RuntimeError("CDP Chrome not found on ports " + ",".join(map(str, CDP_PORTS)))


def _gemini_page(browser):
    for ctx in browser.contexts:
        for page in ctx.pages:
            if "gemini.google.com" in (page.url or ""):
                return page
    page = browser.contexts[0].new_page()
    page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=120_000)
    time.sleep(3)
    return page


def login_check_cdp(cdp_url: str) -> bool:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = _gemini_page(browser)
        time.sleep(2)
        body = page.inner_text("body")
        signed_out = "Sign in" in body and "Meet Gemini" in body
        OUT_ROOT.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(OUT_ROOT / "login_check_cdp.png"), full_page=True)
        return not signed_out


def login_check(profile: Path) -> bool:
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(profile),
            channel="chrome",
            headless=False,
            args=["--no-sandbox"],
            viewport={"width": 1400, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=120_000)
        time.sleep(4)
        body = page.inner_text("body")
        signed_out = "Sign in" in body and "Meet Gemini" in body
        shot = OUT_ROOT / "login_check.png"
        OUT_ROOT.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(shot), full_page=True)
        ctx.close()
        print("screenshot:", shot)
        return not signed_out


def run_batch_cdp(manifest: Path, cdp_url: str, limit: int | None) -> int:
    rows = list(csv.DictReader(manifest.open(encoding="utf-8-sig")))
    if limit:
        rows = rows[:limit]
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    ok = 0
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = _gemini_page(browser)
        if "Sign in" in page.inner_text("body"):
            print("ERROR: Gemini 미로그인 (CDP)", file=sys.stderr)
            return 1
        for row in rows:
            product = row.get("product_name") or row.get("name") or ""
            thumb = Path(os.path.expandvars(row.get("thumbnail_path") or ""))
            out_dir = OUT_ROOT / re.sub(r"[^\w가-힣.-]+", "_", product)[:80]
            out_dir.mkdir(parents=True, exist_ok=True)
            prompt = build_prompt(product, infer_category(product))
            (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
            try:
                page.get_by_text("Images", exact=False).first.click(timeout=8000)
                time.sleep(2)
            except PlaywrightTimeout:
                pass
            if thumb.is_file():
                try:
                    page.locator('input[type="file"]').first.set_input_files(str(thumb))
                    time.sleep(2)
                except PlaywrightTimeout:
                    print(f"WARN: 파일 업로드 UI 없음 — {product}", file=sys.stderr)
            try:
                box = page.locator("textarea, div[contenteditable=true]").first
                box.click(timeout=10_000)
                box.fill(prompt)
                page.keyboard.press("Enter")
                time.sleep(45)
                page.screenshot(path=str(out_dir / "result_screenshot.png"), full_page=True)
                ok += 1
                print("done:", product)
            except PlaywrightTimeout as e:
                print(f"FAIL: {product} — {e}", file=sys.stderr)
    print(f"done {ok}/{len(rows)}")
    return 0 if ok else 2


def run_batch(manifest: Path, profile: Path, limit: int | None) -> int:
    rows = list(csv.DictReader(manifest.open(encoding="utf-8-sig")))
    if limit:
        rows = rows[:limit]
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    ok = 0
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(profile),
            channel="chrome",
            headless=False,
            args=["--no-sandbox"],
            viewport={"width": 1400, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=120_000)
        time.sleep(3)
        if "Sign in" in page.inner_text("body"):
            print("ERROR: Gemini 미로그인. 브라우저에서 로그인 후 다시 실행하세요.", file=sys.stderr)
            ctx.close()
            return 1
        for row in rows:
            product = row.get("product_name") or row.get("name") or ""
            thumb = Path(row.get("thumbnail_path") or "")
            out_dir = OUT_ROOT / re.sub(r"[^\w가-힣.-]+", "_", product)[:80]
            out_dir.mkdir(parents=True, exist_ok=True)
            prompt = build_prompt(product, infer_category(product))
            (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
            try:
                # UI는 Gemini 업데이트에 따라 달라질 수 있음 — Images 모드 진입 시도
                page.get_by_text("Images", exact=False).first.click(timeout=8000)
                time.sleep(2)
            except PlaywrightTimeout:
                pass
            if thumb.is_file():
                try:
                    page.locator('input[type="file"]').first.set_input_files(str(thumb))
                    time.sleep(2)
                except PlaywrightTimeout:
                    print(f"WARN: 파일 업로드 UI 없음 — {product}", file=sys.stderr)
            try:
                box = page.locator("textarea, div[contenteditable=true]").first
                box.click(timeout=10_000)
                box.fill(prompt)
                page.keyboard.press("Enter")
                time.sleep(45)
                page.screenshot(path=str(out_dir / "result_screenshot.png"), full_page=True)
                ok += 1
                print("queued:", product)
            except PlaywrightTimeout as e:
                print(f"FAIL: {product} — {e}", file=sys.stderr)
        ctx.close()
    print(f"done {ok}/{len(rows)}")
    return 0 if ok else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--cdp", default="", help="CDP URL e.g. http://127.0.0.1:9222 (auto-probe if empty)")
    ap.add_argument("--manifest", type=Path, help="CSV: product_name,thumbnail_path")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--login-check", action="store_true")
    args = ap.parse_args()
    if args.login_check:
        if args.cdp or _probe_optional_cdp():
            cdp_url = probe_cdp_url(args.cdp or None)
            ok = login_check_cdp(cdp_url)
        else:
            ok = login_check(args.profile)
        print("logged_in:", ok)
        return 0 if ok else 1
    if not args.manifest:
        ap.error("--manifest 또는 --login-check 필요")
    try:
        cdp_url = probe_cdp_url(args.cdp or None)
        print("using CDP:", cdp_url)
        return run_batch_cdp(args.manifest, cdp_url, args.limit)
    except RuntimeError:
        return run_batch(args.manifest, args.profile, args.limit)


def _probe_optional_cdp() -> bool:
    try:
        probe_cdp_url(None)
        return True
    except RuntimeError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
