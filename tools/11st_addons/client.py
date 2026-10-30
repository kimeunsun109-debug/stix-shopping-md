"""11번가 셀러 REST 호출.

키는 생성자에만 둔다. URL, 예외 문자열, repr 에 넣지 않는다.
경로는 docs/11st-api-notes.md 의 근거를 따른다. 추가구성 전용 쓰기는 없다.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from collections.abc import Mapping
from xml.etree import ElementTree as ET

DEFAULT_BASE_URL = "http://api.11st.co.kr/rest"
TIMEOUT_SECONDS = 30


class MissingApiKey(RuntimeError):
    pass


class ApiError(RuntimeError):
    pass


def redact(text: str, secret: str) -> str:
    if not secret:
        return text
    return text.replace(secret, "***")


def decode_body(raw: bytes, content_type: str | None) -> str:
    declared = ""
    if content_type:
        for part in content_type.split(";"):
            item = part.strip()
            if item.lower().startswith("charset="):
                declared = item.split("=", 1)[1].strip().strip('"')
                break
    encodings: list[str] = []
    for encoding in (declared, "utf-8", "euc-kr", "cp949"):
        if encoding and encoding.lower() not in {item.lower() for item in encodings}:
            encodings.append(encoding)
    last_error: UnicodeDecodeError | None = None
    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError) as exc:
            if isinstance(exc, UnicodeDecodeError):
                last_error = exc
            continue
    raise ApiError("응답 인코딩을 읽지 못했습니다.") from last_error


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise ApiError(f"리다이렉트를 거부했습니다 ({code}).")


class UrllibTransport:
    def send(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> tuple[int, str, bytes]:
        request = urllib.request.Request(url, data=body, headers=dict(headers), method=method)
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            with opener.open(request, timeout=timeout) as response:
                payload = response.read()
                content_type = response.headers.get("Content-Type", "")
                return response.status, content_type, payload
        except ApiError:
            raise
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
            return exc.code, content_type, payload
        except urllib.error.URLError as exc:
            raise ApiError("11번가에 연결하지 못했습니다.") from exc


class ElevenStClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        transport: UrllibTransport | None = None,
        timeout: float = TIMEOUT_SECONDS,
    ) -> None:
        key = (api_key or "").strip()
        if not key:
            raise MissingApiKey("ELEVENST_API_KEY 가 없습니다.")
        self._key = key
        self._base = base_url.rstrip("/")
        self._transport = transport or UrllibTransport()
        self._timeout = timeout

    def __repr__(self) -> str:
        return "ElevenStClient(api_key='***')"

    def fetch_product(self, prd_no: str) -> str:
        url = f"{self._base}/prodservices/product/details/{prd_no}"
        status, text = self._request("GET", url, None)
        if status != 200:
            raise ApiError(f"상품 조회 실패 HTTP {status}")
        _reject_failure_code(text, allow_missing=True)
        if not re.search(r"<(?:[\w.-]+:)?Product\b", text):
            raise ApiError("상품 XML 이 아닌 응답입니다.")
        return text

    def update_product(self, prd_no: str, xml: str) -> str:
        url = f"{self._base}/prodservices/product/{prd_no}"
        status, text = self._request("PUT", url, xml.encode("utf-8"))
        if status != 200:
            raise ApiError(f"상품 수정 실패 HTTP {status}")
        _reject_failure_code(text, allow_missing=True)
        return text

    def _request(self, method: str, url: str, body: bytes | None) -> tuple[int, str]:
        if self._key in url:
            raise ApiError("API 키를 URL에 넣지 않습니다.")
        headers = {
            "openapikey": self._key,
            "Accept": "application/xml, text/xml, */*",
        }
        if body is not None:
            headers["Content-Type"] = "text/xml; charset=UTF-8"
        try:
            status, content_type, payload = self._transport.send(
                method, url, headers, body, self._timeout
            )
        except ApiError as exc:
            raise ApiError(redact(str(exc), self._key)) from None
        except Exception as exc:
            raise ApiError(redact(f"요청 실패: {exc}", self._key)) from None
        try:
            text = decode_body(payload, content_type)
        except ApiError as exc:
            raise ApiError(redact(str(exc), self._key)) from None
        return status, redact(text, self._key)


def _reject_failure_code(xml: str, allow_missing: bool) -> None:
    code = _result_code(xml)
    if code is None and allow_missing:
        return
    if code == "200":
        return
    if code is None:
        raise ApiError("응답에 resultCode 가 없습니다.")
    raise ApiError(f"11번가 resultCode {code}")


def _result_code(xml: str) -> str | None:
    try:
        root = ET.fromstring(_strip_declaration(xml))
    except ET.ParseError:
        return None
    root_name = root.tag.split("}", 1)[-1]
    # 상세 조회 본문에 resultCode 비슷한 값이 있어도 응답 코드로 보지 않는다.
    if root_name.lower() == "product":
        return None
    for element in root.iter():
        name = element.tag.split("}", 1)[-1]
        if name == "resultCode" and element.text and element.text.strip():
            return element.text.strip()
    return None


def _strip_declaration(xml: str) -> str:
    text = xml.lstrip("\ufeff")
    if text.startswith("<?xml"):
        end = text.find("?>")
        if end != -1:
            return text[end + 2 :]
    return text
