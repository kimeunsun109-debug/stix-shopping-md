# -*- coding: utf-8 -*-
"""Selenium WebDriver 생성 (webdriver-manager + Chrome 프로필)."""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

if TYPE_CHECKING:
    from config import AppConfig

logger = logging.getLogger("rocket_price")


def create_driver(cfg: "AppConfig") -> webdriver.Chrome:
    """
    Chrome WebDriver 생성.

    - HEADLESS=false: 실제 창 표시 (Wing SPA 디버깅용)
    - CHROME_USER_DATA_DIR: 로그인 세션 유지 (쿠팡 Wing 재로그인 최소화)
    - USE_CDP=true: 이미 실행 중인 Chrome(CDP)에 attach
    """
    if cfg.use_cdp:
        return _create_cdp_driver(cfg)

    options = Options()
    if cfg.headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=ko-KR")
    options.add_argument(f"--user-data-dir={cfg.chrome_user_data_dir}")
    options.add_argument(f"--profile-directory={cfg.chrome_profile}")
    # 자동화 탐지 완화
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(90)
    driver.implicitly_wait(0)
    return driver


def _create_cdp_driver(cfg: "AppConfig") -> webdriver.Chrome:
    """remote-debugging-port 로 실행된 Chrome 에 attach."""
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{cfg.cdp_port}")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(90)
    driver.implicitly_wait(0)
    logger.info("CDP attach: 127.0.0.1:%s", cfg.cdp_port)
    return driver


def wait_page_ready(driver: webdriver.Chrome, seconds: float = 3.0) -> None:
    """SPA 렌더링 대기."""
    time.sleep(seconds)
