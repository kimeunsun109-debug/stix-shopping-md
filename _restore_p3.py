# -*- coding: utf-8
"""Restore p3 to hold price 13800."""
from playwright.sync_api import sync_playwright
from item_winner.wing_apply import ensure_wing_login, set_vendor_item_price
from item_winner.env_util import load_env

VID = "94705203395"
HOLD = 13800

with sync_playwright() as pw:
    page = pw.chromium.connect_over_cdp("http://127.0.0.1:9233").contexts[0].new_page()
    env = load_env()
    login = ensure_wing_login(page, env)
    print("login:", login.message)
    res = set_vendor_item_price(page, VID, HOLD)
    print("apply:", res.ok, res.message)
    page.close()
