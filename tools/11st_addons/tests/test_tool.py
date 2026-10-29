"""픽스처 XML 과 가짜 전송으로 추가구성 도구를 검증한다. 네트워크와 API 키는 쓰지 않는다."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

from client import ApiError, ElevenStClient, _NoRedirect, decode_body  # noqa: E402
from runner import read_prd_nos, run_batch, write_results  # noqa: E402
from spec import StockPolicyError, validate_stock  # noqa: E402
from xml_edit import (  # noqa: E402
    UnsafeProductDiff,
    assert_only_addon_markup_changed,
    plan_update,
    verify_reread,
)

FIXTURE = (PKG / "fixtures" / "product_old_addons.xml").read_text(encoding="utf-8")
PRD = "1234567890"


def _without_addons(xml: str) -> str:
    start = xml.index("  <ProductComponent>")
    return xml[:start] + "</Product>\n"


class PlanTests(unittest.TestCase):
    def test_renames_matching_addon_and_appends_missing_without_touching_product(self):
        import re

        box = re.search(
            r"<ProductComponent>\s*<addPrdGrpNm>추가구성</addPrdGrpNm>\s*<compPrdNm>포장박스</compPrdNm>.*?</ProductComponent>",
            FIXTURE,
            re.S,
        ).group(0)
        plan = plan_update(FIXTURE, 100)

        self.assertIn("<![CDATA[<p>상세 설명 그대로</p>]]>", plan.xml)
        self.assertEqual(plan.xml.count("<selPrc>35900</selPrc>"), 1)
        self.assertIn("<stckQty>7</stckQty>", plan.xml)
        self.assertIn("<dlvCst>0</dlvCst>", plan.xml)
        self.assertIn("<cupnDscMthdCd>01</cupnDscMthdCd>", plan.xml)
        self.assertIn(box, plan.xml)
        self.assertNotIn("<compPrdQty>9999</compPrdQty>", plan.xml)

        labels = [view.label() for view in plan.after]
        self.assertEqual(
            labels,
            [
                "코팅제 120ml",
                "포장박스",
                "3구펜+고체풀+트레이세트",
                "B7000 110ml",
                "보조눈금자 11.5cm",
            ],
        )
        coating = plan.after[0]
        self.assertEqual(coating.group, "추가구성")
        self.assertEqual(coating.price, 5500)
        self.assertEqual(coating.qty, 100)
        self.assertEqual(plan.after[1].qty, 3)
        self.assertEqual(plan.after[1].price, 500)
        actions = [change.action for change in plan.changes]
        self.assertEqual(actions.count("add"), 3)
        self.assertIn("rename", actions)
        self.assertIn("keep", actions)

    def test_empty_addon_list_inserts_four_and_keeps_detail(self):
        xml = _without_addons(FIXTURE)
        plan = plan_update(xml, 100)
        self.assertIn("<![CDATA[<p>상세 설명 그대로</p>]]>", plan.xml)
        self.assertEqual([view.label() for view in plan.after], [
            "3구펜+고체풀+트레이세트",
            "코팅제 120ml",
            "B7000 110ml",
            "보조눈금자 11.5cm",
        ])
        self.assertTrue(all(view.qty == 100 and view.price for view in plan.after))
        self.assertIn("<compPrdVatCd>01</compPrdVatCd>", plan.xml)

    def test_already_canonical_is_unchanged_bytes(self):
        planned = plan_update(_without_addons(FIXTURE), 100).xml
        again = plan_update(planned, 100)
        self.assertTrue(again.unchanged)
        self.assertEqual(again.xml, planned)

    def test_two_matches_for_one_target_abort(self):
        xml = FIXTURE.replace(
            "<compPrdNm>포장박스</compPrdNm>",
            "<compPrdNm>구 코팅액</compPrdNm>",
        )
        with self.assertRaises(Exception) as caught:
            plan_update(xml, 100)
        self.assertIn("둘 이상", str(caught.exception))

    def test_outside_edit_is_rejected(self):
        planned = plan_update(FIXTURE, 100).xml
        dirty = planned.replace("<selPrc>35900</selPrc>", "<selPrc>1</selPrc>")
        with self.assertRaises(UnsafeProductDiff):
            assert_only_addon_markup_changed(FIXTURE, dirty)

    def test_unknown_addon_tag_aborts(self):
        xml = FIXTURE.replace(
            "<dlvCst>0</dlvCst>",
            "<dlvCst>0</dlvCst>\n  <addPrdMystery>1</addPrdMystery>",
        )
        with self.assertRaises(Exception) as caught:
            plan_update(xml, 100)
        self.assertIn("해석하지 않는", str(caught.exception))

    def test_unique_group_name_is_renamed(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Product>
  <prdNm>이름</prdNm>
  <selPrc>1000</selPrc>
  <ProductComponent>
    <addPrdGrpNm>구형 코팅제</addPrdGrpNm>
    <compPrdNm>구형 코팅제</compPrdNm>
    <addCompPrc>1</addCompPrc>
    <compPrdQty>9</compPrdQty>
  </ProductComponent>
</Product>
"""
        plan = plan_update(xml, 100)
        self.assertIn("<addPrdGrpNm>코팅제 120ml</addPrdGrpNm>", plan.xml)
        self.assertNotIn("구형 코팅제", plan.xml)
        self.assertIn("<selPrc>1000</selPrc>", plan.xml)

    def test_stock_9999_is_rejected_before_any_edit(self):
        with self.assertRaises(StockPolicyError):
            validate_stock(9999)
        with self.assertRaises(StockPolicyError):
            plan_update(FIXTURE, 9999)

    def test_reread_fails_when_sale_price_moves(self):
        planned = plan_update(FIXTURE, 100).xml
        drifted = planned.replace("<selPrc>35900</selPrc>", "<selPrc>1</selPrc>")
        problems = verify_reread(FIXTURE, drifted, 100)
        self.assertTrue(any("selPrc" in item for item in problems))

    def test_reread_accepts_the_planned_document(self):
        planned = plan_update(FIXTURE, 100).xml
        self.assertEqual(verify_reread(FIXTURE, planned, 100), [])


