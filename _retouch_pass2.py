# -*- coding: utf-8 -*-
"""Pass2: stronger chart flatten + official-ref guided re-correction."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

OUT = Path(r"C:\Users\user\OneDrive\Desktop\쇼핑몰관리md\detail_image_retouch_20260726")
REF = OUT / "_official_refs"


def to_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32)


def save_rgb(arr: np.ndarray, path: Path) -> None:
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    im = Image.fromarray(arr)
    if path.suffix.lower() in (".jpg", ".jpeg"):
        im.save(path, quality=93, optimize=True)
    else:
        im.save(path, optimize=True)


def strong_chart_flatten(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    lab = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    L, a, b = lab[:, :, 0], lab[:, :, 1], lab[:, :, 2]

    # background mask: bright + low chroma in LAB a/b near 128
    chroma = np.sqrt((a - 128) ** 2 + (b - 128) ** 2)
    bg = (L > 200) & (chroma < 12)
    if bg.sum() < 500:
        bg = L > np.percentile(L, 90)

    # sample grid for illumination surface
    ys, xs = np.where(bg)
    # downsample samples
    step = max(1, len(xs) // 8000)
    xs_s, ys_s, zs_s = xs[::step], ys[::step], L[ys[::step], xs[::step]]
    # fit plane L ≈ p0 + p1*x + p2*y + p3*x^2 + p4*y^2
    X = np.column_stack(
        [
            np.ones(len(xs_s)),
            xs_s,
            ys_s,
            xs_s**2 / w,
            ys_s**2 / h,
            xs_s * ys_s / max(w, h),
        ]
    )
    coef, *_ = np.linalg.lstsq(X, zs_s, rcond=None)
    yy, xx = np.mgrid[0:h, 0:w]
    illum = (
        coef[0]
        + coef[1] * xx
        + coef[2] * yy
        + coef[3] * (xx**2) / w
        + coef[4] * (yy**2) / h
        + coef[5] * (xx * yy) / max(w, h)
    )
    illum = np.maximum(illum, 1.0)
    target = float(np.median(L[bg]))
    L2 = L * (target / illum)
    # also neutralize a/b of background toward 128
    a2, b2 = a.copy(), b.copy()
    if bg.any():
        a_shift = 128 - float(np.median(a[bg]))
        b_shift = 128 - float(np.median(b[bg]))
        # apply stronger on bg, milder on swatches
        wgt = bg.astype(np.float32)
        wgt = cv2.GaussianBlur(wgt, (0, 0), 3)
        a2 = a + a_shift * (0.35 + 0.65 * wgt)
        b2 = b + b_shift * (0.35 + 0.65 * wgt)

    lab2 = np.stack(
        [np.clip(L2, 0, 255), np.clip(a2, 0, 255), np.clip(b2, 0, 255)], axis=2
    )
    out = cv2.cvtColor(lab2.astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)

    # push bg closer to paper white
    lab3 = cv2.cvtColor(out.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    L3, a3, b3 = lab3[:, :, 0], lab3[:, :, 1], lab3[:, :, 2]
    chroma3 = np.sqrt((a3 - 128) ** 2 + (b3 - 128) ** 2)
    bg3 = (L3 > 205) & (chroma3 < 14)
    L3[bg3] = np.minimum(L3[bg3] * 0.25 + 250 * 0.75, 255)
    a3[bg3] = a3[bg3] * 0.3 + 128 * 0.7
    b3[bg3] = b3[bg3] * 0.3 + 128 * 0.7
    lab3 = np.stack([L3, a3, b3], axis=2)
    out = cv2.cvtColor(lab3.astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)

    # mild sharpen
    blur = cv2.GaussianBlur(out, (0, 0), 0.9)
    out = np.clip(out + 0.22 * (out - blur), 0, 255)
    return out


def ref_guided(rgb: np.ndarray, ref_path: Path, strength: float = 0.3) -> np.ndarray:
    ref = to_rgb(ref_path)
    ref_s = cv2.resize(ref.astype(np.uint8), (160, 160))
    src_s = cv2.resize(rgb.astype(np.uint8), (160, 160))
    lab_r = cv2.cvtColor(ref_s, cv2.COLOR_RGB2LAB).astype(np.float32)
    lab_s = cv2.cvtColor(src_s, cv2.COLOR_RGB2LAB).astype(np.float32)

    def mean_lab(lab):
        L = lab[:, :, 0].ravel()
        m = (L > 35) & (L < 235)
        return lab.reshape(-1, 3)[m].mean(axis=0)

    delta = (mean_lab(lab_r) - mean_lab(lab_s)) * strength
    lab = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    lab += delta.reshape(1, 1, 3)
    lab = np.clip(lab, 0, 255)
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)


def pack_polish(rgb: np.ndarray) -> np.ndarray:
    """Extra glare reduce + wood unify for clover."""
    x = rgb.copy()
    hsv = cv2.cvtColor(x.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    v, s = hsv[:, :, 2], hsv[:, :, 1]
    glare = (v > 242) & (s < 45)
    # dilate glare mask slightly
    gmask = glare.astype(np.uint8) * 255
    gmask = cv2.dilate(gmask, np.ones((3, 3), np.uint8), 1)
    glare = gmask > 0
    v[glare] = v[glare] * 0.88 + 210 * 0.12
    hsv[:, :, 2] = v
    x = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
    # whitish bg
    lum = x.mean(2)
    chroma = x.max(2) - x.min(2)
    bg = (lum > 210) & (chroma < 22)
    x[bg] = x[bg] * 0.4 + np.array([250, 250, 250]) * 0.6
    return x


def main() -> None:
    # 1) re-flatten anchor color chart from curated before
    chart_before = (
        OUT / "앵커444색_풀세트" / "01_원본_before_curated" / "anchor_detail_01_colorchart.jpg"
    )
    chart_after = OUT / "앵커444색_풀세트" / "02_보정_after" / "anchor_detail_01_colorchart.jpg"
    print("chart", chart_before.exists())
    rgb = to_rgb(chart_before)
    out = strong_chart_flatten(rgb)
    # guided by lovecrafts/anchor ref if present
    anchor_refs = sorted(REF.glob("anchor_*"))
    if anchor_refs:
        # prefer larger files
        anchor_refs = sorted(anchor_refs, key=lambda p: -p.stat().st_size)
        out = ref_guided(out, anchor_refs[0], 0.18)
        print("anchor ref", anchor_refs[0].name)
    save_rgb(out, chart_after)
    print("saved chart")

    # 2) clover re-correction with dealer same-SKU image
    clover_before = (
        OUT / "크로바_대형수틀_57-550" / "01_원본_before_curated" / "clover_detail_01_57-550.jpg"
    )
    clover_after = OUT / "크로바_대형수틀_57-550" / "02_보정_after" / "clover_detail_01_57-550.jpg"
    # start from previous after or before
    base = to_rgb(clover_before)
    # first pass polish
    from _retouch_thread_details import retouch_product_pack

    out = retouch_product_pack(base)
    out = pack_polish(out)
    clover_refs = [p for p in REF.glob("clover_jp_57-550*") if p.stat().st_size > 10000]
    if clover_refs:
        out = ref_guided(out, clover_refs[0], 0.32)
        print("clover ref", clover_refs[0].name)
    save_rgb(out, clover_after)

    # catalog too
    for name in ("clover_catalog_main.jpg", "clover_catalog_list.jpg"):
        src = OUT / "크로바_대형수틀_57-550" / "01_원본_before_curated" / name
        dst = OUT / "크로바_대형수틀_57-550" / "02_보정_after" / name
        if not src.exists():
            continue
        o = retouch_product_pack(to_rgb(src))
        if clover_refs:
            o = ref_guided(o, clover_refs[0], 0.28)
        save_rgb(o, dst)
        print("saved", name)

    # 3) anchor other detail pages mild ref guide from pass1 after
    if anchor_refs:
        for name in (
            "anchor_detail_02_anc1.jpg",
            "anchor_detail_03_anc2.jpg",
            "anchor_detail_04_anc3.jpg",
            "anchor_catalog_main.jpg",
        ):
            src = OUT / "앵커444색_풀세트" / "01_원본_before_curated" / name
            dst = OUT / "앵커444색_풀세트" / "02_보정_after" / name
            if not src.exists():
                continue
            from _retouch_thread_details import retouch_photo_composite, retouch_catalog

            fn = retouch_catalog if "catalog" in name else retouch_photo_composite
            o = fn(to_rgb(src))
            o = ref_guided(o, anchor_refs[0], 0.2)
            save_rgb(o, dst)
            print("saved", name)

    # update manifest note
    note = {
        "pass2": True,
        "anchor_ref": str(anchor_refs[0].relative_to(OUT)) if anchor_refs else None,
        "clover_ref": str(clover_refs[0].relative_to(OUT)) if clover_refs else None,
        "actions": [
            "colorchart strong 2D illumination flatten + bg neutralize",
            "clover same-SKU dealer ref guided + glare polish",
            "anchor detail ref-guided mild LAB match",
        ],
    }
    (OUT / "retouch_pass2.json").write_text(
        json.dumps(note, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("DONE pass2")


if __name__ == "__main__":
    main()
