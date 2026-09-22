# -*- coding: utf-8 -*-
"""상세페이지 필요 폴더 원본 → 보정 JPG 변환."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent
SRC_ROOT = Path(r"C:\Users\user\OneDrive\Desktop\상세페이지사진\상세페이지 필요")
OUT = ROOT / "detail_pages" / "e6000" / "images"

MAX_WIDTH = 1400
THUMB_SIZE = 1000
JPG_QUALITY = 93


def _to_rgb(img: Image.Image, bg: tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        base = Image.new("RGB", img.size, bg)
        rgba = img.convert("RGBA")
        base.paste(rgba, mask=rgba.split()[-1])
        return base
    return img.convert("RGB")


def _retouch(img: Image.Image, *, rotate: int = 0) -> Image.Image:
    rgb = _to_rgb(img)
    if rotate:
        rgb = rgb.rotate(rotate, expand=True)
    rgb = ImageOps.autocontrast(rgb, cutoff=1)
    rgb = ImageEnhance.Brightness(rgb).enhance(1.02)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.05)
    rgb = ImageEnhance.Color(rgb).enhance(1.04)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.18)
    if rgb.width > MAX_WIDTH:
        ratio = MAX_WIDTH / rgb.width
        rgb = rgb.resize(
            (MAX_WIDTH, int(rgb.height * ratio)),
            Image.Resampling.LANCZOS,
        )
    return rgb


def _save(img: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="JPEG", quality=JPG_QUALITY, optimize=True, progressive=True)
    return path


def _thumb(img: Image.Image, path: Path) -> Path:
    square = ImageOps.fit(img, (THUMB_SIZE, THUMB_SIZE), method=Image.Resampling.LANCZOS, centering=(0.5, 0.45))
    return _save(square, path)


def _process(src: Path, dst: Path, *, rotate: int = 0, make_thumb: bool = False) -> dict[str, Path]:
    img = _retouch(Image.open(src), rotate=rotate)
    out = {"main": _save(img, dst)}
    if make_thumb:
        thumb_path = dst.with_name(dst.stem + "-thumb-1000.jpg")
        out["thumb"] = _thumb(img, thumb_path)
    return out


def build_all() -> dict[str, dict[str, Path]]:
    usa = SRC_ROOT / "usa e6000"
    g110 = SRC_ROOT / "e6000 110g"
    g30 = SRC_ROOT / "e6000 30g"

    results: dict[str, dict[str, Path]] = {}

    results["usa_e6000"] = {}
    mapping_usa = [
        (usa / "4.jpg", OUT / "usa-e6000-front-back.jpg", 0, True),
        (usa / "1.jpg", OUT / "usa-e6000-front.jpg", 0, False),
        (usa / "2.jpg", OUT / "usa-e6000-twin.jpg", 0, False),
        (usa / "3.jpg", OUT / "usa-e6000-applicator.jpg", 0, False),
        (usa / "제목 없는 디자인 (18).png", OUT / "usa-e6000-cap-detail.jpg", 0, False),
    ]
    for src, dst, rot, thumb in mapping_usa:
        results["usa_e6000"].update(_process(src, dst, rotate=rot, make_thumb=thumb))

    results["e6000_110ml"] = {}
    mapping_110 = [
        (g110 / "9.jpg", OUT / "e6000-110ml-cross.jpg", 0, True),
        (g110 / "7.png", OUT / "e6000-110ml-front.jpg", 180, False),
        (g110 / "3.png", OUT / "e6000-110ml-nozzle.jpg", 0, False),
        (g110 / "6.png", OUT / "e6000-110ml-seal.jpg", 0, False),
    ]
    for src, dst, rot, thumb in mapping_110:
        results["e6000_110ml"].update(_process(src, dst, rotate=rot, make_thumb=thumb))

    for i in range(1, 5):
        src = g110 / f"활용{i}.png"
        dst = OUT / f"e6000-110ml-use-0{i}.jpg"
        results["e6000_110ml"][f"use_{i}"] = _process(src, dst)["main"]

    results["e6000_30ml"] = {}
    mapping_30 = [
        (g30 / "제품 정면 사진.png", OUT / "e6000-30ml-front.jpg", 0, True),
        (g30 / "2.png", OUT / "e6000-30ml-angle.jpg", 0, False),
    ]
    for src, dst, rot, thumb in mapping_30:
        results["e6000_30ml"].update(_process(src, dst, rotate=rot, make_thumb=thumb))

    for i in range(1, 5):
        src = g30 / f"활용{i}.png"
        dst = OUT / f"e6000-30ml-use-0{i}.jpg"
        results["e6000_30ml"][f"use_{i}"] = _process(src, dst)["main"]

    return results


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results = build_all()
    print(f"Source: {SRC_ROOT}")
    print(f"Output: {OUT}")
    for group, paths in results.items():
        print(f"\n[{group}]")
        for name, path in paths.items():
            print(f"  {name}: {path.name}")


if __name__ == "__main__":
    main()
