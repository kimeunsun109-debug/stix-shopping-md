# -*- coding: utf-8 -*-
"""Real STIX catalog loader for Commerce AI operations (100+ products)."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from commerce_ai.cache import CACHE
from commerce_ai.stability.logging_setup import get_logger
from md_catalog_io import load_all_catalogs

_log = get_logger("commerce_ai.ops_catalog")

PLATFORM_TO_MARKETPLACE = {
    "쿠팡": "coupang",
    "로켓그로스": "coupang",
    "스마트스토어": "smartstore",
    "지마켓/옥션": "gmarket",
    "11번가": "11st",
    "카페24": "cafe24",
}

_JUNK_NAME = (
    "상품기본정보",
    "등록상품ID",
    "이용 안내",
    "Help",
    "Catalog Template",
    "필수",
    "결제창",
    "님 결제",
)


def _is_valid_product(rec: dict) -> bool:
    name = (rec.get("name") or "").strip()
    if len(name) < 6:
        return False
    if any(j in name for j in _JUNK_NAME):
        return False
    # pure numeric name = broken header mapping
    if re.fullmatch(r"\d{6,}", name):
        return False
    if rec.get("price") is None and not rec.get("id") and not rec.get("sales"):
        return False
    status = (rec.get("status") or "").strip()
    if status and any(x in status for x in ("중지", "종료", "삭제", "품절")):
        # keep low stock alerts but skip fully stopped if no sales signal
        if not rec.get("sales"):
            return False
    return True


def infer_keyword(name: str) -> str:
    """Extract a search keyword from product title for SEO analysis."""
    n = name
    for token in (
        "보석십자수",
        "십자수",
        "프랑스자수",
        "E6000",
        "B7000",
        "코바늘",
        "자수실",
        "DMC",
        "크로바",
        "비즈",
        "스티커",
        "캔버스",
    ):
        if token.lower() in n.lower():
            return token
    parts = re.split(r"[\s/|_·]+", n)
    return " ".join(parts[:2]) if parts else n[:20]


def infer_category(name: str, raw: dict | None = None) -> str:
    raw = raw or {}
    cat = ""
    for k, v in raw.items():
        if k and "카테고리" in str(k) and v:
            cat = str(v)
            break
    if cat:
        return cat.split(">")[-1].strip()[:40] if ">" in cat else cat[:40]
    return infer_keyword(name)


def load_ops_products(
    *,
    platforms: list[str] | None = None,
    min_price: int | None = None,
    limit: int | None = None,
    prefer_sales: bool = True,
) -> list[dict[str, Any]]:
    """
    Load real STIX catalog products for batch operations.
    Returns normalized ops records with marketplace mapping.
    """
    cache_key = {
        "platforms": tuple(platforms or ()),
        "min_price": min_price,
        "limit": limit,
        "prefer_sales": prefer_sales,
    }
    hit = CACHE.get("ops_products", cache_key)
    if hit is not None:
        return hit

    recs = [r for r in load_all_catalogs() if _is_valid_product(r)]
    if platforms:
        recs = [r for r in recs if r["platform"] in platforms]

    # dedupe by platform+id or platform+name
    seen: set[str] = set()
    unique: list[dict] = []
    for r in recs:
        key = f"{r['platform']}|{r.get('id') or r['name'][:40]}"
        if key in seen:
            continue
        seen.add(key)
        if min_price is not None and (r.get("price") or 0) < min_price:
            continue
        unique.append(r)

    if prefer_sales:
        unique.sort(
            key=lambda x: (
                -(x.get("sales") or 0),
                -(x.get("price") or 0),
                x["name"],
            )
        )
    else:
        unique.sort(key=lambda x: x["name"])

    out: list[dict[str, Any]] = []
    for r in unique:
        out.append(
            {
                "platform": r["platform"],
                "marketplace": PLATFORM_TO_MARKETPLACE.get(r["platform"], "coupang"),
                "product_id": r.get("id") or f"{r['platform']}:{r['name'][:24]}",
                "title": r["name"],
                "price": r.get("price"),
                "stock": r.get("stock"),
                "sales_units": r.get("sales"),
                "status": r.get("status") or "",
                "keyword": infer_keyword(r["name"]),
                "category": infer_category(r["name"], r.get("raw") or {}),
                "raw": r.get("raw") or {},
            }
        )
        if limit and len(out) >= limit:
            break
    CACHE.set("ops_products", cache_key, out, ttl_sec=300.0)
    _log.debug("ops_catalog loaded=%s", len(out))
    return out


def peer_competitors(
    products: list[dict[str, Any]], target: dict[str, Any], *, n: int = 5
) -> list[dict[str, Any]]:
    """Same-marketplace peers sharing keyword tokens — used as competitors."""
    kw = target.get("keyword") or ""
    peers = []
    for p in products:
        if p["product_id"] == target["product_id"]:
            continue
        if p["marketplace"] != target["marketplace"]:
            continue
        if kw and kw not in (p.get("title") or ""):
            continue
        peers.append(p)
        if len(peers) >= n:
            break
    if len(peers) < n:
        for p in products:
            if p["product_id"] == target["product_id"]:
                continue
            if p["marketplace"] != target["marketplace"]:
                continue
            if p in peers:
                continue
            peers.append(p)
            if len(peers) >= n:
                break
    return peers


def catalog_stats() -> dict[str, Any]:
    products = load_ops_products(limit=None)
    by_plat: dict[str, int] = defaultdict(int)
    for p in products:
        by_plat[p["platform"]] += 1
    return {
        "total_valid": len(products),
        "by_platform": dict(by_plat),
        "ready_for_batch": len(products) >= 100,
    }