class FakeClient:
    def __init__(self, xml, fail=(), corrupt=()):
        self.xml = dict(xml)
        self.fail = set(fail)
        self.corrupt = set(corrupt)
        self.fetches: list[str] = []
        self.puts: list[str] = []

    def fetch_product(self, prd_no: str) -> str:
        self.fetches.append(prd_no)
        if prd_no in self.fail:
            raise ApiError("조회 실패")
        return self.xml[prd_no]

    def update_product(self, prd_no: str, xml: str) -> str:
        self.puts.append(prd_no)
        if "SECRET" in xml:
            raise AssertionError("payload contains a secret")
        stored = xml
        if prd_no in self.corrupt:
            stored = xml.replace("<selPrc>35900</selPrc>", "<selPrc>1</selPrc>")
        self.xml[prd_no] = stored
        return "<ClientMessage><resultCode>200</resultCode><message>OK</message></ClientMessage>"


class BatchTests(unittest.TestCase):
    def test_dry_run_writes_no_put_and_records_diff(self):
        client = FakeClient({PRD: FIXTURE, "2222222222": FIXTURE})
        out = io.StringIO()
        report = run_batch(
            [PRD, "2222222222"],
            client,
            apply=False,
            limit=1,
            stock=100,
            backup_dir=Path("/tmp/should-not-be-used"),
            out=out,
        )
        self.assertEqual(client.puts, [])
        self.assertEqual(client.fetches, [PRD])
        self.assertEqual(report.rows[0].status, "dry_run")
        self.assertIn("구형 코팅제", report.rows[0].before)
        self.assertIn("코팅제 120ml|+5500|재고100", report.rows[0].after)
        self.assertEqual(report.rows[1].status, "skipped_limit")
        text = out.getvalue()
        self.assertIn("드라이런", text)
        self.assertIn("추가구성 바깥 XML 토큰은 동일합니다.", text)

    def test_apply_limit_one_and_backup(self):
        client = FakeClient({PRD: FIXTURE, "2222222222": FIXTURE})
        backup = Path(__file__).resolve().parent / "_backup_tmp"
        if backup.exists():
            for child in backup.glob("*"):
                child.unlink()
        out = io.StringIO()
        report = run_batch(
            [PRD, "2222222222"],
            client,
            apply=True,
            limit=1,
            stock=100,
            backup_dir=backup,
            out=out,
        )
        self.assertEqual(client.puts, [PRD])
        self.assertEqual(report.rows[0].status, "verified")
        self.assertEqual(report.rows[1].status, "skipped_limit")
        saved = (backup / f"{PRD}.before.xml").read_text(encoding="utf-8")
        self.assertIn("<compPrdQty>9999</compPrdQty>", saved)
        self.assertNotIn("<compPrdQty>9999</compPrdQty>", client.xml[PRD])
        self.assertIn("<selPrc>35900</selPrc>", client.xml[PRD])
        for child in backup.glob("*"):
            child.unlink()
        backup.rmdir()

    def test_two_consecutive_failures_stop_the_rest(self):
        client = FakeClient(
            {PRD: FIXTURE, "2222222222": FIXTURE, "3333333333": FIXTURE},
            fail=("2222222222", "3333333333"),
        )
        # 첫 상품은 조회 실패가 아니게 두 번째부터 실패시키려면 순서를 실패, 실패, 정상으로.
        client.fail = {PRD, "2222222222"}
        out = io.StringIO()
        report = run_batch(
            [PRD, "2222222222", "3333333333"],
            client,
            apply=True,
            limit=0,
            stock=100,
            backup_dir=None,
            out=out,
        )
        self.assertEqual(client.fetches, [PRD, "2222222222"])
        self.assertEqual(client.puts, [])
        self.assertEqual([row.status for row in report.rows], ["error", "error", "stopped"])
        self.assertFalse(report.ok)

    def test_price_drift_after_put_is_verify_failed(self):
        client = FakeClient({PRD: FIXTURE}, corrupt={PRD})
        out = io.StringIO()
        report = run_batch(
            [PRD],
            client,
            apply=True,
            limit=1,
            stock=100,
            backup_dir=None,
            out=out,
        )
        self.assertEqual(report.rows[0].status, "verify_failed")
        self.assertIn("selPrc", report.rows[0].error)
        self.assertEqual(client.puts, [PRD])

    def test_duplicate_and_csv_roundtrip(self):
        folder = Path(__file__).resolve().parent / "_csv_tmp"
        folder.mkdir(exist_ok=True)
        source = folder / "in.csv"
        target = folder / "out.csv"
        source.write_text("prdNo\n1234567890\n1234567890\n", encoding="utf-8")
        self.assertEqual(read_prd_nos(source), [PRD, PRD])
        client = FakeClient({PRD: FIXTURE})
        report = run_batch(
            read_prd_nos(source),
            client,
            apply=False,
            limit=5,
            stock=100,
            backup_dir=None,
            out=io.StringIO(),
        )
        write_results(target, report.rows)
        text = target.read_text(encoding="utf-8-sig")
        self.assertTrue(text.startswith("prdNo,before add-ons,after add-ons,status,error"))
        self.assertIn("skipped_duplicate", text)
        self.assertEqual(client.puts, [])
        source.unlink()
        target.unlink()
        folder.rmdir()


