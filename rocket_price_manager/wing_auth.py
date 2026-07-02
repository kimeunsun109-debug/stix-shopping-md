# -*- coding: utf-8 -*-
"""쿠팡 Wing(xauth) 로그인 — 검증된 selector (#username, #password, #kc-login)."""
from __future__ import annotations

import logging
import sys
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from browser import wait_page_ready

logger = logging.getLogger("rocket_price")


def is_login_page(driver: webdriver.Chrome, login_sel: dict) -> bool:
    url = driver.current_url.lower()
    if login_sel["login_url_contains"] in url:
        return True
    try:
        body = driver.find_element(By.TAG_NAME, "body").text[:500]
        return "판매자 로그인" in body or "아이디를 입력" in body
    except Exception:
        return False


def is_logged_in(driver: webdriver.Chrome, wing_sel: dict) -> bool:
    url = driver.current_url.lower()
    for bad in wing_sel.get("logged_in_url_excludes", []):
        if bad in url:
            return False
    if "wing.coupang.com" in url:
        try:
            body = driver.find_element(By.TAG_NAME, "body").text[:800]
            if "판매자 로그인" in body or "아이디를 입력" in body:
                return False
            if "Sign in to seller" in body:
                return False
        except Exception:
            pass
        return True
    return False


def login_wing(
    driver: webdriver.Chrome,
    username: str,
    password: str,
    landing_url: str,
    selectors: dict,
    retry_count: int = 3,
    retry_delay: int = 10,
) -> None:
    """
    Wing 로그인.

    xauth 로그인 폼 selector (2026-06-29 probe_results/wing_login.json 검증):
      #username, #password, #kc-login
    """
    login_sel = selectors["login"]
    wing_sel = selectors["wing"]

    driver.get(landing_url)
    wait_page_ready(driver, 4)

    if is_logged_in(driver, wing_sel):
        logger.info("Wing 이미 로그인 상태")
        return

    for attempt in range(1, retry_count + 1):
        try:
            if not is_login_page(driver, login_sel):
                driver.get(landing_url)
                wait_page_ready(driver, 4)

            wait = WebDriverWait(driver, 25)
            user_el = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, login_sel["username"]))
            )
            pass_el = driver.find_element(By.CSS_SELECTOR, login_sel["password"])
            submit = driver.find_element(By.CSS_SELECTOR, login_sel["submit"])

            user_el.clear()
            user_el.send_keys(username)
            pass_el.clear()
            pass_el.send_keys(password)
            submit.click()

            wait_page_ready(driver, 5)

            if is_logged_in(driver, wing_sel):
                logger.info("Wing 로그인 성공")
                return

            raise TimeoutException("로그인 후에도 Wing 페이지 진입 실패")
        except Exception as exc:
            logger.warning("Wing 로그인 실패 (%s/%s): %s", attempt, retry_count, exc)
            time.sleep(retry_delay)

    logger.error("Wing 로그인 최종 실패 — 프로그램 종료")
    sys.exit(1)
