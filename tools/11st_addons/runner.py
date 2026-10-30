"""CSV 상품번호마다 추가구성을 맞춘다. 기본은 원격에 쓰지 않는다."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from client import ApiError
from spec import CANONICAL_ADDONS, StockPolicyError, SpecError, validate_stock
from xml_edit import (
    Plan,
    UnsafeProductDiff,
    XmlShapeError,
    format_addon_list,
    format_diff,
    plan_update,
    verify_reread,
)

RESULT_FIELDS = ["prdNo", "before add-ons", "after add-ons", "status", "error"]
MAX_CONSECUTIVE_FAILURES = 2


class InputError(ValueError):
    pass


@dataclass
class Row:
    prd_no: str
    before: str = ""
    after: str = ""
    status: str = ""
    error: str = ""

    def as_csv(self) -> dict[str, str]:
        return {
            "prdNo": self.prd_no,
            "before add-ons": self.before,
            "after add-ons": self.after,
            "status": self.status,
            "error": self.error,
        }

    @property
    def failed(self) -> bool:
        return self.status in {
            "aborted_unsafe_diff",
            "error",
            "verify_failed",
            "ambiguous",
        }


@dataclass
class BatchReport:
    rows: list[Row] = field(default_factory=list)
    puts: int = 0

    @property
    def ok(self) -> bool:
        return not any(row.failed or row.status == "stopped" for row in self.rows)


def read_prd_nos(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise InputError(f"입력 CSV를 읽지 못했습니다: {path}") from exc
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames or "prdNo" not in reader.fieldnames:
        raise InputError("입력 CSV 첫 줄에 prdNo 열이 있어야 합니다.")
    numbers: list[str] = []
    for index, record in enumerate(reader, start=2):
        raw = (record.get("prdNo") or "").strip()
        if not raw:
            continue
        if not raw.isdigit() or not 6 <= len(raw) <= 15:
            raise InputError(f"{index}행 prdNo 가 상품번호 형식이 아닙니다: {raw}")
        numbers.append(raw)
    if not numbers:
        raise InputError("prdNo 가 한 건도 없습니다.")
    return numbers


def write_results(path: Path, rows: list[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_csv())


def run_batch(
    prd_nos: list[str],
    client,
    *,
    apply: bool,
    limit: int,
    stock: int,
    backup_dir: Path | None,
    out,
) -> BatchReport:
    validate_stock(stock)
    if limit < 0:
        raise InputError("--limit 는 0 이상이어야 합니다. 0 은 제한 없음입니다.")
    report = BatchReport()
    seen: set[str] = set()
    consecutive = 0
    stopped = False
    attempted = 0
    for prd_no in prd_nos:
        if prd_no in seen:
            report.rows.append(Row(prd_no, status="skipped_duplicate", error="같은 상품번호가 앞에 있습니다."))
            continue
        seen.add(prd_no)
        if stopped:
            report.rows.append(
                Row(prd_no, status="stopped", error="연속 실패 2회로 배치를 멈췄습니다.")
            )
            continue
        if limit and attempted >= limit:
            report.rows.append(Row(prd_no, status="skipped_limit", error=f"--limit {limit}"))
            continue
        attempted += 1
        row = _process_one(
            prd_no,
            client,
            apply=apply,
            stock=stock,
            backup_dir=backup_dir,
            out=out,
            report=report,
        )
        report.rows.append(row)
        if row.failed:
            consecutive += 1
            if consecutive >= MAX_CONSECUTIVE_FAILURES:
                stopped = True
        else:
            consecutive = 0
    return report


def _process_one(prd_no, client, *, apply, stock, backup_dir, out, report: BatchReport) -> Row:
    try:
        before_xml = client.fetch_product(prd_no)
    except ApiError as exc:
        print(f"[{prd_no}] 조회 실패: {exc}", file=out)
        return Row(prd_no, status="error", error=str(exc))
    if not _addon_blocks_present(before_xml):
        print(
            f"[{prd_no}] 재고 조회(stck)에 추가구성이 없습니다. "
            "셀러오피스 화면에 있으면 조회가 누락한 것이니 --apply 하지 마세요. 중복 등록됩니다.",
            file=out,
        )
    try:
        plan = plan_update(before_xml, stock)
    except (SpecError, XmlShapeError, UnsafeProductDiff, StockPolicyError) as exc:
        status = "aborted_unsafe_diff" if isinstance(exc, UnsafeProductDiff) else "ambiguous"
        if isinstance(exc, XmlShapeError):
            status = "error"
        print(f"[{prd_no}] {exc}", file=out)
        return Row(prd_no, status=status, error=str(exc))

    print(format_diff(plan, prd_no), file=out)
    before = format_addon_list(plan.before)
    after = format_addon_list(plan.after)
    if plan.unchanged:
        print(f"[{prd_no}] 이미 목표와 같습니다. 쓰지 않습니다.", file=out)
        return Row(prd_no, before, after, "unchanged", "")
    if not apply:
        print(f"[{prd_no}] 드라이런. 서버에 쓰지 않습니다.", file=out)
        return Row(prd_no, before, after, "dry_run", "")

    try:
        _backup(backup_dir, prd_no, before_xml)
    except OSError as exc:
        print(f"[{prd_no}] 로컬 백업 실패. 서버에는 쓰지 않았습니다: {exc}", file=out)
        return Row(prd_no, before, after, "error", f"백업 실패: {exc}")
    try:
        client.update_product(prd_no, plan.xml)
        report.puts += 1
        reread = client.fetch_product(prd_no)
    except ApiError as exc:
        print(f"[{prd_no}] 쓰기 또는 재조회 실패: {exc}", file=out)
        return Row(prd_no, before, after, "error", str(exc))

    problems = verify_reread(before_xml, reread, stock)
    if problems:
        message = " ; ".join(problems)
        print(f"[{prd_no}] 재조회 확인 실패: {message}", file=out)
        return Row(prd_no, before, after, "verify_failed", message)
    print(f"[{prd_no}] 반영 후 재조회에서 판매가·주요 항목이 같고 추가구성이 목표와 같습니다.", file=out)
    return Row(prd_no, before, after, "verified", "")


def _backup(backup_dir: Path | None, prd_no: str, xml: str) -> None:
    if backup_dir is None:
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"{prd_no}.before.xml"
    # 파일은 UTF-8 로 남기고, 조회 응답의 euc-kr 선언도 UTF-8 로 맞춘다.
    text = re.sub(r"""(<\?xml[^>]*?encoding\s*=\s*["'])[^"']+""", r"\g<1>UTF-8", xml, count=1)
    target.write_text(text, encoding="utf-8")


def _addon_blocks_present(xml: str) -> bool:
    return "ProductComponent" in xml


def expected_managed_names() -> list[str]:
    return [spec.name for spec in CANONICAL_ADDONS]
