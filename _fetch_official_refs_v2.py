# -*- coding: utf-8 -*-
"""Scrape official/same-product pages for real image URLs and download."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

OUT = Path(r"C:\Users\user\OneDrive\Desktop\쇼핑몰관리md\detail_image_retouch_20260726")
REF = OUT / "_official_refs"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def get_text(url: str) -> str:
    return get(url).decode("utf-8", "replace")


def abs_url(base: str, u: str) -> str:
    from urllib.parse import urljoin

    return urljoin(base, u)


def find_imgs(html: str, base: str) -> list[str]:
    urls = []
    for pat in [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'"image"\s*:\s*"(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
        r'src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
        r'data-src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
    ]:
        for m in re.findall(pat, html, flags=re.I):
            u = abs_url(base, m)
            if any(x in u.lower() for x in ("logo", "icon", "sprite", "svg", "favicon", "1x1")):
                continue
            if u not in urls:
                urls.append(u)
    return urls


def save(url: str, dest: Path) -> bool:
    try:
        data = get(url)
        if len(data) < 2000:
            return False
        dest.write_bytes(data)
        print("OK", dest.name, len(data) // 1024, "KB", url[:90])
        return True
    except Exception as e:
        print("FAIL", url[:90], e)
        return False


def main() -> None:
    REF.mkdir(parents=True, exist_ok=True)
    jobs = [
        (
            "anchor_official_mouline",
            "https://anchorcrafts.com/products/anchor-stranded-cotton-mouline-5",
            "ANCHOR",
            "공식 Stranded Cotton Mouliné — 444 solid colours",
        ),
        (
            "anchor_official_shade_card",
            "https://anchorcrafts.com/products/anchor-embroidery-thread-shade-card",
            "ANCHOR",
            "공식 Shade Card CA-4546",
        ),
        (
            "clover_official_hoop_18cm",
            "https://www.clover-mfg.com/en/product/n8812",
            "CLOVER",
            "공식 Embroidery Hoop 18cm (동일 구조 제품군)",
        ),
        (
            "clover_jp_57-550_dealer",
            "https://eshop.needleworkclub.com/product-13539",
            "CLOVER",
            "딜러 동일 SKU 57-550 / JAN 4901316575502",
        ),
        # Japanese clover product search pages often list 57-550
        (
            "clover_rakuten_same",
            "https://search.rakuten.co.jp/search/mall/%E3%82%AF%E3%83%AD%E3%83%90%E3%83%BC+57-550/",
            "CLOVER",
            "라쿠텐 동일제품 57-550 검색",
        ),
    ]
    results = []
    for key, url, brand, note in jobs:
        print("\n#", key, url)
        entry = {
            "key": key,
            "brand": brand,
            "verify_url": url,
            "note": note,
            "images": [],
            "saved": [],
        }
        try:
            html = get_text(url)
        except Exception as e:
            entry["error"] = str(e)
            results.append(entry)
            continue
        imgs = find_imgs(html, url)
        print(" found", len(imgs))
        entry["images"] = imgs[:12]
        saved = 0
        for i, iu in enumerate(imgs[:8], 1):
            ext = ".jpg"
            for e in (".png", ".webp", ".jpeg", ".jpg"):
                if e in iu.lower():
                    ext = e.split("?")[0]
                    if not ext.startswith("."):
                        ext = "." + ext
                    break
            dest = REF / f"{key}_{i}{ext}"
            if save(iu, dest):
                entry["saved"].append(str(dest.relative_to(OUT)))
                saved += 1
                if saved >= 2:
                    break
        results.append(entry)

    # Also pull a known public Anchor box / shade reference via Wikimedia or open CDN if any
    # Fallback: use Google shopping style open image from makehomedeco competitor pages is NOT used.
    # Instead download Anchor crafts og:image via alternate shop domains.
    alts = [
        (
            "https://www.sewandso.co.uk/product/anchor-stranded-cotton-colour-card/168246",
            "anchor_sewandso_shade",
        ),
        (
            "https://www.lovecrafts.com/en-gb/p/anchor-stranded-cotton",
            "anchor_lovecrafts",
        ),
    ]
    for url, key in alts:
        print("\n# alt", key)
        try:
            html = get_text(url)
        except Exception as e:
            print(" err", e)
            continue
        imgs = find_imgs(html, url)
        for i, iu in enumerate(imgs[:5], 1):
            dest = REF / f"{key}_{i}.jpg"
            if save(iu, dest):
                results.append(
                    {
                        "key": key,
                        "brand": "ANCHOR",
                        "verify_url": url,
                        "note": "동일 ANCHOR stranded cotton / shade 계열 공식유통",
                        "saved": [str(dest.relative_to(OUT))],
                        "images": [iu],
                    }
                )
                break

    (REF / "refs_v2.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nDONE", REF)


if __name__ == "__main__":
    main()