class ClientTests(unittest.TestCase):
    def test_key_never_appears_in_url_repr_or_errors(self):
        secret = "SECRETKEY1234567890ABCD"

        class Boom:
            def send(self, method, url, headers, body, timeout):
                self.method = method
                self.url = url
                self.header = headers.get("openapikey")
                raise RuntimeError(headers["openapikey"])

        transport = Boom()
        client = ElevenStClient(secret, transport=transport)
        self.assertNotIn(secret, repr(client))
        with self.assertRaises(ApiError) as caught:
            client.fetch_product(PRD)
        self.assertNotIn(secret, str(caught.exception))
        self.assertNotIn(secret, transport.url)
        self.assertEqual(transport.header, secret)
        self.assertTrue(transport.url.endswith(f"/prodservices/product/details/{PRD}"))
        self.assertEqual(transport.method, "GET")

        class Ok:
            def send(self, method, url, headers, body, timeout):
                self.method = method
                self.url = url
                body_text = b"" if body is None else body
                if secret.encode() in body_text or secret in url:
                    raise AssertionError("secret leaked")
                payload = b"<ClientMessage><resultCode>200</resultCode></ClientMessage>"
                return 200, "text/xml; charset=UTF-8", payload

        transport = Ok()
        client = ElevenStClient(secret, transport=transport)
        client.update_product(PRD, "<Product><prdNm>a</prdNm></Product>")
        self.assertEqual(transport.method, "PUT")
        self.assertTrue(transport.url.endswith(f"/prodservices/product/{PRD}"))

    def test_redirect_is_refused(self):
        with self.assertRaises(ApiError):
            _NoRedirect().redirect_request(None, None, 302, "moved", {}, "http://evil.example/")

    def test_euc_kr_body_decodes(self):
        self.assertEqual(decode_body("코팅제".encode("euc-kr"), "text/xml; charset=EUC-KR"), "코팅제")

    def test_missing_key(self):
        with self.assertRaises(Exception):
            ElevenStClient("  ")

    def test_business_error_code_is_not_success(self):
        class Ack:
            def send(self, method, url, headers, body, timeout):
                payload = "<ClientMessage><resultCode>500</resultCode><message>no</message></ClientMessage>"
                return 200, "text/xml", payload.encode()

        client = ElevenStClient("abc123456789", transport=Ack())
        with self.assertRaises(ApiError) as caught:
            client.update_product(PRD, "<Product></Product>")
        self.assertIn("500", str(caught.exception))
        self.assertNotIn("abc123456789", str(caught.exception))


