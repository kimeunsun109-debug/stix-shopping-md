# -*- coding: utf-8 -*-
"""면사 447색상 택1 (product_no=61) 상세 이미지 수집·보정."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(r"C:\Users\user\OneDrive\Desktop\쇼핑몰관리md")
OUT = ROOT / "detail_image_retouch_20260726" / "면사447색_택1"
PAGE = (
    "https://makehomedeco.co.kr/product/"
    "8m-면사-자수실-447색상-택1-프랑스자수-컬러-수예실/61/category/47/display/1/"
)
PAGE_ALT = "https://makehomedeco.co.kr/product/detail.html?product_no=61"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def abs_url(u: str) -> str:
    u = u.strip().strip('"').strip("'")
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return "https://makehomedeco.co.kr" + u
    if u.startswith("http"):
        return u
    return "https://makehomedeco.co.kr/" + u.lstrip("./")


def download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        if len(data) < 2000:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except Exception as e:
        print("FAIL", url, e)
        return False


def extract_imgs(html: str) -> list[str]:
    # detail block
    m = re.search(
        r'id="prdDetail".*?(?=<div id="prdInfo"|id="prdReview"|xans-product-relation)',
        html,
        flags=re.S | re.I,
    )
    chunk = m.group(0) if m else html
    urls: list[str] = []
    for pat in [
        r'(?:src|ec-data-src)=["\']([^"\']+)["\']',
        r'(/web/(?:upload|home%20-1|home|product)[^"\'\s]+\.(?:jpg|jpeg|png|webp))',
        r'(https?://[^"\'\s]+?/web/(?:upload|product|home)[^"\'\s]+\.(?:jpg|jpeg|png|webp))',
    ]:
        for hit in re.findall(pat, chunk, flags=re.I):
            urls.append(abs_url(hit))
    # catalog big
    for hit in re.findall(
        r'<img[^>]+class="[^"]*BigImage[^"]*"[^>]+src=["\']([^"\']+)["\']',
        html,
        flags=re.I,
    ):
        urls.append(abs_url(hit))
    for hit in re.findall(
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]+class="[^"]*BigImage',
        html,
        flags=re.I,
    ):
        urls.append(abs_url(hit))
    # list thumbs in detail too
    skip = (
        "icon",
        "btn_",
        "foot_",
        "arr_",
        "logo",
        "blank",
        "loading",
        "sns_",
        "echosting",
        "cafe24.com/skin",
        "cafe24.com/design",
        "cafe24.com/images",
        "favicon",
        "pdi_sold",
        "mileage",
        "common/img",
    )
    seen: list[str] = []
    for u in urls:
        low = u.lower()
        if any(s in low for s in skip):
            continue
        if not re.search(r"\.(jpg|jpeg|png|webp)(\?|$)", low):
            continue
        if u not in seen:
            seen.append(u)
    return seen


def to_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32)


def save_rgb(arr: np.ndarray, path: Path) -> None:
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.fromarray(arr)
    if path.suffix.lower() in (".jpg", ".jpeg"):
        im.save(path, quality=92, optimize=True)
    else:
        im.save(path, optimize=True)


def photo_mask(rgb: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    blur = cv2.GaussianBlur(gray, (0, 0), 3)
    local_var = cv2.GaussianBlur((gray - blur) ** 2, (0, 0), 7)
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[:, :, 1]
    thr = np.percentile(local_var, 55)
    mask = (local_var > thr).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (0, 0), 4)
    flat = (local_var < np.percentile(local_var, 35)) & (sat > 80)
    mask = np.where(flat, mask * 0.15, mask)
    return np.clip(mask, 0, 1)


def flatten_illumination(rgb: np.ndarray, strength: float = 0.55) -> np.ndarray:
    lab = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    L = lab[:, :, 0]
    k = max(31, (min(rgb.shape[:2]) // 12) | 1)
    illum = cv2.GaussianBlur(L, (k, k), 0)
    illum = np.maximum(illum, 1.0)
    mean_illum = float(np.median(illum))
    lab[:, :, 0] = np.clip(L * ((mean_illum / illum) ** strength), 0, 255)
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)


def estimate_wb_gains(rgb: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    if mask is None:
        m = np.ones(rgb.shape[:2], dtype=bool)
    else:
        m = mask > 0.35
    pix = rgb[m]
    if pix.size < 1000:
        pix = rgb.reshape(-1, 3)
    lum = pix.mean(axis=1)
    chroma = pix.max(axis=1) - pix.min(axis=1)
    sel = (lum > np.percentile(lum, 70)) & (chroma < 35)
    if sel.sum() < 200:
        sel = lum > np.percentile(lum, 80)
    ref = np.maximum(pix[sel].mean(axis=0), 1.0)
    gains = np.clip(float(ref.mean()) / ref, 0.85, 1.18)
    return gains


def mild_clahe_L(rgb: np.ndarray, clip: float = 1.3) -> np.ndarray:
    lab = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB).astype(np.float32)


def unsharp(rgb: np.ndarray, amount: float = 0.28, sigma: float = 1.1) -> np.ndarray:
    blur = cv2.GaussianBlur(rgb, (0, 0), sigma)
    return np.clip(rgb + amount * (rgb - blur), 0, 255)


def retouch(rgb: np.ndarray, mode: str) -> np.ndarray:
    if mode == "catalog":
        x = flatten_illumination(rgb, 0.45)
        x = x * estimate_wb_gains(x).reshape(1, 1, 3)
        x = mild_clahe_L(x, 1.2)
        x = unsharp(x, 0.25, 1.0)
        mix = 0.8
        return rgb * (1 - mix) + x * mix

    # photo / composite detail
    mask = photo_mask(rgb)
    x = flatten_illumination(rgb, 0.5)
    x = x * estimate_wb_gains(x, mask).reshape(1, 1, 3)
    x = mild_clahe_L(x, 1.3)
    x = np.clip(x * 1.02, 0, 255)
    x = unsharp(x, 0.28, 1.1)
    m = (mask * 0.82)[..., None]
    out = rgb * (1 - m) + x * m
    out = flatten_illumination(out, 0.18)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    before = OUT / "01_원본_before"
    after = OUT / "02_보정_after"
    before.mkdir(exist_ok=True)
    after.mkdir(exist_ok=True)

    print("fetch", PAGE_ALT)
    html = get(PAGE_ALT)
    (OUT / "page_debug.html").write_text(html[:250000], encoding="utf-8")
    imgs = extract_imgs(html)
    print("found", len(imgs))
    for u in imgs:
        print(" ", u)

    sources = []
    saved: list[Path] = []
    for i, u in enumerate(imgs, 1):
        name = Path(urllib.parse.unquote(urllib.parse.urlparse(u).path)).name
        # unique
        dest = before / f"{i:02d}_{name}"
        if download(u, dest):
            print("OK", dest.name, dest.stat().st_size // 1024, "KB")
            saved.append(dest)
            sources.append({"url": u, "file": str(dest.relative_to(OUT.parent))})

    # filter tiny UI leftovers
    work = []
    for p in saved:
        try:
            im = Image.open(p)
            w, h = im.size
        except Exception:
            continue
        if w < 120 or h < 120:
            continue
        if p.stat().st_size < 8000:
            continue
        work.append(p)

    print("retouch targets", len(work))
    results = []
    for p in work:
        rgb = to_rgb(p)
        mode = "catalog" if min(rgb.shape[:2]) <= 600 and abs(rgb.shape[0] - rgb.shape[1]) < 80 else "photo"
        # tall detail -> photo
        if rgb.shape[0] > rgb.shape[1] * 1.3:
            mode = "photo"
        out = retouch(rgb, mode)
        dest = after / p.name
        save_rgb(out, dest)
        results.append(
            {
                "before": str(p.relative_to(OUT.parent)),
                "after": str(dest.relative_to(OUT.parent)),
                "mode": mode,
                "size": list(Image.open(p).size),
            }
        )
        print("retouched", p.name, mode)

    # update source list md append section
    md_path = OUT.parent / "원본출처_목록.md"
    section = [
        "",
        "## 1-b) 면사 447색상 택1 (요청 페이지 보정)",
        "",
        f"- 작업일: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 상품코드: P00000CI / product_no=61",
        f"- 상품명: 8M 면사 자수실 447색상 택1 프랑스자수 컬러 수예실",
        f"- 상세페이지: {PAGE}",
        f"- 폴더: `면사447색_택1/01_원본_before` → `면사447색_택1/02_보정_after`",
        "",
        "| Before | After | mode |",
        "|---|---|---|",
    ]
    for r in results:
        section.append(f"| `{r['before']}` | `{r['after']}` | {r['mode']} |")
    section.append("")
    if md_path.exists():
        text = md_path.read_text(encoding="utf-8")
        # replace previous 1-b if exists
        if "## 1-b)" in text:
            text = text.split("## 1-b)")[0].rstrip() + "\n"
        md_path.write_text(text + "\n".join(section), encoding="utf-8")
    else:
        md_path.write_text("\n".join(section), encoding="utf-8")

    (OUT / "manifest.json").write_text(
        json.dumps(
            {"page": PAGE, "sources": sources, "results": results},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("DONE", OUT)
    print("files", len(results))


if __name__ == "__main__":
    main()
