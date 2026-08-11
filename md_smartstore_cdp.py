# -*- coding: utf-8 -*-
"""스마트스토어 CDP 페이지 조작 공통."""
from __future__ import annotations

import json
import re
import time
import urllib.request

from playwright.sync_api import Page

from md_smartstore_reg_common import CDP, filter_tags_for_store


def cleanup_cdp_tabs(port: int = 9233) -> None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=3) as r:
            tabs = json.loads(r.read())
        for t in tabs:
            url = t.get("url", "")
            if "/products/edit/" in url or "diagnosis" in url:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/json/close/{t['id']}", timeout=2
                )
    except Exception:
        pass


def get_work_page(browser):
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "smartstore.naver.com" in pg.url:
                return pg
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    page = ctx.new_page()
    page.goto(
        "https://sell.smartstore.naver.com/#/products/origin-list",
        wait_until="domcontentloaded",
        timeout=90000,
    )
    time.sleep(3)
    return page


def attach_dialog_handler(page: Page) -> None:
    page.on("dialog", lambda d: d.accept())


def dismiss_modals(page: Page) -> None:
    page.evaluate(
        """() => {
          for (const b of document.querySelectorAll('button')) {
            const t = (b.innerText || '').trim();
            if (['확인','닫기','나중에'].includes(t)) b.click();
          }
        }"""
    )


def select_selling_filter(page: Page) -> None:
    page.evaluate(
        """() => {
          const labels = [...document.querySelectorAll('label,span,button')];
          const el = labels.find(e => (e.innerText||'').trim() === '판매중');
          el?.click();
        }"""
    )


def expand_search_settings(page: Page) -> None:
    page.evaluate(
        """() => {
          const blocks = [...document.querySelectorAll('div,section')].filter(d => {
            const t = d.innerText || '';
            return t.startsWith('검색설정') && t.includes('태그') && t.length < 3000;
          });
          blocks[0]?.querySelector('a.btn.btn-default')?.click();
        }"""
    )


def read_product_tags(page: Page) -> list[str]:
    return page.evaluate(
        """() => [...document.querySelectorAll('.tag-area .tag, .tag-list .tag, span.tag')]
          .map(e => (e.innerText||'').replace(/×/g,'').trim()).filter(Boolean)"""
    )


def clear_one_product_tag(page: Page) -> bool:
    return page.evaluate(
        """() => {
          const close = document.querySelector('.tag-area .tag .btn-delete, .tag .close, .tag button');
          if (close) { close.click(); return true; }
          const tags = [...document.querySelectorAll('.tag-area .tag, span.tag')];
          const last = tags[tags.length-1];
          last?.querySelector('button,a,span')?.click();
          return !!last;
        }"""
    )


def leave_edit_to_list(page: Page) -> None:
    page.evaluate(
        """() => {
          const btns = [...document.querySelectorAll('button,a')];
          const cancel = btns.find(b => (b.innerText||'').trim() === '취소');
          cancel?.click();
        }"""
    )
    time.sleep(0.8)
    page.evaluate(
        """() => {
          const btn = [...document.querySelectorAll('button')].find(b => (b.innerText||'').trim() === '확인');
          btn?.click();
        }"""
    )


def ensure_list_page(page: Page) -> None:
    try:
        body = page.locator("body").inner_text(timeout=3000) or ""
    except Exception:
        body = ""
    if "/products/edit/" in page.url or "검색설정" in body:
        leave_edit_to_list(page)
        time.sleep(1)
    if "#/products/origin-list" not in page.url:
        page.goto(
            "https://sell.smartstore.naver.com/#/products/origin-list",
            wait_until="domcontentloaded",
            timeout=90000,
        )
    for _ in range(15):
        time.sleep(1)
        if page.evaluate("() => document.querySelectorAll('.ag-row').length") > 0:
            return
    select_selling_filter(page)
    time.sleep(3)


