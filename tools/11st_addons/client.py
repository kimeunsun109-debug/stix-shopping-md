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


_XML_DECL_ENCODING = re.compile(rb"""^\s*<\?xml[^>]*?encoding\s*=\s*["']([A-Za-z0-9._-]+)["']""")


def xml_declared_encoding(raw: bytes) -> str:
    match = _XML_DECL_ENCODING.match(raw.lstrip(b"\xef\xbb\xbf")[:200])
    return match.group(1).decode("ascii") if match else ""


def decode_body(raw: bytes, content_type: str | None) -> str:
    """11번가 응답은 EUC-KR 이다. 헤더 charset, XML 선언, EUC-KR(CP949), UTF-8 순으로 읽는다."""
    declared = ""
    if content_type:
        for part in content_type.split(";"):
            item = part.strip()
            if item.lower().startswith("charset="):
                declared = item.split("=", 1)[1].strip().strip('"')
                break
    encodings: list[str] = []
    for encoding in (declared, xml_declared_encoding(raw), "euc-kr", "cp949", "utf-8"):
        if not encoding:
            continue
        # EUC-KR 로 선언돼도 확장 한글이 섞일 수 있어 CP949 를 바로 뒤에 둔다.
        candidates = [encoding, "cp949"] if encoding.lower() in {"euc-kr", "euckr", "ks_c_5601-1987"} else [encoding]
        for item in candidates:
            if item.lower() not in {known.lower() for known in encodings}:
                encodings.append(item)
    last_error: UnicodeDecodeError | None = None
    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError) as exc:
            if isinstance(exc, UnicodeDecodeError):
                last_error = exc
            continue
    raise ApiError("응답 인코딩을 읽지 못했습니다.") from last_error


PUT_ENCODING = "euc-kr"
_DECLARATION = re.compile(r"^\ufeff?\s*<\?xml[^>]*\?>\s*")
# 조회 응답에만 있는 안내 값. 저장 본문에서는 뺀다.
READ_ONLY_FIELDS = ("message", "validateMsg", "nResult", "selStatNm")


def encode_put_body(xml: str) -> bytes:
    """저장 본문은 EUC-KR 바이트와 같은 선언으로 보낸다. EUC-KR 로 못 쓰는 글자가 있으면 보내지 않는다."""
    body = _DECLARATION.sub("", xml, count=1)
    for name in READ_ONLY_FIELDS:
        body = re.sub(rf"<{name}\b[^>]*/>|<{name}\b[^>]*>.*?</{name}>", "", body, count=1, flags=re.DOTALL)
    text = f'<?xml version="1.0" encoding="{PUT_ENCODING}" standalone="yes"?>' + body
    try:
        return text.encode(PUT_ENCODING)
    except UnicodeEncodeError as exc:
        raise ApiError(f"EUC-KR 로 쓸 수 없는 글자가 있어 저장하지 않습니다: {exc.object[exc.start:exc.end]!r}") from None


_STCK_COMPONENT = re.compile(
    r"<(?:[\w.-]+:)?productComponent\b[^>]*>(.*?)</(?:[\w.-]+:)?productComponent>",
    re.DOTALL,
)
_PRODUCT_CLOSE = re.compile(r"</(?:[\w.-]+:)?Product\s*>")


def stck_components(stck_xml: str) -> list[str]:
    """재고 조회(stck) 응답의 productComponent 안쪽 XML 목록."""
    if not re.search(r"<(?:[\w.-]+:)?ProductStocks\b", stck_xml):
        raise ApiError("재고 조회 응답이 ProductStocks 가 아닙니다.")
    return [match.group(1) for match in _STCK_COMPONENT.finditer(stck_xml)]


def merge_components(product_xml: str, stck_xml: str) -> str:
    """상품 조회 XML 끝에 stck 의 추가구성을 ProductComponent 블록으로 붙인다.

    상품 조회(prodmarket)에는 추가구성이 없고 stck 에만 있다. 비교와 저장 본문은 이 합친 XML 로 한다.
    """
    if re.search(r"<(?:[\w.-]+:)?ProductComponent\b", product_xml):
        raise ApiError("상품 조회에 ProductComponent 가 이미 있습니다. 합치지 않습니다.")
    closes = list(_PRODUCT_CLOSE.finditer(product_xml))
    if not closes:
        raise ApiError("상품 XML 에 Product 닫는 태그가 없습니다.")
    blocks = []
    for inner in stck_components(stck_xml):
        fields = re.findall(r"<([A-Za-z]\w*)\b[^>]*/>|<([A-Za-z]\w*)\b[^>]*>(.*?)</\2>", inner, re.DOTALL)
        rows = "".join(
            f"<{empty}></{empty}>" if empty else f"<{name}>{value}</{name}>"
            for empty, name, value in fields
        )
        blocks.append(f"\n  <ProductComponent>{rows}</ProductComponent>")
    close = closes[-1]
    # 공백으로 띄워 둬야 새 줄을 끼워 넣어도 바깥 토큰 비교가 흔들리지 않는다.
    return product_xml[: close.start()] + "".join(blocks) + "\n" + product_xml[close.start() :]


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

    def fetch_base_product(self, prd_no: str) -> str:
        """prodmarketservice/prodmarket: 상품 전체 XML. 추가구성은 없다."""
        url = f"{self._base}/prodmarketservice/prodmarket/{prd_no}"
        status, text = self._request("GET", url, None)
        if status != 200:
            raise ApiError(f"상품 조회 실패 HTTP {status}{_error_hint(text)}")
        _reject_failure_code(text, allow_missing=True)
        if not re.search(r"<(?:[\w.-]+:)?Product\b", text):
            raise ApiError("상품 XML 이 아닌 응답입니다.")
        return text

    def fetch_stock(self, prd_no: str) -> str:
        """prodmarketservice/prodmarket/stck: 재고와 현재 추가구성(productComponents)."""
        url = f"{self._base}/prodmarketservice/prodmarket/stck/{prd_no}"
        status, text = self._request("GET", url, None)
        if status != 200:
            raise ApiError(f"재고·추가구성 조회 실패 HTTP {status}{_error_hint(text)}")
        _reject_failure_code(text, allow_missing=True)
        stck_components(text)
        return text

    def fetch_product(self, prd_no: str) -> str:
        """상품 XML 에 현재 추가구성을 합친 XML. 둘 중 하나라도 실패하면 오류다."""
        base = self.fetch_base_product(prd_no)
        stock = self.fetch_stock(prd_no)
        return merge_components(base, stock)

    def update_product(self, prd_no: str, xml: str) -> str:
        url = f"{self._base}/prodservices/product/{prd_no}"
        status, text = self._request("PUT", url, encode_put_body(xml))
        if status != 200:
            raise ApiError(f"상품 수정 실패 HTTP {status}{_error_hint(text)}")
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
            headers["Content-Type"] = f"text/xml; charset={PUT_ENCODING.upper()}"
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


def _error_hint(text: str) -> str:
    """오류 응답의 resultCode/message 를 짧게 붙인다. 키는 _request 에서 이미 가렸다."""
    code = re.search(r"<(?:[\w.-]+:)?resultCode>\s*([^<]*?)\s*<", text)
    message = re.search(r"<(?:[\w.-]+:)?message>\s*([^<]*?)\s*<", text)
    parts = [item.group(1)[:80] for item in (code, message) if item and item.group(1)]
    return f" ({' '.join(parts)})" if parts else ""


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
