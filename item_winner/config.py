# -*- coding: utf-8
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkuTarget:
    key: str
    label: str
    my_url: str
    competitor_url: str
    vendor_item_id: str
    min_price: int
    step: int = 10
    target_price: int | None = None
    hold_price: int | None = None  # 유지가 (reactive_lower_only 시)
    reactive_lower_only: bool = False  # 경쟁자 인하 시에만 추격, 동가·인상 시 유지
    competitor_name: str = ""
    bundled: bool = False  # same PDP — scrape competitor from modal


B7000_TARGETS: list[SkuTarget] = [
    SkuTarget(
        key="p1_15mlx1",
        label="1번 B7000 15ml×1 (vs 빙고)",
        my_url="https://www.coupang.com/vp/products/9208609745?itemId=27375322495&vendorItemId=94214344499",
        competitor_url="https://www.coupang.com/vp/products/9208609745?itemId=27375322495&vendorItemId=94214344499",
        vendor_item_id="94214344499",
        min_price=1290,
        target_price=1500,
        competitor_name="빙고",
        bundled=True,
    ),
    SkuTarget(
        key="p2_15mlx3",
        label="2번 B7000 15ml×3 (vs 온라인마켓)",
        my_url="https://www.coupang.com/vp/products/9349553166?itemId=27735684713&vendorItemId=94705203391",
        competitor_url="https://www.coupang.com/vp/products/9628775687?itemId=28758431435&vendorItemId=95697083224",
        vendor_item_id="94705203391",
        min_price=9790,
        target_price=9990,
        competitor_name="온라인",
    ),
    SkuTarget(
        key="p3_110mlx2",
        label="3번 B7000 110ml×2 (vs 온라인마켓)",
        my_url="https://www.coupang.com/vp/products/9351979625?itemId=27744180453&vendorItemId=94705203395",
        competitor_url="https://www.coupang.com/vp/products/9619525970?itemId=28724704543&vendorItemId=95622458586",
        vendor_item_id="94705203395",
        min_price=12490,
        target_price=13800,
        hold_price=13800,
        reactive_lower_only=True,
        competitor_name="온라인",
    ),
]

INTERVAL_SEC = 30 * 60
MONITOR_UNTIL: str | None = None  # None = 종료일 없이 계속 모니터링
