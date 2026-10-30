# -*- coding: utf-8 -*-
"""제작_산출물 폴더(콜라주 이미지)에서 상품별 상세페이지를 일괄 생성한다.

사용 예
    python3 -m detail_page.build --src /path/to/제작_산출물 --out detail_page_out
    python3 -m detail_page.build --src ... --out ... --only 01_ 13031829_ --no-render

출력 (--out)
    pages/<slug>.html        편집 가능한 HTML (분할 저장 버튼 포함)
    images/<slug>_*.jpg      패널 분리 이미지
    slices/<slug>/NN_*.jpg   섹션별 분할 이미지 (스토어 업로드용)
    long/<slug>.jpg          세로 한 장 합본
    index.html               전체 인덱스
    QA_REPORT.md             확인이 필요한 상품 목록
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from .catalog import PRODUCTS, Product
from .render import PAGE_W, SECTION_IDS, prepare_images, render_html, render_index

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
CHROME_CANDIDATES = ["/usr/local/bin/google-chrome", "/usr/bin/google-chrome", "/usr/bin/chromium"]


def slug_of(key: str) -> str:
    return key.rstrip("_") or key


def find_files(src: Path, prod: Product):
    files = sorted(p for p in src.iterdir() if p.suffix.lower() in IMG_EXT and p.name.startswith(prod.key))
    if not files:
        return None, None
    if prod.hero_key:
        hero = next((f for f in files if f.stem == prod.hero_key), None)
        rest = [f for f in files if f != hero]
        return (rest[0] if rest else None), hero
    return files[0], None


def image_warnings(path: Path) -> list[str]:
    w, h = Image.open(path).size
    warn = []
    if min(w, h) <= 800:
        warn.append(f"원본 해상도 낮음 ({w}x{h}) — 패널당 약 {w // 2}px, 확대 시 흐릿할 수 있음")
    if abs(w - h) > 40:
        warn.append(f"정사각형이 아닌 원본 ({w}x{h}) — 패널이 정사각형으로 중앙 크롭됨")
    return warn


def launch_browser(pw):
    for exe in CHROME_CANDIDATES:
        if Path(exe).exists():
            return pw.chromium.launch(executable_path=exe, args=["--no-sandbox"])
    return pw.chromium.launch(args=["--no-sandbox"])


def screenshot_slices(page, html_path: Path, out_dir: Path, slug: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    page.goto(html_path.resolve().as_uri(), wait_until="load")
    page.evaluate("document.fonts && document.fonts.ready")
    paths = []
    for sid, label in SECTION_IDS:
        p = out_dir / f"{label}.png"
        page.locator(f"#{sid}").screenshot(path=str(p))
        paths.append(p)
    jpgs = []
    for p in paths:
        j = p.with_suffix(".jpg")
        Image.open(p).convert("RGB").save(j, quality=90, optimize=True)
        p.unlink()
        jpgs.append(j)
    return jpgs


def stack_long(slices: list[Path], dest: Path, thumb: Path):
    ims = [Image.open(p).convert("RGB") for p in slices]
    w = ims[0].width
    canvas = Image.new("RGB", (w, sum(i.height for i in ims)), "white")
    y = 0
    for im in ims:
        canvas.paste(im, (0, y))
        y += im.height
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest, quality=88, optimize=True)
    t = canvas.crop((0, 0, w, int(w * 4 / 3))).resize((300, 400), Image.LANCZOS)
    thumb.parent.mkdir(parents=True, exist_ok=True)
    t.save(thumb, quality=80)


def write_report(out: Path, rows: list[dict], missing: list[str]):
    flagged = [r for r in rows if r["qa"] or r["warn"]]
    lines = [
        "# 상세페이지 생성 QA 리포트",
        "",
        f"- 생성 상품: **{len(rows)}종** (섹션 6장 + 세로 합본 각 1장)",
        f"- 확인 필요: **{len(flagged)}종**",
        "",
        "상세 카피는 **상품명에 적힌 사실(수량·규격·색상)만** 단정하고, 이미지에서 확인한 내용(색감·모티브 등)은 포인트/구성 설명에 한정해 사용했습니다. 활용 컷 캡션은 이미지와 어긋나지 않도록 중립 문구입니다.",
        "아래 상품은 업로드 전에 이미지 또는 상품명을 한 번 더 확인하세요.",
        "",
        "| 상품 | 구분 | 내용 |",
        "|---|---|---|",
    ]
    for r in flagged:
        name = r["name"].replace("<br>", " ")
        for q in ([r["qa"]] if r["qa"] else []):
            lines.append(f"| {r['slug']} {name} | 이미지/상품명 불일치 | {q} |")
        for w in r["warn"]:
            lines.append(f"| {r['slug']} {name} | 이미지 품질 | {w} |")
    if missing:
        lines += ["", "## 카탈로그에 있으나 이미지를 찾지 못한 항목", ""] + [f"- {m}" for m in missing]
    (out / "QA_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, help="콜라주 이미지가 있는 폴더(제작_산출물)")
    ap.add_argument("--out", default="detail_page_out")
    ap.add_argument("--only", nargs="*", help="특정 key(접두)만 생성")
    ap.add_argument("--no-render", action="store_true", help="HTML/이미지만 만들고 JPG 분할은 생략")
    a = ap.parse_args(argv)

    src, out = Path(a.src), Path(a.out)
    if not src.is_dir():
        print(f"소스 폴더가 없습니다: {src}", file=sys.stderr)
        return 2
    for d in ("pages", "images", "slices", "long", "long_thumb"):
        (out / d).mkdir(parents=True, exist_ok=True)

    targets = [p for p in PRODUCTS if not a.only or p.key in a.only]
    rows, missing, jobs = [], [], []
    for prod in targets:
        collage, hero = find_files(src, prod)
        if collage is None:
            missing.append(prod.key)
            continue
        slug = slug_of(prod.key)
        imgs = prepare_images(prod, collage, hero, out / "images", slug)
        html_path = out / "pages" / f"{slug}.html"
        html_path.write_text(render_html(prod, imgs, slug, with_tools=True), encoding="utf-8")
        shot_path = out / "pages" / f".{slug}.capture.html"
        shot_path.write_text(render_html(prod, imgs, slug, with_tools=False), encoding="utf-8")
        rows.append({"slug": slug, "name": prod.name, "qa": prod.qa, "warn": image_warnings(collage)})
        jobs.append((slug, shot_path))

    if not a.no_render and jobs:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = launch_browser(pw)
            ctx = browser.new_context(viewport={"width": PAGE_W + 40, "height": 1200}, device_scale_factor=2, locale="ko-KR")
            page = ctx.new_page()
            for n, (slug, shot_path) in enumerate(jobs, 1):
                slices = screenshot_slices(page, shot_path, out / "slices" / slug, slug)
                stack_long(slices, out / "long" / f"{slug}.jpg", out / "long_thumb" / f"{slug}.jpg")
                print(f"[{n}/{len(jobs)}] {slug}")
            browser.close()

    for _, shot_path in jobs:
        shot_path.unlink(missing_ok=True)

    (out / "index.html").write_text(render_index(rows), encoding="utf-8")
    write_report(out, rows, missing)
    print(f"완료: {len(rows)}종 / 누락 {len(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
