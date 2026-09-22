# -*- coding: utf-8 -*-
"""상세페이지 이미지 보정 · 박스 히어로 생성."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parent
SRC = Path(r"C:\Users\user\OneDrive\Desktop\상세페이지사진\상세페이지 필요")
E6000_IMG = ROOT / "detail_pages" / "e6000" / "images"
B6000_IMG = ROOT / "detail_pages" / "b6000" / "images"
GRAY = (236, 236, 238)
BOX = (860, 620)


def _enhance(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB")
    rgb = ImageOps.autocontrast(rgb, cutoff=1)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.04)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.12)
    return rgb


def _content_bbox(im: Image.Image, gray: tuple[int, int, int] = GRAY, tol: int = 12):
    w, h = im.size
    p = im.load()
    l, t, r, b = w, h, 0, 0
    found = False
    for y in range(h):
        for x in range(w):
            c = p[x, y]
            if abs(c[0] - gray[0]) > tol or abs(c[1] - gray[1]) > tol or abs(c[2] - gray[2]) > tol:
                if not (c[0] > 238 and c[1] > 238 and c[2] > 238):
                    l = min(l, x)
                    t = min(t, y)
                    r = max(r, x)
                    b = max(b, y)
                    found = True
    return (l, t, r + 1, b + 1) if found else (0, 0, w, h)


def make_hero_box(src: Path, dst: Path, *, rotate: int = 0, pad: int = 24) -> Path:
    img = _enhance(Image.open(src))
    if rotate:
        img = img.rotate(rotate, expand=True)
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if r > 238 and g > 238 and b > 238:
                px[x, y] = GRAY
    l, t, r, b = _content_bbox(img)
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(w, r + pad)
    b = min(h, b + pad)
    cropped = img.crop((l, t, r, b))
    scale = min(BOX[0] / cropped.width, BOX[1] / cropped.height)
    nw, nh = int(cropped.width * scale), int(cropped.height * scale)
    product = cropped.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", BOX, GRAY)
    canvas.paste(product, ((BOX[0] - nw) // 2, (BOX[1] - nh) // 2))
    dst.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dst, quality=93, optimize=True)
    return dst


def save_jpg(src: Path, dst: Path, *, rotate: int = 0, max_w: int = 1400) -> Path:
    img = _enhance(Image.open(src))
    if rotate:
        img = img.rotate(rotate, expand=True)
    if img.width > max_w:
        ratio = max_w / img.width
        img = img.resize((max_w, int(img.height * ratio)), Image.Resampling.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, quality=93, optimize=True)
    return dst


def build_e6000_110() -> None:
    g = SRC / "e6000 110g"
    make_hero_box(g / "7.png", E6000_IMG / "e6000-110ml-front-box.jpg", rotate=180)
    save_jpg(g / "3.png", E6000_IMG / "e6000-110ml-angle.jpg")
    save_jpg(g / "6.png", E6000_IMG / "e6000-110ml-nozzle.jpg")
    for i in range(1, 5):
        save_jpg(g / f"활용{i}.png", E6000_IMG / f"e6000-110ml-use-0{i}.jpg")


def build_usa_e6000() -> None:
    usa_src = SRC / "usa e6000"
    front = E6000_IMG / "usa-e6000-front.jpg"
    if not front.exists() and (usa_src / "1.jpg").exists():
        save_jpg(usa_src / "1.jpg", front)
    make_hero_box(front, E6000_IMG / "usa-e6000-front-box.jpg")
    cap = usa_src / "제목 없는 디자인 (18).png"
    if cap.exists():
        save_jpg(cap, E6000_IMG / "usa-e6000-cap-detail.jpg")
    elif (E6000_IMG / "usa-e6000-applicator.jpg").exists():
        save_jpg(E6000_IMG / "usa-e6000-applicator.jpg", E6000_IMG / "usa-e6000-cap-detail.jpg")
    save_jpg(E6000_IMG / "usa-e6000-applicator.jpg", E6000_IMG / "usa-e6000-angle.jpg")
    for i in range(1, 5):
        src = E6000_IMG / f"usa e6000 use 0{i}.png"
        if src.exists():
            save_jpg(src, E6000_IMG / f"usa-e6000-use-0{i}.jpg")


def build_b6000() -> None:
    g = E6000_IMG / "B6000 15ML"
    make_hero_box(g / "b6000 15ml main.png", B6000_IMG / "b6000-15ml-front-box.jpg")
    save_jpg(g / "2.png", B6000_IMG / "b6000-15ml-angle.jpg")
    save_jpg(g / "b6000 15ml detail.jpg", B6000_IMG / "b6000-15ml-cap-detail.jpg", max_w=860)
    save_jpg(g / "활용3.png", B6000_IMG / "b6000-15ml-use-01.jpg", max_w=1200)
    e30 = ROOT / "detail_pages" / "e6000" / "images"
    for i in range(2, 5):
        src = e30 / f"e6000-30ml-use-0{i}.jpg"
        if src.exists():
            save_jpg(src, B6000_IMG / f"b6000-15ml-use-0{i}.jpg")


def main() -> None:
    build_e6000_110()
    build_usa_e6000()
    build_b6000()
    print("detail images ready")


if __name__ == "__main__":
    main()
