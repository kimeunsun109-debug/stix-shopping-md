# -*- coding: utf-8 -*-
"""2x2 합성 이미지를 4분할 패널로 저장."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def split_quad(src: Path, out_dir: Path, prefix: str = "") -> list[Path]:
    img = Image.open(src).convert("RGB")
    w, h = img.size
    if w != h:
        raise ValueError(f"expected square composite, got {w}x{h}: {src}")
    half = w // 2
    boxes = [
        (0, 0, half, half),
        (half, 0, w, half),
        (half, half, w, h),
        (0, half, half, h),
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i, box in enumerate(boxes, start=1):
        crop = img.crop(box)
        dest = out_dir / f"{prefix}{i:02d}.jpg"
        crop.save(dest, quality=92, subsampling=0)
        written.append(dest)
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description="Split 2x2 detail composite into four JPEG panels.")
    ap.add_argument("composite", type=Path, help="상세페이지_4분할_합성.jpg 등 1:1 합성 파일")
    ap.add_argument("-o", "--out-dir", type=Path, required=True, help="4분할 패널 출력 폴더")
    ap.add_argument("--prefix", default="", help="파일명 접두사 (예: 01_)")
    args = ap.parse_args()
    paths = split_quad(args.composite, args.out_dir, prefix=args.prefix)
    for p in paths:
        print(p, p.stat().st_size)


if __name__ == "__main__":
    main()
