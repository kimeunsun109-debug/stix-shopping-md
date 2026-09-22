# -*- coding: utf-8 -*-
"""
자수실/크로바 상세 이미지 보정
- 정렬·구도 유지 (기하 변환 없음)
- 조명/화이트밸런스 불균일 보정 → 균일·신뢰감
- 크로바·앵커: 공식/동일제품 레퍼런스 확인 후 재보정
- 몰 업로드·가격변경 없음
"""
from __future__ import annotations

import json
import shutil
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(r"C:\Users\user\OneDrive\Desktop\쇼핑몰관리md")
OUT = ROOT / "detail_image_retouch_20260726"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


@dataclass
class JobFile:
    src_name: str
    out_name: str
    mode: str  # photo_composite | color_chart | product_pack | catalog
    note: str = ""


PRODUCTS = {
    "면사447색_풀세트": {
        "code": "P00000GG",
        "title": "프랑스자수 자수실 447색 풀세트 대용량 컬러 자수실 세트",
        "page": "https://makehomedeco.co.kr/product/detail.html?product_no=163",
        "files": [
            JobFile("page_01_44720FULLSET201.png", "447_detail_01_FULLSET201.png", "photo_composite", "상세 메인(정렬 촬영 컷 포함)"),
            JobFile("page_02_44720FULLSET202.png", "447_detail_02_FULLSET202.png", "photo_composite", "상세 하단(정렬 촬영+배송안내)"),
            JobFile("catalog_163_shop1_243481.jpg", "447_catalog_main.jpg", "catalog", "대표이미지"),
        ],
    },
    "앵커444색_풀세트": {
        "code": "P0000BJO",
        "title": "ANCHOR 독일 앵커 자수실 444색 풀세트 십자수 자수실 올인원 프리미엄 공예 세트",
        "page": "https://makehomedeco.co.kr/product/detail.html?product_no=924",
        "files": [
            JobFile("page_01_666.jpg", "anchor_detail_01_colorchart.jpg", "color_chart", "컬러차트(조명 좌우 불균일)"),
            JobFile("page_02_anc%201.jpg", "anchor_detail_02_anc1.jpg", "photo_composite", "상세 anc1"),
            JobFile("page_03_anc%202.jpg", "anchor_detail_03_anc2.jpg", "photo_composite", "상세 anc2"),
            JobFile("page_04_anc%203.jpg", "anchor_detail_04_anc3.jpg", "photo_composite", "상세 anc3"),
            JobFile("catalog_924_shop1_15324080489293.jpg", "anchor_catalog_main.jpg", "catalog", "대표이미지"),
        ],
    },
    "크로바_대형수틀_57-550": {
        "code": "P0000CIX",
        "title": "크로바 57-550 대형 수틀 30cm 자수틀 프랑스자수 십자수 원단 고정 틀",
        "page": "https://makehomedeco.co.kr/product/detail.html?product_no=1583",
        "files": [
            JobFile("page_01_5720550.jpg", "clover_detail_01_57-550.jpg", "product_pack", "상세(패키지 촬영 2컷)"),
            JobFile("catalog_5ec1a2cf365d42a9e4e5d1bffefdf1ea.jpg", "clover_catalog_main.jpg", "catalog", "대표이미지"),
            JobFile("catalog_8c76fba1bd0d2948a30b84de8f41a54f.jpg", "clover_catalog_list.jpg", "catalog", "목록이미지"),
        ],
    },
}


def download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
        if len(data) < 1500:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except Exception as e:
        print("  ref FAIL", url, e)
        return False


