# -*- coding: utf-8 -*-
"""Fetch makehomedeco detail images for thread products."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\Users\user\OneDrive\Desktop\쇼핑몰관리md")
OUT = ROOT / "detail_image_retouch_20260726"
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


def find_product_url(keyword: str) -> str | None:
    html = get(
        "https://makehomedeco.co.kr/product/search.html?keyword="
        + urllib.parse.quote(keyword)
    )
    # cafe24 product links
    links = re.findall(r'href="(/product/[^"]+)"', html)
    for L in links:
        if any(x in L for x in ("search", "list", "compare", "recent")):
            continue
        if "/category/" in L or re.search(r"/product/.+/\d+/", L):
            return abs_url(L)
    # product_no style
    m = re.search(r'product_no=(\d+)', html)
    if m:
        return f"https://makehomedeco.co.kr/product/detail.html?product_no={m.group(1)}"
    return None


def extract_images(html: str) -> list[str]:
    urls: list[str] = []
    # detail area often in #prdDetail or .cont
    chunks = re.findall(
        r'(id="prdDetail".*?</div>\s*</div>)|(class="cont".*?</div>)',
        html,
        flags=re.I | re.S,
    )
    body = " ".join("".join(c) for c in chunks) if chunks else html
    for pat in [
        r'<img[^>]+src=["\']([^"\']+)["\']',
        r'<img[^>]+ec-data-src=["\']([^"\']+)["\']',
        r'data-src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
        r'(https?://[^"\'\s]+?\.(?:jpg|jpeg|png|webp))',
        r'(/web/upload/[^"\'\s]+?\.(?:jpg|jpeg|png|webp))',
        r'(/web/product/[^"\'\s]+?\.(?:jpg|jpeg|png|webp))',
    ]:
        for m in re.findall(pat, body, flags=re.I):
            u = abs_url(m)
            if any(
                skip in u.lower()
                for skip in (
                    "icon",
                    "btn_",
                    "banner",
                    "logo",
                    "blank.gif",
                    "loading",
                    "common/img",
                    "design/",
                    "sns_",
                    "favicon",
                )
            ):
                continue
            if u not in urls:
                urls.append(u)
    return urls


def download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        if len(data) < 2000:
            return False
        dest.write_bytes(data)
        return True
    except Exception as e:
        print("  FAIL", url, e)
        return False


def cafe24_thumb(rel: str) -> list[str]:
    """Candidate cafe24 CDN paths for catalog thumbnails."""
    rel = rel.lstrip("/")
    bases = [
        f"https://makehomedeco.co.kr/web/product/big/{rel}",
        f"https://makehomedeco.co.kr/web/product/medium/{rel}",
        f"https://makehomedeco.co.kr/web/product/small/{rel}",
        f"https://makehomedeco.co.kr/web/product/tiny/{rel}",
        f"https://ecimg.cafe24img.com/pg1521b40289025089/makehomedeco/web/product/big/{rel}",
    ]
    return bases


def main() -> None:
    prod = next(p for p in ROOT.iterdir() if p.is_dir() and "전체" in p.name)
    xlsx = next(p for p in prod.iterdir() if "카페24" in p.name and p.suffix == ".xlsx")
    df = pd.read_excel(xlsx, dtype=str)
    code_col = df.columns[0]
    # locate image columns by index from earlier run
    img_cols = [c for c in df.columns if "이미지등록" in str(c)]
    name_col = df.columns[7]
    detail_cols = [c for c in df.columns if "상세설명" in str(c) or "상품 상세" in str(c)]

    jobs = [
        ("면사447색_풀세트", "P00000GG", "447"),
        ("앵커444색_풀세트", "P0000BJO", "444"),
        ("크로바_대형수틀_57-550", "P0000CIX", "57-550"),
    ]

    OUT.mkdir(parents=True, exist_ok=True)
    sources = []

    for folder, code, kw in jobs:
        row = df[df[code_col] == code]
        if row.empty:
            print("MISSING CODE", code)
            continue
        r = row.iloc[0]
        name = str(r[name_col])
        print("\n###", code, name)

        before = OUT / folder / "01_원본_before"
        before.mkdir(parents=True, exist_ok=True)

        # 1) catalog images from excel
        for c in img_cols:
            rel = r.get(c)
            if pd.isna(rel) or not str(rel).strip():
                continue
            rel = str(rel).strip()
            ok = False
            for cand in cafe24_thumb(rel):
                dest = before / f"catalog_{Path(rel).name}"
                if dest.exists() and dest.stat().st_size > 2000:
                    ok = True
                    sources.append(
                        {
                            "product": name,
                            "code": code,
                            "role": "catalog",
                            "url": cand,
                            "file": str(dest.relative_to(OUT)),
                        }
                    )
                    break
                if download(cand, dest):
                    print("  catalog OK", cand)
                    sources.append(
                        {
                            "product": name,
                            "code": code,
                            "role": "catalog",
                            "url": cand,
                            "file": str(dest.relative_to(OUT)),
                        }
                    )
                    ok = True
                    break
            if not ok:
                print("  catalog FAIL", rel)

        # 2) detail HTML embedded images from excel
        for c in detail_cols:
            html = r.get(c)
            if pd.isna(html) or "<img" not in str(html).lower():
                continue
            imgs = extract_images(str(html))
            print("  excel detail imgs", len(imgs), "from", c)
            for i, u in enumerate(imgs, 1):
                dest = before / f"excel_detail_{i:02d}_{Path(urllib.parse.urlparse(u).path).name}"
                if download(u, dest):
                    sources.append(
                        {
                            "product": name,
                            "code": code,
                            "role": "excel_detail",
                            "url": u,
                            "file": str(dest.relative_to(OUT)),
                        }
                    )

        # 3) live product page
        purl = find_product_url(kw if kw not in ("447", "444") else name[:20])
        if not purl:
            purl = find_product_url(code)
        print("  product_url", purl)
        if purl:
            page = get(purl)
            # save debug html snippet
            (OUT / folder / "page_debug.html").write_text(page[:200000], encoding="utf-8")
            imgs = extract_images(page)
            # also grab all upload/product images from full page
            extra = re.findall(
                r'((?:https?:)?//[^"\'\s]+?/web/(?:upload|product)/[^"\'\s]+\.(?:jpg|jpeg|png|webp))',
                page,
                flags=re.I,
            )
            extra += re.findall(
                r'(/web/(?:upload|product)/[^"\'\s]+\.(?:jpg|jpeg|png|webp))',
                page,
                flags=re.I,
            )
            for e in extra:
                u = abs_url(e)
                if u not in imgs:
                    imgs.append(u)
            print("  page imgs", len(imgs))
            for i, u in enumerate(imgs, 1):
                fname = Path(urllib.parse.urlparse(u).path).name
                dest = before / f"page_{i:02d}_{fname}"
                if dest.exists() and dest.stat().st_size > 2000:
                    sources.append(
                        {
                            "product": name,
                            "code": code,
                            "role": "page",
                            "url": u,
                            "file": str(dest.relative_to(OUT)),
                            "page": purl,
                        }
                    )
                    continue
                if download(u, dest):
                    print("  page OK", fname)
                    sources.append(
                        {
                            "product": name,
                            "code": code,
                            "role": "page",
                            "url": u,
                            "file": str(dest.relative_to(OUT)),
                            "page": purl,
                        }
                    )

        # count
        n = len(list(before.glob("*.*")))
        print("  saved files:", n)

    (OUT / "sources_raw.json").write_text(
        json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nDONE sources", len(sources), "->", OUT)


if __name__ == "__main__":
    main()