def open_product_edit(page: Page, product_id: str) -> bool:
    cleanup_cdp_tabs()
    ensure_list_page(page)
    dismiss_modals(page)
    select_selling_filter(page)
    time.sleep(1)
    page.locator("input[type=text]").nth(1).fill(product_id)
    page.keyboard.press("Enter")
    time.sleep(4)
    opened = page.evaluate(
        """(pid) => {
          const row = [...document.querySelectorAll('.ag-row')].find(r => r.innerText.includes(pid));
          const btn = row?.querySelector('button[data-nclicks-code="itg.edit"]');
          if (btn) { btn.click(); return true; }
          const links = [...(row?.querySelectorAll('a,button,span') || [])]
            .filter(e => (e.innerText || '').trim() === '수정');
          if (links[0]) { links[0].click(); return true; }
          return false;
        }""",
        product_id,
    )
    if not opened:
        return False
    for _ in range(20):
        time.sleep(1)
        body = page.locator("body").inner_text(timeout=5000)
        if "검색설정" in body or "브랜드를 입력" in body or "상품수정" in body:
            return True
    return False


def ensure_tag_input_visible(page: Page) -> bool:
    page.evaluate(
        """() => {
          const el = [...document.querySelectorAll('*')].find(e => (e.innerText || '').includes('검색설정'));
          el?.scrollIntoView({block: 'center'});
        }"""
    )
    time.sleep(0.8)
    for _ in range(4):
        if page.locator('input[placeholder="태그를 입력해주세요."]').count():
            return True
        expand_search_settings(page)
        time.sleep(0.8)
    return page.locator('input[placeholder="태그를 입력해주세요."]').count() > 0


def search_product_exists(page: Page, product_id: str) -> bool:
    ensure_list_page(page)
    dismiss_modals(page)
    select_selling_filter(page)
    time.sleep(1)
    page.locator("input[type=text]").nth(1).fill(product_id)
    page.keyboard.press("Enter")
    time.sleep(3)
    return page.evaluate(
        """(pid) => [...document.querySelectorAll('.ag-row')].some(r => r.innerText.includes(pid))""",
        product_id,
    )


def apply_tags_via_edit(page: Page, row: dict, *, dry_run: bool = False, extra_tags: list[str] | None = None) -> dict:
    pid = row["product_id"]
    all_tags = [t.strip() for t in row["tags"].split(",") if t.strip()]
    if extra_tags:
        all_tags = extra_tags + all_tags
    expected_tags = filter_tags_for_store(all_tags, row.get("brand", ""))
    res = {
        "product_id": pid,
        "name": row.get("name", "")[:60],
        "ok": False,
        "expected_tags": expected_tags,
        "applied_tags": [],
        "steps": [],
    }

    if not open_product_edit(page, pid):
        res["error"] = "수정 페이지 로드 실패"
        return res

    if not ensure_tag_input_visible(page):
        res["error"] = "태그 입력란 없음"
        return res

    existing = set(read_product_tags(page))
    expected_set = set(expected_tags)
    overlap = existing & expected_set
    res["steps"].append(f"existing:{len(existing)} overlap:{len(overlap)}")

    if len(existing) >= 8 and len(overlap) >= min(3, len(expected_set)) and not extra_tags:
        res["applied_tags"] = list(existing)
        res["ok"] = True
        res["steps"].append("skip:overlap_ok")
        return res

    to_add = [t for t in expected_tags if t not in existing]
    while len(existing) >= 10 and to_add:
        if existing - expected_set:
            clear_one_product_tag(page)
            time.sleep(0.3)
            existing = set(read_product_tags(page))
            to_add = [t for t in expected_tags if t not in existing]
            continue
        break

    if dry_run:
        res["applied_tags"] = list(existing) + to_add[: 10 - len(existing)]
        res["ok"] = True
        res["steps"].append("dry_run")
        return res

    tag_input = page.locator('input[placeholder="태그를 입력해주세요."]')
    for tag in to_add:
        if len(read_product_tags(page)) >= 10:
            break
        if not ensure_tag_input_visible(page):
            break
        tag_input.fill(tag)
        page.keyboard.press("Enter")
        time.sleep(0.4)

    save = page.get_by_role("button", name=re.compile("저장"))
    for i in range(save.count()):
        try:
            if save.nth(i).is_visible():
                save.nth(i).click(timeout=5000)
                break
        except Exception:
            pass
    time.sleep(2)
    dismiss_modals(page)

    final = read_product_tags(page)
    res["applied_tags"] = final
    res["ok"] = len(final) >= min(5, len(expected_tags))
    res["steps"].append(f"final:{len(final)}")
    leave_edit_to_list(page)
    return res
