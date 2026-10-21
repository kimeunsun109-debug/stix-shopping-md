#!/usr/bin/env python3
"""Scan a product root folder and write gemini_pdp manifest CSV (Windows paths)."""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

THUMB_NAMES = ("thumb.jpeg", "thumb.jpg", "썸네일.jpg", "thumbnail.jpg", "썸네일.png")


def find_thumb(product_dir: Path) -> Path | None:
    for name in THUMB_NAMES:
        p = product_dir / name
        if p.is_file():
            return p
    for sub in ("source", "원본", "썸네일", "thumb"):
        d = product_dir / sub
        if not d.is_dir():
            continue
        for name in THUMB_NAMES:
            p = d / name
            if p.is_file():
                return p
    imgs = sorted(
        [
            f
            for f in product_dir.iterdir()
            if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ],
        key=lambda x: x.name.lower(),
    )
    return imgs[0] if imgs else None


def to_manifest_path(path: Path, use_userprofile: bool) -> str:
    if not use_userprofile or os.name != "nt":
        return str(path)
    home = Path.home()
    try:
        rel = path.resolve().relative_to(home)
        return "%USERPROFILE%\\" + str(rel).replace("/", "\\")
    except ValueError:
        return str(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--root",
        type=Path,
        required=True,
        help=r"e.g. %%USERPROFILE%%\OneDrive\Desktop\...\다시제작",
    )
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--no-userprofile", action="store_true")
    args = ap.parse_args()

    root = Path(os.path.expandvars(str(args.root))).resolve()
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")

    rows: list[dict[str, str]] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if not child.is_dir():
            continue
        thumb = find_thumb(child)
        if not thumb:
            print("skip (no image):", child.name)
            continue
        rows.append(
            {
                "product_name": child.name,
                "thumbnail_path": to_manifest_path(thumb, not args.no_userprofile),
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["product_name", "thumbnail_path"])
        w.writeheader()
        w.writerows(rows)

    print(f"wrote {len(rows)} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
