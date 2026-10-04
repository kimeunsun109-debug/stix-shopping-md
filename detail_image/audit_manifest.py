# -*- coding: utf-8 -*-
"""
OneDrive Graph `list_drive_items` 결과(JSON)로 다시제작 SKU 검수표 생성.

입력 JSON 형식: {"value": [{"name", "size", "folder": {"childCount"}, "id"}, ...]}

판정:
- childCount==5 → flat 레이아웃(01~04+thumb), 합성/4분할 폴더 없음 → 재생성 1순위
- childCount==3 → 표준 레이아웃 → 패널 해상도는 로컬 audit_local.py로 2차 검수
- total size < 120_000 (flat) → 극저용량 실패
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Row:
    folder: str
    item_id: str
    child_count: int
    total_bytes: int
    layout: str
    priority: int
    needs_regen: bool
    reasons: list[str]


def audit_entry(item: dict) -> Row:
    name = item["name"]
    size = int(item.get("size") or 0)
    child = int((item.get("folder") or {}).get("childCount") or 0)
    item_id = item.get("id", "")
    reasons: list[str] = []
    priority = 3

    if child == 5:
        layout = "flat_01_04"
        reasons.append("flat_layout_missing_composite_folder")
        priority = 1
        if size < 120_000:
            reasons.append("critically_small_folder")
            priority = 0
        elif size < 550_000:
            reasons.append("small_folder_bytes")
            priority = 1
    elif child == 3:
        layout = "4분할_subfolder"
        if size < 900_000:
            reasons.append("review_folder_size")
            priority = 2
    else:
        layout = "unknown"
        reasons.append(f"unexpected_child_count_{child}")
        priority = 1

    needs = bool(reasons) and layout != "4분할_subfolder" or "review_folder_size" in reasons
    if layout == "4분할_subfolder" and "review_folder_size" not in reasons:
        needs = False

    return Row(
        folder=name,
        item_id=item_id,
        child_count=child,
        total_bytes=size,
        layout=layout,
        priority=priority,
        needs_regen=needs,
        reasons=reasons if reasons else ["ok"],
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("listing_json", type=Path, help="Graph list_drive_items 응답 JSON")
    ap.add_argument("-o", "--out", type=Path, default=Path("MD_다시제작_검수.csv"))
    ap.add_argument("--json", type=Path, default=Path("MD_다시제작_검수.json"))
    args = ap.parse_args()

    data = json.loads(args.listing_json.read_text(encoding="utf-8"))
    items = sorted(data.get("value", []), key=lambda x: x.get("name", ""))
    rows = [audit_entry(i) for i in items if i.get("folder")]

    args.json.write_text(
        json.dumps([asdict(r) for r in rows], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with args.out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "folder",
                "item_id",
                "child_count",
                "total_bytes",
                "layout",
                "priority",
                "needs_regen",
                "reasons",
            ],
        )
        w.writeheader()
        for r in rows:
            d = asdict(r)
            d["reasons"] = ";".join(r.reasons)
            w.writerow(d)

    needs = [r for r in rows if r.needs_regen]
    flat = [r for r in rows if r.layout == "flat_01_04"]
    print(f"scanned={len(rows)} needs_regen={len(needs)} flat_layout={len(flat)}")
    print(f"wrote {args.out} {args.json}")


if __name__ == "__main__":
    main()
