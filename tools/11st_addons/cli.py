"""명령행. 기본은 드라이런이고, --apply 가 있을 때만 상품 수정 PUT 을 보낸다."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from client import DEFAULT_BASE_URL, ElevenStClient, MissingApiKey
from runner import InputError, run_batch, write_results
from spec import DEFAULT_ADDON_STOCK, StockPolicyError, validate_stock


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 tools/11st_addons/run.py",
        description=(
            "11번가 기존 상품의 추가구성상품 4종만 맞춥니다. "
            "기본은 조회와 diff 만 하고 서버에 쓰지 않습니다."
        ),
    )
    parser.add_argument("--input", required=True, type=Path, help="prdNo 열이 있는 CSV")
    parser.add_argument("--output", required=True, type=Path, help="결과 CSV")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="실제로 상품 수정 요청을 보냅니다. 없으면 드라이런입니다.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="처리할 상품 수. 기본 1. 0 이면 제한 없음.",
    )
    parser.add_argument(
        "--addon-stock",
        type=int,
        default=DEFAULT_ADDON_STOCK,
        help=f"맞추는 추가구성의 재고. 기본 {DEFAULT_ADDON_STOCK}. 9999 는 거부.",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=None,
        help="--apply 때 수정 전 XML 을 저장할 폴더. 기본은 결과 CSV 옆 11st_addon_backups/",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="셀러 REST 기본 주소. 테스트용.",
    )
    return parser


def main(argv: list[str] | None = None, *, client_factory=None, env=None, stdout=None) -> int:
    stdout = stdout or sys.stdout
    args = build_parser().parse_args(argv)
    try:
        validate_stock(args.addon_stock)
        prd_nos = read_input(args.input)
    except (InputError, StockPolicyError) as exc:
        print(str(exc), file=stdout)
        return 2

    environ = os.environ if env is None else env
    try:
        client = _client(environ, args.base_url, client_factory)
    except MissingApiKey as exc:
        print(str(exc), file=stdout)
        return 2

    backup_dir = None
    if args.apply:
        backup_dir = args.backup_dir or (args.output.parent / "11st_addon_backups")
        scope = "제한 없이" if args.limit == 0 else f"최대 {args.limit}개"
        print(f"모드: 적용. 이번 실행은 {scope} 상품에 수정 요청을 보냅니다.", file=stdout)
    else:
        print("모드: 드라이런. 서버에 쓰지 않습니다.", file=stdout)

    report = run_batch(
        prd_nos,
        client,
        apply=args.apply,
        limit=args.limit,
        stock=args.addon_stock,
        backup_dir=backup_dir,
        out=stdout,
    )
    write_results(args.output, report.rows)
    print(f"결과 CSV: {args.output}", file=stdout)
    return 0 if report.ok else 1


def read_input(path: Path):
    from runner import read_prd_nos

    return read_prd_nos(path)


def _client(env, base_url: str, client_factory):
    key = env.get("ELEVENST_API_KEY", "")
    if client_factory is not None:
        return client_factory(key)
    return ElevenStClient(key, base_url=base_url)