class CliTests(unittest.TestCase):
    def test_missing_key_and_forbidden_stock_do_not_call_network(self):
        from cli import main

        folder = Path(__file__).resolve().parent / "_cli_tmp"
        folder.mkdir(exist_ok=True)
        source = folder / "in.csv"
        target = folder / "out.csv"
        source.write_text("prdNo\n1234567890\n", encoding="utf-8")
        calls = []

        def factory(key):
            calls.append(key)
            return FakeClient({PRD: FIXTURE})

        code = main(
            ["--input", str(source), "--output", str(target), "--addon-stock", "9999"],
            client_factory=factory,
            env={"ELEVENST_API_KEY": "should-not-print"},
            stdout=io.StringIO(),
        )
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])
        self.assertFalse(target.exists())

        out = io.StringIO()
        code = main(
            ["--input", str(source), "--output", str(target)],
            env={},
            stdout=out,
        )
        self.assertEqual(code, 2)
        self.assertIn("ELEVENST_API_KEY", out.getvalue())
        self.assertNotIn("should-not-print", out.getvalue())

        out = io.StringIO()
        code = main(
            ["--input", str(source), "--output", str(target), "--limit", "1"],
            client_factory=factory,
            env={"ELEVENST_API_KEY": "present-but-hidden"},
            stdout=out,
        )
        self.assertEqual(code, 0)
        self.assertEqual(calls, ["present-but-hidden"])
        self.assertIn("드라이런", out.getvalue())
        self.assertNotIn("present-but-hidden", out.getvalue())
        self.assertFalse((folder / "11st_addon_backups").exists())
        text = target.read_text(encoding="utf-8-sig")
        self.assertIn("dry_run", text)
        source.unlink()
        target.unlink()
        folder.rmdir()


if __name__ == "__main__":
    unittest.main()
