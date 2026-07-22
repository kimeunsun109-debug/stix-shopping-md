# -*- coding: utf-8 -*-
"""Mode A — Chrome CDP collector (coupang.com search + product page)."""
from __future__ import annotations

import re
import time
from datetime import datetime
from urllib.parse import quote

from seo_engine.collectors.base import BaseCollector
from seo_engine.models import CollectionBundle, ProductSnapshot


def _probe_cdp_ports(ports: list[int] | None = None) -> int:
    import urllib.request

    for p in ports or [9222, 9223, 9233]:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{p}/json/version", timeout=2)
            return p
        except Exception:
            continue
    raise RuntimeError(
        "Chrome CDP를 찾을 수 없습니다. "
        "원격 디버깅 포트(9222/9223/9233)로 Chrome을 실행한 뒤 다시 시도하세요."
    )


class CdpCollector(BaseCollector):
    def __init__(
        self,
        *,
        keyword: str,
        mine_url: str = "",
        mine_title: str = "",
        top_n: int = 5,
        cdp_port: int = 0,
        review_limit: int = 30,
    ) -> None:
        self.keyword = keyword
        self.mine_url = mine_url.strip()
        self.mine_title = mine_title.strip()
        self.top_n = top_n
        self.cdp_port = cdp_port
        self.review_limit = review_limit

    def collect(self) -> CollectionBundle:
        from playwright.sync_api import sync_playwright

        port = self.cdp_port or _probe_cdp_ports()
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            page = browser.contexts[0].new_page()
            competitors = self._collect_search_top(page)
            mine = self._collect_mine(page, competitors)
            return CollectionBundle(
                keyword=self.keyword,
                mine=mine,
                competitors=competitors,
                source="cdp",
                marketplace="coupang",
                collected_at=datetime.now().isoformat(timespec="seconds"),
            )

    def _collect_search_top(self, page) -> list[ProductSnapshot]:
        url = f"https://www.coupang.com/np/search?q={quote(self.keyword)}&channel=user"
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        time.sleep(2.5)
        blocked = page.evaluate(
            "() => /access denied|캡차|비정상적인 접근/i.test(document.body.innerText||'')"
        )
        if blocked:
            raise RuntimeError(
                "쿠팡 검색 Access Denied/캡차. Mode B(수동 입력)로 전환하거나 "
                "수동으로 로그인한 Chrome 탭에서 재시도하세요."
            )

        items = page.evaluate(
            """(topN) => {
          const out = [];
          const cards = [...document.querySelectorAll('li.search-product, li[class*=ProductUnit], a[href*=\"/vp/products/\"]')];
          const seen = new Set();
          for (const el of cards) {
            const a = el.tagName === 'A' ? el : el.querySelector('a[href*=\"/vp/products/\"]');
            if (!a) continue;
            const href = a.href || '';
            const m = href.match(/products\\/(\\d+)/);
            if (!m || seen.has(m[1])) continue;
            seen.add(m[1]);
            const root = el.closest('li') || el;
            const title = (root.innerText||'').split('\\n').map(s=>s.trim()).filter(Boolean)[0] || a.innerText || '';
            const priceM = (root.innerText||'').match(/([\\d,]+)원/);
            const reviewM = (root.innerText||'').match(/\\(([\\d,]+)\\)/);
            const img = root.querySelector('img');
            out.push({
              product_id: m[1],
              url: href.split('?')[0],
              title: title.slice(0,120),
              price: priceM ? priceM[1].replace(/,/g,'') : '',
              review_count: reviewM ? reviewM[1].replace(/,/g,'') : '',
              image: img ? (img.src||img.getAttribute('data-img-src')||'') : ''
            });
            if (out.length >= topN) break;
          }
          return out;
        }""",
            self.top_n,
        )
        comps: list[ProductSnapshot] = []
        for i, it in enumerate(items, 1):
            snap = ProductSnapshot(
                title=it.get("title") or "",
                price=int(it["price"]) if it.get("price") else None,
                review_count=int(it["review_count"]) if it.get("review_count") else None,
                image_urls=[it["image"]] if it.get("image") else [],
                url=it.get("url") or "",
                product_id=str(it.get("product_id") or ""),
                rank=i,
            )
            # optional enrich first 3 product pages
            if i <= 3 and snap.url:
                try:
                    enriched = self._scrape_product_page(page, snap.url, review_limit=10)
                    snap.detail_text = enriched.detail_text or snap.detail_text
                    snap.reviews = enriched.reviews or snap.reviews
                    snap.brand = enriched.brand or snap.brand
                    snap.rating = enriched.rating or snap.rating
                    if enriched.title:
                        snap.title = enriched.title
                except Exception:
                    pass
            comps.append(snap)
        return comps

    def _collect_mine(self, page, competitors: list[ProductSnapshot]) -> ProductSnapshot:
        if self.mine_url:
            return self._scrape_product_page(page, self.mine_url, review_limit=self.review_limit)
        if self.mine_title:
            # try match from SERP
            for c in competitors:
                if self.mine_title[:20] in c.title or c.title[:20] in self.mine_title:
                    if c.url:
                        return self._scrape_product_page(page, c.url, review_limit=self.review_limit)
                    return c
            return ProductSnapshot(title=self.mine_title)
        raise ValueError("Mode A: --mine-url 또는 --mine-title 이 필요합니다.")

    def _scrape_product_page(self, page, url: str, review_limit: int = 20) -> ProductSnapshot:
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        time.sleep(2)
        data = page.evaluate(
            """(limit) => {
          const text = document.body.innerText || '';
          const title = (document.querySelector('h1, .prod-buy-header__title')||{}).innerText
            || (document.querySelector('[class*=title]')||{}).innerText || '';
          const brand = (document.querySelector('.prod-brand-name, [class*=brand]')||{}).innerText || '';
          const priceM = text.match(/([\\d,]+)\\s*원/);
          const ratingM = text.match(/([0-5]\\.?\\d?)\\/?5|별점\\s*([0-5]\\.?\\d?)/);
          const reviewM = text.match(/([\\d,]+)\\s*개\\s*상품평|상품평\\s*([\\d,]+)/);
          const imgs = [...document.querySelectorAll('img')].slice(0,8).map(i=>i.src).filter(Boolean);
          // review snippets: lines that look like buyer comments
          const lines = text.split('\\n').map(s=>s.trim()).filter(s=>s.length>12 && s.length<160);
          const reviews = [];
          for (const l of lines) {
            if (/배송|별로|별로예요|만족|좋아요|추천|초보|예쁘|쉽게|선물/.test(l)) {
              reviews.push(l);
              if (reviews.length >= limit) break;
            }
          }
          return {
            title: (title||'').trim().slice(0,150),
            brand: (brand||'').trim().slice(0,40),
            price: priceM ? priceM[1].replace(/,/g,'') : '',
            rating: ratingM ? (ratingM[1]||ratingM[2]) : '',
            review_count: reviewM ? (reviewM[1]||reviewM[2]||'').replace(/,/g,'') : '',
            images: imgs,
            detail: text.slice(0,4000),
            reviews
          };
        }""",
            review_limit,
        )
        pid_m = re.search(r"products/(\d+)", url)
        return ProductSnapshot(
            title=data.get("title") or "",
            brand=data.get("brand") or "",
            price=int(data["price"]) if data.get("price") else None,
            review_count=int(data["review_count"]) if data.get("review_count") else None,
            rating=float(data["rating"]) if data.get("rating") else None,
            image_urls=list(data.get("images") or [])[:8],
            detail_text=data.get("detail") or "",
            reviews=list(data.get("reviews") or []),
            url=url.split("?")[0],
            product_id=pid_m.group(1) if pid_m else "",
        )
