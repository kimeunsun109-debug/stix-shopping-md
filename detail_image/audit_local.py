# -*- coding: utf-8 -*-
"""
OneDrive 로컬 경로의 '다시제작' 폴더 품질 검수.

판정 기준 (자동):
- 4분할 패널이 512x512 이하이거나 파일이 80KB 미만 → 재생성 후보
- 썸네일/합성 누락 → 재생성 후보
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

PANEL_MAX_SIDE = 512
PANEL_MIN_BYTES = 80_000
COMPOSITE_MIN_BYTES = 200_000


@dataclass
class ProductAudit:
    folder: str
    layout: str
    has_thumb: bool
    has_composite: bool
    panel_count: int
    panel_max_side: int
    panel_min_bytes: int
    needs_regen: bool
    reasons: list[str]


def _image_meta(path: Path) -> tuple[int, int, int]:
    size = path.stat().st_size
    with Image.open(path) as im:
        w, h = im.size
    return w, h, size


def audit_product_dir(product_dir: Path) -> ProductAudit:
    reasons: list[str] = []
    thumb = product_dir / "썸네일.jpg"
    if not thumb.exists():
        thumb = product_dir / "thumb.jpg"
    composite = product_dir / "상세페이지_4분할_합성.jpg"
    split_dir = product_dir / "4분할"
    panels: list[Path] = []
    layout = "unknown"

    if split_dir.is_dir():
        layout = "4분할_subfolder"
        panels = sorted(split_dir.glob("*.jpg")) + sorted(split_dir.glob("*.png"))
    else:
        layout = "flat_01_04"
        panels = sorted(product_dir.glob("0[1-4].jpg"))

    if not thumb.is_file():
        reasons.append("missing_thumbnail")
    if not composite.is_file():
        reasons.append("missing_composite")
    if len(panels) < 4:
        reasons.append(f"panel_count_{len(panels)}")

    max_side = 0
    min_bytes = 10**9
    for p in panels[:4]:
        w, h, nbytes = _image_meta(p)
        max_side = max(max_side, w, h)
        min_bytes = min(min_bytes, nbytes)

    if panels and max_side <= PANEL_MAX_SIDE:
        reasons.append(f"low_panel_resolution_{max_side}")
    if panels and min_bytes < PANEL_MIN_BYTES:
        reasons.append(f"small_panel_bytes_{min_bytes}")
    if composite.is_file() and composite.stat().st_size < COMPOSITE_MIN_BYTES:
        reasons.append("small_composite")

    needs = bool(reasons)
    return ProductAudit(
        folder=product_dir.name,
        layout=layout,
        has_thumb=thumb.is_file(),
        has_composite=composite.is_file(),
        panel_count=len(panels),
        panel_max_side=max_side,
        panel_min_bytes=min_bytes if panels else 0,
        needs_regen=needs,
        reasons=reasons,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "root",
        type=Path,
        help=r"예: ...\상세페이지사진\짧은_구식_상세페이지\제작_산출물\다시제작",
    )
    ap.add_argument("-o", "--out", type=Path, default=Path("MD_다시제작_검수.csv"))
    ap.add_argument("--json", type=Path, default=Path("MD_다시제작_검수.json"))
    args = ap.parse_args()

    rows = [audit_product_dir(p) for p in sorted(args.root.iterdir()) if p.is_dir()]
    needs = [r for r in rows if r.needs_regen]

    args.json.write_text(
        json.dumps([asdict(r) for r in rows], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with args.out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "folder",
                "layout",
                "has_thumb",
                "has_composite",
                "panel_count",
                "panel_max_side",
                "panel_min_bytes",
                "needs_regen",
                "reasons",
            ],
        )
        w.writeheader()
        for r in rows:
            d = asdict(r)
            d["reasons"] = ";".join(r.reasons)
            w.writerow(d)

    print(f"scanned={len(rows)} needs_regen={len(needs)}")
    print(f"wrote {args.out} {args.json}")


if __name__ == "__main__":
    main()
