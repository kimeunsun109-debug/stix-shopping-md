# -*- coding: utf-8 -*-
"""Marketplace collectors — thin adapters; Analyzer stays shared.

Add a new marketplace by implementing BaseCollector that returns CollectionBundle
with marketplace=<name>. Mode A/B/Hybrid still apply via underlying collectors.
"""
from __future__ import annotations

from pathlib import Path

from seo_engine.collectors.base import BaseCollector
from seo_engine.collectors.cdp import CdpCollector
from seo_engine.collectors.hybrid import HybridCollector
from seo_engine.collectors.manual import ManualCollector
from seo_engine.models import CollectionBundle, ProductSnapshot


def _tag(bundle: CollectionBundle, marketplace: str) -> CollectionBundle:
    bundle.marketplace = marketplace
    return bundle


class CoupangCollector(BaseCollector):
    """Default Coupang adapter (CDP / Manual / Hybrid)."""

    def __init__(
        self,
        *,
        mode: str = "manual",
        keyword: str = "",
        mine_url: str = "",
        mine_title: str = "",
        mine_brand: str = "",
        mine_detail: str = "",
        reviews: list[str] | None = None,
        competitors: list | None = None,
        input_path: str | Path | None = None,
        top_n: int = 5,
        cdp_port: int = 0,
    ) -> None:
        self.mode = mode
        self.keyword = keyword
        self.mine_url = mine_url
        self.mine_title = mine_title
        self.mine_brand = mine_brand
        self.mine_detail = mine_detail
        self.reviews = reviews or []
        self.competitors = competitors or []
        self.input_path = input_path
        self.top_n = top_n
        self.cdp_port = cdp_port

    def collect(self) -> CollectionBundle:
        if self.mode == "cdp":
            return _tag(
                CdpCollector(
                    keyword=self.keyword,
                    mine_url=self.mine_url,
                    mine_title=self.mine_title,
                    top_n=self.top_n,
                    cdp_port=self.cdp_port,
                ).collect(),
                "coupang",
            )
        if self.mode == "auto":
            return _tag(
                HybridCollector(
                    keyword=self.keyword,
                    mine_url=self.mine_url,
                    mine_title=self.mine_title,
                    mine_brand=self.mine_brand,
                    mine_detail=self.mine_detail,
                    reviews=self.reviews,
                    competitors=self.competitors,
                    input_path=self.input_path,
                    top_n=self.top_n,
                    cdp_port=self.cdp_port,
                ).collect(),
                "coupang",
            )
        mine = None
        if self.mine_title or self.mine_url:
            mine = ProductSnapshot(
                title=self.mine_title,
                brand=self.mine_brand,
                detail_text=self.mine_detail,
                url=self.mine_url,
                reviews=list(self.reviews),
            )
        return _tag(
            ManualCollector(
                keyword=self.keyword,
                mine=mine,
                competitors=self.competitors,
                path=self.input_path,
            ).collect(),
            "coupang",
        )


class _MarketplaceManualCollector(BaseCollector):
    """Mode B wrapper for non-Coupang marketplaces (same schema, different tag)."""

    marketplace: str = "generic"

    def __init__(
        self,
        *,
        keyword: str = "",
        mine: ProductSnapshot | dict | None = None,
        competitors: list | None = None,
        path: str | Path | None = None,
    ) -> None:
        self._inner = ManualCollector(
            keyword=keyword, mine=mine, competitors=competitors or [], path=path
        )

    def collect(self) -> CollectionBundle:
        return _tag(self._inner.collect(), self.marketplace)


class SmartStoreCollector(_MarketplaceManualCollector):
    marketplace = "smartstore"


class GmarketCollector(_MarketplaceManualCollector):
    marketplace = "gmarket"


class AuctionCollector(_MarketplaceManualCollector):
    marketplace = "auction"


class ElevenStreetCollector(_MarketplaceManualCollector):
    marketplace = "11st"


class AmazonCollector(_MarketplaceManualCollector):
    marketplace = "amazon"


MARKETPLACE_COLLECTORS = {
    "coupang": CoupangCollector,
    "smartstore": SmartStoreCollector,
    "gmarket": GmarketCollector,
    "auction": AuctionCollector,
    "11st": ElevenStreetCollector,
    "amazon": AmazonCollector,
}
