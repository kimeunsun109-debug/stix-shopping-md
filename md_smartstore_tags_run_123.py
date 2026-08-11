# -*- coding: utf-8 -*-
"""1→2→3 순서 실행: 태그 보충 → 30건 대조 → 나머지 태그 배치."""
from __future__ import annotations

import subprocess
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent
CDP = "http://127.0.0.1:9233"


def cdp_ok() -> bool:
    try:
        with urllib.request.urlopen(f"{CDP}/json/version", timeout=2) as r:
            return bool(r.read())
    except Exception:
        return False


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    return subprocess.call(cmd, cwd=BASE)


def main() -> int:
    if not cdp_ok():
        print("CDP(Chrome 9233) 없음 — 오프라인 작업만 실행합니다.")
        print("로컬에서 start_chrome_for_md.bat 실행 후 이 스크립트를 다시 실행하세요.")
        run([sys.executable, "md_smartstore_registration_review.py"])
        run([sys.executable, "md_smartstore_tag_reconcile.py"])
        return 1

    # 1) 12668512904 태그 보충
    rc = run([
        sys.executable, "md_smartstore_registration_apply.py",
        "--product-id", "12668512904",
        "--extra-tags", "뜨개가방,뜨개질,DIY,취미,수예,만들기",
    ])
    if rc:
        print("태그 보충 실패 — 중단")
        return rc

    # 2) 30건 대조 (라이브)
    run([sys.executable, "md_smartstore_tag_reconcile.py", "--live"])

    # 3) 나머지 태그 (--start 30) + 실패 17건 재시도
    rc = run([
        sys.executable, "md_smartstore_registration_apply.py",
        "--mode", "tags", "--start", "30",
    ])
    if rc:
        return rc
    return run([
        sys.executable, "md_smartstore_registration_apply.py",
        "--mode", "tags", "--retry-failed",
    ])


if __name__ == "__main__":
    raise SystemExit(main())
