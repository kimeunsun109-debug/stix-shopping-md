# -*- coding: utf-8 -*-
"""경쟁가 크롤링만 테스트 (Wing 미사용)."""
from __future__ import annotations

import sys

from browser import create_driver, wait_page_ready
from competitor import calc_target_price, load_selectors, scrape_competitor_option
from config import load_config
from logger_util import setup_logger

logger = setup_logger()


def main() -> int:
    cfg = load_config()
    selectors = load_selectors(cfg.selectors_path)
    driver = create_driver(cfg)
    try:
        for pset in cfg.price_sets:
            snap = scrape_competitor_option(
                driver,
                cfg.competitor_url,
                pset.competitor_option_label,
                cfg.my_seller_name,
                selectors,
            )
            target = calc_target_price(
                snap.price, cfg.price_undercut, pset.min_price
            )
            logger.info(
                "[%s] 판매자=%s | 경쟁가=%s | 목표가=%s | 본인=%s",
                pset.name,
                snap.seller_name,
                f"{snap.price:,}",
                f"{target:,}",
                "Y" if snap.is_my_listing else "N",
            )
        return 0
    finally:
        if not cfg.use_cdp:
            driver.quit()


if __name__ == "__main__":
    sys.exit(main())
