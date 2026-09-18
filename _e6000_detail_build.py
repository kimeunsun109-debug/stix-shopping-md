# -*- coding: utf-8 -*-
"""E6000 상세페이지용 제품사진 정리 · HTML 출력 경로 확인."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent
ASSETS = Path(r"C:\Users\user\.cursor\projects\C-Users-user-stix-shopping-md\assets")
OUT = ROOT / "detail_pages" / "e6000" / "images"

SOURCES = {
    "usa_e6000": ASSETS / "99538466-B1C8-454A-BC13-8150695B8263_L0_001.jpg",
    "e6000_110ml": ASSETS / "CE924CD2-86BD-4EC6-A46F-C5A7A30F77FB_L0_001.jpg",
    "e6000_30ml": ASSETS / "72D8B26D-CA7C-4779-BFAB-EB963F265EB2_L0_001.jpg",
}


def _enhance(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB")
    rgb = ImageEnhance.Contrast(rgb).enhance(1.06)
    rgb = ImageEnhance.Color(rgb).enhance(1.04)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.12)
    return rgb


def _trim_overlay_text(img: Image.Image, bottom_ratio: float = 0.14) -> Image.Image:
    w, h = img.size
    crop_h = int(h * (1 - bottom_ratio))
    return img.crop((0, 0, w, crop_h))


def _on_canvas(
    product: Image.Image,
    canvas_size: tuple[int, int],
    bg: tuple[int, int, int] = (245, 245, 247),
    scale: float = 0.82,
) -> Image.Image:
    canvas = Image.new("RGB", canvas_size, bg)
    pw, ph = product.size
    target_w = int(canvas_size[0] * scale)
    target_h = int(ph * target_w / pw)
    if target_h > int(canvas_size[1] * scale):
        target_h = int(canvas_size[1] * scale)
        target_w = int(pw * target_h / ph)
    resized = product.resize((target_w, target_h), Image.Resampling.LANCZOS)
    shadow = Image.new("RGBA", (target_w + 40, target_h + 40), (0, 0, 0, 0))
    mask = Image.new("L", resized.size, 0)
    mask_draw = Image.new("L", resized.size, 180)
    shadow.paste((0, 0, 0, 55), (18, 22), mask_draw)
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    x = (canvas_size[0] - target_w) // 2
    y = (canvas_size[1] - target_h) // 2
    canvas_rgba = canvas.convert("RGBA")
    canvas_rgba.alpha_composite(shadow, (x - 10, y - 8))
    canvas_rgba.paste(resized, (x, y))
    return canvas_rgba.convert("RGB")


def _square_thumb(img: Image.Image, size: int = 1000) -> Image.Image:
    return ImageOps.fit(img, (size, size), method=Image.Resampling.LANCZOS, centering=(0.5, 0.45))


def build_usa_e6000() -> dict[str, Path]:
    src = Image.open(SOURCES["usa_e6000"])
    hero = _enhance(src)
    hero_path = OUT / "usa-e6000-front-back-hero.jpg"
    hero.save(hero_path, quality=94, optimize=True)

    thumb = _square_thumb(hero, 1000)
    thumb_path = OUT / "usa-e6000-thumb-1000.jpg"
    thumb.save(thumb_path, quality=94, optimize=True)

    white = _on_canvas(hero, (1200, 900), bg=(255, 255, 255), scale=0.88)
    white_path = OUT / "usa-e6000-white-hero.jpg"
    white.save(white_path, quality=94, optimize=True)
    return {"hero": hero_path, "thumb": thumb_path, "white": white_path}


def build_tube_variant(key: str, prefix: str, bottom_ratio: float = 0.14) -> dict[str, Path]:
    raw = Image.open(SOURCES[key])
    trimmed = _trim_overlay_text(raw, bottom_ratio=bottom_ratio)
    lifestyle = _enhance(trimmed)
    lifestyle_path = OUT / f"{prefix}-lifestyle.jpg"
    lifestyle.save(lifestyle_path, quality=94, optimize=True)

    white = _on_canvas(trimmed, (1200, 900), bg=(248, 248, 250), scale=0.78)
    white_path = OUT / f"{prefix}-white-hero.jpg"
    white.save(white_path, quality=94, optimize=True)

    thumb = _square_thumb(white, 1000)
    thumb_path = OUT / f"{prefix}-thumb-1000.jpg"
    thumb.save(thumb_path, quality=94, optimize=True)
    return {"lifestyle": lifestyle_path, "white": white_path, "thumb": thumb_path}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results = {
        "usa_e6000": build_usa_e6000(),
        "e6000_110ml": build_tube_variant("e6000_110ml", "e6000-110ml"),
        "e6000_30ml": build_tube_variant("e6000_30ml", "e6000-30ml", bottom_ratio=0.15),
    }
    print("E6000 detail images saved:")
    for group, paths in results.items():
        print(f"  [{group}]")
        for name, path in paths.items():
            print(f"    {name}: {path}")


if __name__ == "__main__":
    main()
