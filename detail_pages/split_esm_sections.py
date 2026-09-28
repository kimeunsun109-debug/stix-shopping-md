# -*- coding: utf-8 -*-
"""지마켓·옥션(ESM) 상세 교체용 섹션 JPEG.

2026-09-21 분할본의 교체 오류:
- 가로 1720px. ESM 상세 이미지는 860px 기준이라 초과분이 교체 실패로 이어짐.
- 마지막 브랜드 섹션(sec-10)이 스크롤 전에 찍혀 흰 화면으로 저장됨.
- 파일명에 · 가 들어가 같은 섹션이 두 파일로 남음.
- 이미지 로딩 시간 초과를 남긴 채 저장을 계속함.

이미지가 모두 로드된 뒤에만, 섹션을 화면에 넣고 가로 860px JPEG로 저장한다.
흰 화면이면 실패로 끝낸다. 쇼핑몰 업로드는 하지 않는다.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CHROME = "/usr/local/bin/google-chrome"
WIDTH = 860
SLUGS = {
    "sec-01": "hero",
    "sec-02": "size",
    "sec-03": "product",
    "sec-04": "cap",
    "sec-05": "use",
    "sec-06": "curing",
    "sec-07": "why",
    "sec-08": "spec",
    "sec-09": "faq",
    "sec-10": "brand",
}
PAGES = [
    (
        ROOT / "detail_pages/e6000/E6000_30ml_상세페이지.html",
        ROOT / "detail_pages/e6000/preview_30ml",
        "E6000_30ml",
    ),
    (
        ROOT / "detail_pages/e6000/E6000_110ml_상세페이지.html",
        ROOT / "detail_pages/e6000/preview_110ml",
        "E6000_110ml",
    ),
    (
        ROOT / "detail_pages/e6000/USA_E6000_110ml_상세페이지.html",
        ROOT / "detail_pages/e6000/preview_usa_110ml",
        "USA_E6000_110ml",
    ),
    (
        ROOT / "detail_pages/b6000/B6000_15ml_상세페이지.html",
        ROOT / "detail_pages/b6000/preview_15ml",
        "B6000_15ml",
    ),
]


def _is_blank(path: Path) -> bool:
    im = Image.open(path).convert("L")
    lo, hi = im.getextrema()
    # 거의 단색 흰색이면 이전 sec-10 교체 오류와 같다.
    return lo > 245 and hi > 250


def _fit_width(path: Path) -> tuple[int, int]:
    im = Image.open(path).convert("RGB")
    if im.width != WIDTH:
        height = max(1, round(im.height * WIDTH / im.width))
        im = im.resize((WIDTH, height), Image.Resampling.LANCZOS)
        im.save(path, "JPEG", quality=90, optimize=True)
    return im.width, im.height


def _clear_old(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.iterdir():
        if old.suffix.lower() in {".jpg", ".jpeg", ".json"}:
            old.unlink()


def split_page(page, html: Path, out_dir: Path, base: str) -> dict:
    if not html.is_file():
        raise FileNotFoundError(html)
    _clear_old(out_dir)
    page.goto(html.as_uri(), wait_until="load", timeout=60_000)
    page.wait_for_function(
        """() => {
            const imgs = Array.from(document.images);
            return imgs.every((img) => img.complete && img.naturalWidth > 0);
        }""",
        timeout=30_000,
    )
    page.evaluate("() => document.fonts && document.fonts.ready")
    sections = page.locator("section.capture-area")
    count = sections.count()
    if count != 10:
        raise RuntimeError(f"{html.name}: 섹션 {count}개 (10개여야 함)")

    saved = []
    for i in range(count):
        el = sections.nth(i)
        section_id = el.get_attribute("id") or f"sec-{i+1:02d}"
        slug = SLUGS.get(section_id, f"s{i+1:02d}")
        title = el.locator("h1, h2").first.inner_text().replace("\n", " ").strip()
        el.scroll_into_view_if_needed()
        page.wait_for_timeout(150)
        name = f"{base}_{i+1:02d}_{slug}.jpg"
        dest = out_dir / name
        el.screenshot(path=str(dest), type="jpeg", quality=90)
        width, height = _fit_width(dest)
        if width != WIDTH:
            raise RuntimeError(f"{name}: 가로 {width}px")
        if _is_blank(dest):
            raise RuntimeError(f"{name}: 흰 화면. 이전 sec-10 교체 오류와 같음")
        saved.append(
            {
                "index": i + 1,
                "section_id": section_id,
                "title": title,
                "file": name,
                "width": width,
                "height": height,
                "bytes": dest.stat().st_size,
                "status": "saved",
            }
        )

    report = {
        "html": str(html.relative_to(ROOT)),
        "out_dir": str(out_dir.relative_to(ROOT)),
        "base_name": base,
        "width": WIDTH,
        "section_count": count,
        "saved_count": len(saved),
        "sections": saved,
        "errors": [],
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "note": "ESM 상세 교체용 860px. 흰 화면·가로 초과·특수문자 파일명을 고친 재분할.",
    }
    (out_dir / "split_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> int:
    chrome = Path(CHROME)
    if not chrome.is_file():
        print(f"chrome 없음: {CHROME}", file=sys.stderr)
        return 1
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=str(chrome),
            args=["--no-sandbox", "--disable-dev-shm-usage", "--hide-scrollbars"],
        )
        context = browser.new_context(
            viewport={"width": WIDTH, "height": 1400},
            device_scale_factor=1,
        )
        page = context.new_page()
        try:
            for html, out_dir, base in PAGES:
                report = split_page(page, html, out_dir, base)
                print(f"{base}: {report['saved_count']}장 → {out_dir.relative_to(ROOT)}")
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
