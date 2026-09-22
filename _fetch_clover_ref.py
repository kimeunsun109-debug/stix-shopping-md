# -*- coding: utf-8 -*-
import re
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

OUT = Path(r"C:\Users\user\OneDrive\Desktop\쇼핑몰관리md\detail_image_retouch_20260726\_official_refs")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
        if len(data) < 5000:
            print("skip small", len(data), url)
            return False
        dest.write_bytes(data)
        print("OK", dest.name, len(data) // 1024, "KB")
        return True
    except Exception as e:
        print("FAIL", e, url[:100])
        return False


def imgs_from(html: str, base: str) -> list[str]:
    found = []
    pats = [
        r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
        r'content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
        r'<img[^>]+src=["\']([^"\']+)["\']',
        r'data-src=["\']([^"\']+)["\']',
        r'(https?://[^\s"\']+\.(?:jpg|jpeg|png|webp))',
    ]
    for pat in pats:
        for m in re.findall(pat, html, flags=re.I):
            u = urljoin(base, m)
            low = u.lower()
            if any(x in low for x in ("logo", "icon", "banner", "sprite", "placeholder", "1x1", "svg")):
                continue
            if u not in found:
                found.append(u)
    return found


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = [
        "https://www.yuzawaya.shop/shopdetail/000000055911/",
        "https://clover.co.jp/products/57550",
        "https://clover.co.jp/products/57-550",
        "https://www.clover.co.jp/products/detail.php?product_id=57550",
    ]
    saved = 0
    for page in pages:
        print("\nPAGE", page)
        try:
            html = get(page)
        except Exception as e:
            print(" page fail", e)
            continue
        # save snippet
        (OUT / "debug_page.html").write_text(html[:100000], encoding="utf-8")
        imgs = imgs_from(html, page)
        print(" imgs", len(imgs))
        for i, u in enumerate(imgs[:10], 1):
            print("  -", u[:120])
            dest = OUT / f"clover_57-550_yuzawaya_{saved+1}.jpg"
            # keep original ext
            if ".png" in u.lower():
                dest = dest.with_suffix(".png")
            if download(u, dest):
                saved += 1
                if saved >= 3:
                    return
    print("saved", saved)


if __name__ == "__main__":
    main()