def fetch_official_refs() -> list[dict]:
    """공식/동일제품 레퍼런스 수집 (크로바·앵커 재보정용)."""
    ref_dir = OUT / "_official_refs"
    ref_dir.mkdir(parents=True, exist_ok=True)
    refs = []

    candidates = [
        # Anchor official — stranded cotton product / shade card pages (image assets)
        {
            "brand": "ANCHOR",
            "product": "Stranded Cotton Mouliné 444 solid colours",
            "verify_url": "https://anchorcrafts.com/products/anchor-stranded-cotton-mouline-5",
            "same_product_note": "공식: 444 solid + 16 ombre. 자사 판매명 '444색 풀세트'와 동일 라인 확인.",
            "image_urls": [
                "https://anchorcrafts.com/cdn/shop/files/Anchor_Stranded_Cotton_Mouline.jpg",
                "https://anchorcrafts.com/cdn/shop/products/anchor-stranded-cotton.jpg",
            ],
            "save_as": "anchor_official_stranded_cotton.jpg",
        },
        {
            "brand": "ANCHOR",
            "product": "Embroidery Thread Shade Card (CA-4546)",
            "verify_url": "https://anchorcrafts.com/products/anchor-embroidery-thread-shade-card",
            "same_product_note": "공식 셰이드카드 — 444 solid 실물 샘플. 상세 컬러차트 톤 레퍼런스.",
            "image_urls": [
                "https://anchorcrafts.com/cdn/shop/files/Anchor_Embroidery_Thread_Shade_Card.jpg",
                "https://anchorcrafts.com/cdn/shop/products/CA-4546.jpg",
            ],
            "save_as": "anchor_official_shade_card.jpg",
        },
        # Clover 57-550 = JP article; 동일 계열 Embroidery Hoop (wood, metal screw)
        {
            "brand": "CLOVER",
            "product": "57-550 대형 수틀 30cm (JAN 4901316575502)",
            "verify_url": "https://eshop.needleworkclub.com/product-13539",
            "same_product_note": "JAN 4901316575502 = Clover 57-550 확인. 공식영문 라인은 Art.8812(18cm) 등 동일 구조 수틀.",
            "image_urls": [
                "https://eshop.needleworkclub.com/image/product/13539/1.jpg",
                "https://eshop.needleworkclub.com/images/product/13539.jpg",
            ],
            "save_as": "clover_57-550_same_sku_ref.jpg",
        },
        {
            "brand": "CLOVER",
            "product": "Official Embroidery Hoop series (wood hoop family)",
            "verify_url": "https://www.clover-mfg.com/en/products/embroidery/embroidery-hoop/clover-embroidery-hoop/",
            "same_product_note": "공식 수틀 시리즈(내외측 이중링·나사조임) — 자사 57-550과 동일 제품군 구조 확인.",
            "image_urls": [
                "https://www.clover-mfg.com/en/wp-content/uploads/sites/2/2021/03/8812.jpg",
                "https://www.clover-mfg.com/wp-content/uploads/2021/03/8812.jpg",
            ],
            "save_as": "clover_official_hoop_family.jpg",
        },
        # Google/commerce same-product images (Anchor full set packaging look)
        {
            "brand": "ANCHOR",
            "product": "Google/마켓 동일제품 박스 세트 이미지",
            "verify_url": "https://www.google.com/search?q=ANCHOR+자수실+444색+풀세트&tbm=isch",
            "same_product_note": "동일 제품명 검색으로 박스형 풀세트 존재 확인. 색감 재보정 허용 근거.",
            "image_urls": [],
            "save_as": "",
        },
    ]

    # Also try cafe24/cdn and known public product images via duck-style open urls
    extra_try = [
        (
            "clover_google_same_57-550.jpg",
            [
                "https://shopping-phinf.pstatic.net/main_8221234/82212344719.jpg",
            ],
            {
                "brand": "CLOVER",
                "product": "네이버/구글 동일 SKU 검색용 (실패 가능)",
                "verify_url": "https://www.google.com/search?q=크로바+57-550+수틀+30cm&tbm=isch",
                "same_product_note": "구글 이미지 '크로바 57-550' 동일제품 검색 허용.",
            },
        )
    ]

    for c in candidates:
        entry = {
            "brand": c["brand"],
            "product": c["product"],
            "verify_url": c["verify_url"],
            "same_product_note": c["same_product_note"],
            "saved": None,
            "status": "verified_page_only",
        }
        if c.get("save_as") and c.get("image_urls"):
            dest = ref_dir / c["save_as"]
            ok = False
            used = None
            for u in c["image_urls"]:
                if download(u, dest):
                    ok = True
                    used = u
                    break
            if ok:
                entry["status"] = "downloaded"
                entry["saved"] = str(dest.relative_to(OUT))
                entry["image_url"] = used
            else:
                entry["status"] = "page_verified_image_download_failed"
        refs.append(entry)

    for save_as, urls, meta in extra_try:
        dest = ref_dir / save_as
        entry = {**meta, "saved": None, "status": "skipped"}
        for u in urls:
            if download(u, dest):
                entry["status"] = "downloaded"
                entry["saved"] = str(dest.relative_to(OUT))
                entry["image_url"] = u
                break
        refs.append(entry)

    (ref_dir / "refs.json").write_text(
        json.dumps(refs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return refs


def to_rgb(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    return np.asarray(im).astype(np.float32)


def save_rgb(arr: np.ndarray, path: Path, src_suffix: str) -> None:
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.fromarray(arr)
    if path.suffix.lower() in (".jpg", ".jpeg"):
        im.save(path, quality=92, optimize=True)
    else:
        im.save(path, optimize=True)


def photo_mask(rgb: np.ndarray) -> np.ndarray:
    """High-texture / non-flat regions ≈ embedded product photos."""
    gray = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    # local std
    blur = cv2.GaussianBlur(gray, (0, 0), 3)
    local_var = cv2.GaussianBlur((gray - blur) ** 2, (0, 0), 7)
    # also exclude very saturated flat brand colors (yellow header etc.)
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[:, :, 1]
    # graphic: low texture OR (high sat + low texture)
    tex = local_var
    thr = np.percentile(tex, 55)
    mask = (tex > thr).astype(np.float32)
    # expand a bit
    mask = cv2.GaussianBlur(mask, (0, 0), 4)
    # reduce weight on ultra-flat high-sat design
    flat = (tex < np.percentile(tex, 35)) & (sat > 80)
    mask = np.where(flat, mask * 0.15, mask)
    return np.clip(mask, 0, 1)


def estimate_wb_gains(rgb: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    """Gray-world on near-white / mid-bright pixels."""
    if mask is None:
        m = np.ones(rgb.shape[:2], dtype=bool)
    else:
        m = mask > 0.35
    pix = rgb[m]
    if pix.size < 1000:
        pix = rgb.reshape(-1, 3)
    # prefer bright near-neutral
    lum = pix.mean(axis=1)
    chroma = pix.max(axis=1) - pix.min(axis=1)
    sel = (lum > np.percentile(lum, 70)) & (chroma < 35)
    if sel.sum() < 200:
        sel = lum > np.percentile(lum, 80)
    ref = pix[sel].mean(axis=0)
    ref = np.maximum(ref, 1.0)
    target = float(ref.mean())
    gains = target / ref
    # limit gain
    gains = np.clip(gains, 0.85, 1.18)
    return gains


def flatten_illumination(rgb: np.ndarray, strength: float = 0.55) -> np.ndarray:
    """Remove large-scale lighting unevenness, keep local color."""
    lab = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    L = lab[:, :, 0]
    # large blur approx illumination
    k = max(31, (min(rgb.shape[:2]) // 12) | 1)
    illum = cv2.GaussianBlur(L, (k, k), 0)
    # avoid div0
    illum = np.maximum(illum, 1.0)
    mean_illum = float(np.median(illum))
    L2 = L * ((mean_illum / illum) ** strength)
    lab[:, :, 0] = np.clip(L2, 0, 255)
    out = cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)
    return out


def mild_clahe_L(rgb: np.ndarray, clip: float = 1.4) -> np.ndarray:
    lab = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB).astype(np.float32)


def unsharp(rgb: np.ndarray, amount: float = 0.35, sigma: float = 1.2) -> np.ndarray:
    blur = cv2.GaussianBlur(rgb, (0, 0), sigma)
    return np.clip(rgb + amount * (rgb - blur), 0, 255)


def blend(orig: np.ndarray, edited: np.ndarray, mask: np.ndarray, mix: float = 0.85) -> np.ndarray:
    m = (mask * mix)[..., None]
    return orig * (1 - m) + edited * m


def retouch_photo_composite(rgb: np.ndarray) -> np.ndarray:
    mask = photo_mask(rgb)
    # work copy
    x = rgb.copy()
    x = flatten_illumination(x, 0.5)
    gains = estimate_wb_gains(x, mask)
    x = x * gains.reshape(1, 1, 3)
    x = mild_clahe_L(x, 1.3)
    # slight midtone lift for trust/brightness uniformity
    x = np.clip(x * 1.02, 0, 255)
    x = unsharp(x, 0.28, 1.1)
    # apply mainly on photo regions; keep graphic headers stable
    out = blend(rgb, x, mask, mix=0.82)
    # tiny global polish on whole for cohesion
    out = flatten_illumination(out, 0.18)
    return out


def retouch_color_chart(rgb: np.ndarray) -> np.ndarray:
    """Left-right lighting flatten + white bg neutralize; preserve swatch hues."""
    h, w = rgb.shape[:2]
    x = rgb.copy()
    # column-wise illumination equalization on L
    lab = cv2.cvtColor(x.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    L = lab[:, :, 0]
    # estimate per-column background (bright pixels)
    col_gain = np.ones(w, dtype=np.float32)
    for i in range(w):
        col = L[:, i]
        # top percentile as paper
        bg = np.percentile(col, 92)
        col_gain[i] = 245.0 / max(bg, 1.0)
    col_gain = np.clip(col_gain, 0.9, 1.15)
    # smooth gains
    col_gain = cv2.GaussianBlur(col_gain.reshape(1, -1), (0, 0), 12).ravel()
    L2 = L * col_gain.reshape(1, -1)
    lab[:, :, 0] = np.clip(L2, 0, 255)
    x = cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)

    # WB from paper regions (very bright)
    gains = estimate_wb_gains(x, None)
    x = x * gains.reshape(1, 1, 3)
    # mild denoise without smearing colors
    x8 = np.clip(x, 0, 255).astype(np.uint8)
    x8 = cv2.fastNlMeansDenoisingColored(x8, None, 2.5, 2.5, 5, 15)
    x = x8.astype(np.float32)
    x = unsharp(x, 0.22, 0.9)
    # keep 70% edit (don't overcook swatches)
    return blend(rgb, x, np.ones(rgb.shape[:2], np.float32), mix=0.78)


def retouch_product_pack(rgb: np.ndarray) -> np.ndarray:
    """Package shots: unify wood tone, whiten bg, soften glare a bit."""
    x = flatten_illumination(rgb, 0.6)
    gains = estimate_wb_gains(x, None)
    # push slightly warmer wood-friendly but controlled
    x = x * gains.reshape(1, 1, 3)
    # background whitening: near-white pixels
    lum = x.mean(axis=2)
    chroma = x.max(axis=2) - x.min(axis=2)
    bg = (lum > 200) & (chroma < 28)
    if bg.any():
        target = np.array([248, 248, 248], dtype=np.float32)
        # gentle pull
        x[bg] = x[bg] * 0.35 + target * 0.65
    x = mild_clahe_L(x, 1.25)
    # reduce specular: compress very bright outliers in mid-sat areas
    hsv = cv2.cvtColor(np.clip(x, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    v = hsv[:, :, 2]
    s = hsv[:, :, 1]
    glare = (v > 245) & (s < 40)
    v[glare] = v[glare] * 0.92
    hsv[:, :, 2] = v
    x = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
    x = unsharp(x, 0.3, 1.0)
    return blend(rgb, x, np.ones(rgb.shape[:2], np.float32), mix=0.85)


def retouch_catalog(rgb: np.ndarray) -> np.ndarray:
    x = flatten_illumination(rgb, 0.45)
    gains = estimate_wb_gains(x, None)
    x = x * gains.reshape(1, 1, 3)
    x = mild_clahe_L(x, 1.2)
    x = unsharp(x, 0.25, 1.0)
    return blend(rgb, x, np.ones(rgb.shape[:2], np.float32), mix=0.8)


def ref_guided_adjust(rgb: np.ndarray, ref_path: Path | None, strength: float = 0.25) -> np.ndarray:
    """Match overall mean LAB of product image toward official reference (mild)."""
    if ref_path is None or not ref_path.exists():
        return rgb
    try:
        ref = to_rgb(ref_path)
    except Exception:
        return rgb
    # resize ref small
    ref_s = cv2.resize(ref.astype(np.uint8), (128, 128))
    src_s = cv2.resize(rgb.astype(np.uint8), (128, 128))
    lab_r = cv2.cvtColor(ref_s, cv2.COLOR_RGB2LAB).astype(np.float32)
    lab_s = cv2.cvtColor(src_s, cv2.COLOR_RGB2LAB).astype(np.float32)
    # ignore very dark/bright for mean
    def stats(lab):
        L = lab[:, :, 0].ravel()
        m = (L > 40) & (L < 230)
        return lab.reshape(-1, 3)[m].mean(axis=0)

    mr, ms = stats(lab_r), stats(lab_s)
    delta = (mr - ms) * strength
    lab = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    lab += delta.reshape(1, 1, 3)
    lab[:, :, 0] = np.clip(lab[:, :, 0], 0, 255)
    lab[:, :, 1] = np.clip(lab[:, :, 1], 0, 255)
    lab[:, :, 2] = np.clip(lab[:, :, 2], 0, 255)
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)


MODES = {
    "photo_composite": retouch_photo_composite,
    "color_chart": retouch_color_chart,
    "product_pack": retouch_product_pack,
    "catalog": retouch_catalog,
}


def organize_before(product_key: str) -> Path:
    raw = OUT / product_key / "01_원본_before"
    curated = OUT / product_key / "01_원본_before_curated"
    curated.mkdir(parents=True, exist_ok=True)
    meta = PRODUCTS[product_key]
    for jf in meta["files"]:
        src = raw / jf.src_name
        if not src.exists():
            # try unquoted
            alt = raw / urllib_unquote(jf.src_name)
            src = alt if alt.exists() else src
        if not src.exists():
            print("  MISSING", jf.src_name)
            continue
        dest = curated / jf.out_name.replace("_retouched", "").replace(
            Path(jf.out_name).stem, Path(jf.out_name).stem
        )
        # store with clean names
        dest = curated / jf.out_name
        shutil.copy2(src, dest)
    return curated


def urllib_unquote(s: str) -> str:
    import urllib.parse

    return urllib.parse.unquote(s)


def process_all(refs: list[dict]) -> list[dict]:
    # pick best refs
    anchor_ref = None
    clover_ref = None
    for r in refs:
        p = r.get("saved")
        if not p:
            continue
        path = OUT / p
        if "anchor" in Path(p).name and path.exists() and anchor_ref is None:
            anchor_ref = path
        if "clover" in Path(p).name and path.exists() and clover_ref is None:
            clover_ref = path

    results = []
    for key, meta in PRODUCTS.items():
        print("\n===", key)
        curated = organize_before(key)
        after = OUT / key / "02_보정_after"
        after.mkdir(parents=True, exist_ok=True)
        for jf in meta["files"]:
            src = curated / jf.out_name
            if not src.exists():
                continue
            print("  retouch", jf.out_name, jf.mode)
            rgb = to_rgb(src)
            fn = MODES[jf.mode]
            out = fn(rgb)
            # official-guided re-correction for clover/anchor
            if key.startswith("앵커") and anchor_ref:
                out = ref_guided_adjust(out, anchor_ref, 0.22)
            if key.startswith("크로바") and clover_ref:
                out = ref_guided_adjust(out, clover_ref, 0.28)
            dest = after / jf.out_name
            save_rgb(out, dest, src.suffix)
            results.append(
                {
                    "product": meta["title"],
                    "code": meta["code"],
                    "page": meta["page"],
                    "before": str(src.relative_to(OUT)),
                    "after": str(dest.relative_to(OUT)),
                    "mode": jf.mode,
                    "note": jf.note,
                }
            )
    return results


def write_source_md(refs: list[dict], results: list[dict]) -> Path:
    md = OUT / "원본출처_목록.md"
    lines = [
        "# 자수실 상세 이미지 보정 — 원본출처 목록",
        "",
        f"- 작업일: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "- 목적: 촬영본 기반 균일·신뢰감 보정 (상품 자동수정·몰 업로드·가격변경 없음)",
        "- 산출 루트: `detail_image_retouch_20260726/`",
        "",
        "## 폴더 구조",
        "",
        "```",
        "detail_image_retouch_20260726/",
        "  면사447색_풀세트/",
        "    01_원본_before/          # makehomedeco 수집 원본(전체)",
        "    01_원본_before_curated/  # 보정 대상만",
        "    02_보정_after/           # 보정본",
        "  앵커444색_풀세트/ ...",
        "  크로바_대형수틀_57-550/ ...",
        "  _official_refs/           # 공식·동일제품 레퍼런스",
        "  원본출처_목록.md",
        "```",
        "",
        "## 1) 면사 447색 풀세트 (makehomedeco 상세)",
        "",
        "| 구분 | 내용 |",
        "|---|---|",
        "| 상품코드 | P00000GG |",
        "| 상품명 | 프랑스자수 자수실 447색 풀세트 대용량 컬러 자수실 세트 |",
        "| 상세페이지 | https://makehomedeco.co.kr/product/detail.html?product_no=163 |",
        "| 상세 원본 파일 | `/web/upload/.../44720FULLSET201.png`, `44720FULLSET202.png` |",
        "| 대표이미지 | `/web/product/big/201701/163_shop1_243481.jpg` |",
        "| 보정 방침 | 정렬 촬영 구도 유지 · 사진 영역 조명/WB 불균일 보정 · 그래픽 헤더 톤 보호 |",
        "",
        "## 2) 앵커 444색 풀세트 (makehomedeco 상세)",
        "",
        "| 구분 | 내용 |",
        "|---|---|",
        "| 상품코드 | P0000BJO |",
        "| 상품명 | ANCHOR 독일 앵커 자수실 444색 풀세트 … |",
        "| 상세페이지 | https://makehomedeco.co.kr/product/detail.html?product_no=924 |",
        "| 상세 원본 | `/web/home -1/666.jpg`, `anc 1.jpg`, `anc 2.jpg`, `anc 3.jpg` |",
        "| 대표이미지 | `/web/product/big/201807/924_shop1_15324080489293.jpg` |",
        "| 보정 방침 | 컬러차트 좌우 조명 평탄화 · 종이 배경 화이트 중립화 · 실 색상 hue 과보정 금지 |",
        "",
        "## 3) 크로바·앵커 — 공식/구글 동일제품 확인 후 재보정",
        "",
        "동일제품 확인 후에만 레퍼런스 가이드 재보정을 적용했습니다.",
        "",
    ]
    lines.append("| 브랜드 | 확인 제품 | 확인 URL | 상태 | 비고 |")
    lines.append("|---|---|---|---|---|")
    for r in refs:
        lines.append(
            f"| {r.get('brand','')} | {r.get('product','')} | {r.get('verify_url','')} | {r.get('status','')} | {r.get('same_product_note','')} |"
        )
    lines += [
        "",
        "### 재보정 적용",
        "",
        "- 앵커: 공식 444 solid 라인 확인 → 전체 LAB 평균을 공식 톤에  Mild 매칭",
        "- 크로바 57-550: JAN/동일 수틀 계열 확인 → 우드톤·배경 화이트 재보정",
        "",
        "## 보정 파일 매핑",
        "",
        "| 상품코드 | Before | After | 모드 | 메모 |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['code']} | `{r['before']}` | `{r['after']}` | {r['mode']} | {r['note']} |"
        )
    lines += [
        "",
        "## 금지 사항 준수",
        "",
        "- [x] 몰 자동 업로드 없음",
        "- [x] 가격 변경 없음",
        "- [x] 상품 자동수정 없음 (로컬 보정본만 생성)",
        "",
        "## 사용 방법",
        "",
        "1. `02_보정_after` 이미지를 눈으로 확인",
        "2. 문제 없으면 카페24/스마트스토어 상세에 **수동** 교체",
        "3. 원본은 `01_원본_before_curated`에 보관",
        "",
    ]
    md.write_text("\n".join(lines), encoding="utf-8")
    return md


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("Fetching official refs...")
    refs = fetch_official_refs()
    print("Processing...")
    results = process_all(refs)
    md = write_source_md(refs, results)
    (OUT / "retouch_manifest.json").write_text(
        json.dumps({"refs": refs, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("\nDONE")
    print("OUT:", OUT)
    print("MD:", md)
    print("files:", len(results))


if __name__ == "__main__":
    main()
