# -*- coding: utf-8
"""Scrape Coupang listing prices via CDP."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

from playwright.sync_api import Page

from item_winner.config import SkuTarget

OUR_SELLER_HINTS = ("스팃스", "stix", "spits", "spitz")


@dataclass
class PriceObservation:
    my_price: int | None
    competitor_price: int | None
    is_winner: bool
    raw_note: str = ""


def _first_price(text: str) -> int | None:
    m = re.search(r"(\d{1,3}(?:,\d{3})*)\s*원", text)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def _main_display_price(page: Page) -> int | None:
    for _ in range(2):
        val = page.evaluate(
            """() => {
          const sels = [
            '.total-price strong', '.prod-sale-price',
            '[class*="totalPrice"]', '[class*="salePrice"]',
            'meta[property="product:price:amount"]',
          ];
          for (const sel of sels) {
            const el = document.querySelector(sel);
            if (!el) continue;
            const raw = (el.getAttribute('content') || el.innerText || '').replace(/[^0-9]/g, '');
            if (raw && Number(raw) >= 100) return Number(raw);
          }
          const body = document.body.innerText || '';
          const m = body.match(/(\\d{1,3}(?:,\\d{3})*)\\s*원/);
          return m ? Number(m[1].replace(/,/g, '')) : null;
        }"""
        )
        if val and int(val) >= 100:
            return int(val)
        time.sleep(2)
    return None


def _competitor_hints(name: str) -> list[str]:
    hints = [name.strip()] if name.strip() else []
    if "빙고" not in "".join(hints):
        hints.extend(["빙고", "빙고인터", "빙고인터네셔널"])
    return [h for h in hints if h]


def _is_our_seller(text: str) -> bool:
    t = text.lower()
    return any(h.lower() in t for h in OUR_SELLER_HINTS)


def _price_in_range(n: int, lo: int = 500, hi: int = 50000) -> bool:
    return lo <= n <= hi


def _parse_competitor_from_dom(
    page: Page, competitor_name: str, price_lo: int = 1000, price_hi: int = 3000
) -> int | None:
    hints = _competitor_hints(competitor_name)
    return page.evaluate(
        """([hints, lo, hi]) => {
      const isOurs = (t) => /스팃스|stix|spits|spitz/i.test(t);
      const nodes = [...document.querySelectorAll(
        'tr, li, div, section, article, [role="dialog"], [class*="seller"], [class*="vendor"], [class*="offer"]'
      )];
      const hits = [];
      for (const node of nodes) {
        const t = (node.innerText || '').trim();
        if (!t || t.length > 250) continue;
        const m = t.match(/(\\d{1,3}(?:,\\d{3})*)\\s*원/);
        if (!m) continue;
        const v = Number(m[1].replace(/,/g, ''));
        if (v < lo || v > hi) continue;
        if (isOurs(t)) continue;
        const hasHint = hints.some(h => t.includes(h));
        if (hasHint) hits.push(v);
      }
      if (!hits.length) return null;
      // same-offer duplicates → pick first (usually listed price)
      return hits[0];
    }""",
        [hints, price_lo, price_hi],
    )


def _extract_seller_section(body: str) -> str:
    for marker in ("다른 판매자", "다른판매자"):
        idx = body.find(marker)
        if idx >= 0:
            return body[idx : idx + 12000]
    return body


def _parse_bingo_seller_block(section: str, competitor_name: str) -> int | None:
    """Parse Coupang '다른 판매자' blocks — one block per 판매자: line."""
    hints = _competitor_hints(competitor_name)
    blocks = re.split(r"(?=판매자\s*:)", section)
    for block in blocks:
        if not any(h in block for h in hints):
            continue
        if _is_our_seller(block):
            continue
        per_unit = re.findall(r"(\d{1,3}(?:,\d{3})*)\s*원\s*\(1개당", block)
        for raw in per_unit:
            val = int(raw.replace(",", ""))
            if _price_in_range(val, 1000, 3000):
                return val
        prices = [
            int(x.replace(",", ""))
            for x in re.findall(r"(\d{1,3}(?:,\d{3})*)\s*원", block)
        ]
        for val in prices:
            if _price_in_range(val, 1000, 3000):
                return val
    return None


def _parse_competitor_from_text(
    body: str, competitor_name: str, price_lo: int = 1000, price_hi: int = 3000
) -> int | None:
    hints = _competitor_hints(competitor_name)
    section = _extract_seller_section(body)

    block_price = _parse_bingo_seller_block(section, competitor_name)
    if block_price is not None:
        return block_price

    lines = section.splitlines()
    for i, line in enumerate(lines):
        if not any(h in line for h in hints):
            continue
        if _is_our_seller(line):
            continue
        block = "\n".join(lines[i : i + 8])
        per_unit = re.findall(r"(\d{1,3}(?:,\d{3})*)\s*원\s*\(1개당", block)
        for raw in per_unit:
            val = int(raw.replace(",", ""))
            if _price_in_range(val, price_lo, price_hi):
                return val

    patterns = [
        r"주식회사\s*빙고[^\n]{0,160}?(\d{1,3}(?:,\d{3})*)\s*원",
        r"빙고인터[^\n]{0,160}?(\d{1,3}(?:,\d{3})*)\s*원",
    ]
    for pat in patterns:
        m = re.search(pat, section, re.I)
        if not m:
            continue
        val = int(m.group(1).replace(",", ""))
        if _price_in_range(val, price_lo, price_hi):
            return val
    return None


def _open_other_sellers_modal(page: Page) -> bool:
    patterns = (
        r"다른\s*판매자\s*보기",
        r"다른\s*판매자",
        r"판매자\s*\(\d+\)",
        r"새\s*상품\s*\(\d+\)",
    )
    for pat in patterns:
        try:
            page.get_by_text(re.compile(pat)).first.click(timeout=3500)
            time.sleep(2)
            body = page.evaluate("() => (document.body.innerText || '').slice(0, 8000)")
            if "빙고" in body or re.search(r"판매자|판매\s*가", body):
                return True
        except Exception:
            continue
    return False


def _scrape_bundled_competitor(page: Page, competitor_name: str) -> tuple[int | None, str]:
    opened = _open_other_sellers_modal(page)
    body = page.evaluate("() => (document.body.innerText || '').slice(0, 60000)")

    price_lo, price_hi = 1000, 3000  # 15ml×1 — 빙고·단품 구간
    price = _parse_competitor_from_text(body, competitor_name, price_lo, price_hi)
    if price is None:
        price = _parse_competitor_from_dom(page, competitor_name, price_lo, price_hi)

    tag = "bundled-modal" if opened else "bundled-inline"
    if price is None and opened:
        tag = "bundled-modal-empty"
    return price, tag


def observe_sku(page: Page, sku: SkuTarget) -> PriceObservation:
    notes: list[str] = []

    page.goto(sku.my_url, wait_until="domcontentloaded", timeout=90000)
    time.sleep(3)
    my_body = page.evaluate("() => (document.body.innerText || '')")
    if "Access Denied" in my_body or "접근할 수 없" in my_body:
        time.sleep(5)
        page.reload(wait_until="domcontentloaded")
        time.sleep(3)
        my_body = page.evaluate("() => (document.body.innerText || '')")
    my_price = _main_display_price(page)
    is_winner = bool(re.search(r"아이템\s*위너", my_body, re.I))

    if sku.bundled:
        comp_price, tag = _scrape_bundled_competitor(page, sku.competitor_name)
        notes.append(tag)
    else:
        page.goto(sku.competitor_url, wait_until="domcontentloaded", timeout=90000)
        time.sleep(2.5)
        comp_price = _main_display_price(page)
        notes.append("competitor-page")

    return PriceObservation(
        my_price=my_price,
        competitor_price=comp_price,
        is_winner=is_winner,
        raw_note="; ".join(notes),
    )
