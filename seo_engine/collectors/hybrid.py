# -*- coding: utf-8 -*-
"""Hybrid collector: Mode A with automatic fallback to Mode B."""
from __future__ import annotations

from pathlib import Path

from seo_engine.collectors.base import BaseCollector
from seo_engine.collectors.cdp import CdpCollector
from seo_engine.collectors.manual import ManualCollector
from seo_engine.models import CollectionBundle, ProductSnapshot


class HybridCollector(BaseCollector):
    """
    Tries CdpCollector first. On Access Denied / bot / CDP failure,
    falls back to ManualCollector with the same keyword/mine fields.
    """

    def __init__(
        self,
        *,
        keyword: str,
        mine_url: str = "",
        mine_title: str = "",
        mine_brand: str = "",
        mine_detail: str = "",
        reviews: list[str] | None = None,
        competitors: list | None = None,
        input_path: str | Path | None = None,
        top_n: int = 5,
        cdp_port: int = 0,
        prefer: str = "cdp",  # cdp | manual
    ) -> None:
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
        self.prefer = prefer

    def collect(self) -> CollectionBundle:
        if self.prefer == "manual":
            return self._manual().collect()

        try:
            bundle = CdpCollector(
                keyword=self.keyword,
                mine_url=self.mine_url,
                mine_title=self.mine_title,
                top_n=self.top_n,
                cdp_port=self.cdp_port,
            ).collect()
            return bundle
        except Exception as e:
            msg = str(e)
            fallback = self._manual()
            # if manual has no data, re-raise with guidance
            try:
                bundle = fallback.collect()
            except Exception as e2:
                raise RuntimeError(
                    f"Mode A 실패 ({msg}). Mode B 전환도 실패 ({e2}). "
                    f"--input 또는 --mine-title/--competitors 를 제공하세요."
                ) from e2
            bundle.source = "hybrid"
            bundle.fallback_note = f"Mode A 실패 -> Mode B 자동전환: {msg[:200]}"
            return bundle

    def _manual(self) -> ManualCollector:
        mine = None
        if self.mine_title or self.mine_url:
            mine = ProductSnapshot(
                title=self.mine_title,
                brand=self.mine_brand,
                detail_text=self.mine_detail,
                url=self.mine_url,
                reviews=list(self.reviews),
            )
        return ManualCollector(
            keyword=self.keyword,
            mine=mine,
            competitors=self.competitors,
            path=self.input_path,
        )
