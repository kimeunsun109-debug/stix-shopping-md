# -*- coding: utf-8 -*-
"""STIX MD - ① 엑셀 다운로드 + ② 가격/매출 분석 일괄 실행"""
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent


def run(script: str) -> int:
    print(f"\n=== {script} ===")
    return subprocess.call([sys.executable, str(BASE / script)])


def main():
    (BASE / "쇼핑몰별 전체상품").mkdir(exist_ok=True)
    (BASE / "쇼핑몰별 매출주문").mkdir(exist_ok=True)

    rc1 = run("md_export_download.py")
    rc2 = run("md_price_sales_analyze.py")
    # CDP fetch 보조
    rc3 = run("md_seller_fetch.py")

    print("\n=== done ===")
    print("  md_export_download:", "ok" if rc1 == 0 else "partial/fail")
    print("  md_price_sales_analyze:", "ok" if rc2 == 0 else "fail")
    print("  md_seller_fetch:", "ok" if rc3 == 0 else "fail")
    return 0 if rc2 == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
