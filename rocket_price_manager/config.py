# -*- coding: utf-8 -*-
"""환경변수(.env) 로드 및 설정 검증."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f".env 필수값 누락: {name}")
    return value


def _int(name: str, default: int | None = None) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        if default is None:
            raise ValueError(f".env 필수값 누락: {name}")
        return default
    return int(raw)


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class PriceSetConfig:
    """경쟁 옵션 1개 + Wing 수정 대상 1개."""

    name: str
    competitor_option_label: str
    min_price: int
    wing_option_label: str
    wing_search_keyword: str


@dataclass(frozen=True)
class AppConfig:
    competitor_url: str
    my_product_url: str
    my_seller_name: str
    wing_username: str
    wing_password: str
    vendor_inventory_id: str
    price_undercut: int
    check_interval: int
    headless: bool
    retry_count: int
    retry_delay: int
    use_cdp: bool
    cdp_port: int
    chrome_user_data_dir: str
    chrome_profile: str
    wing_page_mode: str
    price_sets: list[PriceSetConfig]
    selectors_path: Path


def load_config() -> AppConfig:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        print(f"[ERROR] .env 파일이 없습니다: {env_path}")
        print("       .env.example 을 복사해 .env 를 만든 뒤 값을 입력하세요.")
        sys.exit(1)

    load_dotenv(env_path, override=True)

    price_sets = [
        PriceSetConfig(
            name="SET2",
            competitor_option_label=os.getenv("COMPETITOR_SET2_LABEL", "2개").strip(),
            min_price=_int("MIN_PRICE_SET2"),
            wing_option_label=os.getenv("WING_SET2_OPTION_LABEL", "").strip()
            or os.getenv("COMPETITOR_SET2_LABEL", "2개").strip(),
            wing_search_keyword=os.getenv("WING_SET2_SEARCH_KEYWORD", "B7000").strip(),
        ),
        PriceSetConfig(
            name="SET4",
            competitor_option_label=os.getenv("COMPETITOR_SET4_LABEL", "4개").strip(),
            min_price=_int("MIN_PRICE_SET4"),
            wing_option_label=os.getenv("WING_SET4_OPTION_LABEL", "").strip()
            or os.getenv("COMPETITOR_SET4_LABEL", "4개").strip(),
            wing_search_keyword=os.getenv("WING_SET4_SEARCH_KEYWORD", "B7000").strip(),
        ),
    ]

    user_data = os.getenv("CHROME_USER_DATA_DIR", "").strip()
    if not user_data:
        user_data = str(BASE_DIR.parent / "chrome_md_profile")

    use_cdp = _bool("USE_CDP", False)
    wing_user = os.getenv("WING_USERNAME", "").strip()
    wing_pass = os.getenv("WING_PASSWORD", "").strip()
    if not use_cdp and (not wing_user or not wing_pass):
        raise ValueError(".env 필수값 누락: WING_USERNAME / WING_PASSWORD (또는 USE_CDP=true)")

    return AppConfig(
        competitor_url=_require("COMPETITOR_URL"),
        my_product_url=_require("MY_PRODUCT_URL"),
        my_seller_name=_require("MY_SELLER_NAME"),
        wing_username=wing_user,
        wing_password=wing_pass,
        vendor_inventory_id=os.getenv("VENDOR_INVENTORY_ID", "").strip(),
        price_undercut=_int("PRICE_UNDERCUT", 100),
        check_interval=_int("CHECK_INTERVAL", 600),
        headless=_bool("HEADLESS", False),
        retry_count=_int("RETRY_COUNT", 3),
        retry_delay=_int("RETRY_DELAY", 10),
        use_cdp=use_cdp,
        cdp_port=_int("CDP_PORT", 9233),
        chrome_user_data_dir=user_data,
        chrome_profile=os.getenv("CHROME_PROFILE", "Default").strip(),
        wing_page_mode=os.getenv("WING_PAGE_MODE", "modify").strip(),
        price_sets=price_sets,
        selectors_path=BASE_DIR / "selectors.json",
    )
