# -*- coding: utf-8 -*-
"""스마트스토어 등록정보 보완 엑셀 생성."""
from __future__ import annotations

from md_smartstore_reg_common import find_excel, write_review_excel


def main() -> int:
    path = write_review_excel()
    print(f"저장: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
