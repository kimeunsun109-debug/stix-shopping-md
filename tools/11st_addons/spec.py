"""스팃스 액자형 추가구성 4종과 재고 정책.

필드 의미와 근거는 docs/11st-api-notes.md 에 있다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AddonSpec:
    name: str
    price: int
    keywords: tuple[str, ...]


# 구매자 화면에 맞출 이름. 가격은 추가금액(원).
CANONICAL_ADDONS: tuple[AddonSpec, ...] = (
    AddonSpec("3구펜+고체풀+트레이세트", 1000, ("3구펜", "고체풀", "트레이세트")),
    AddonSpec("보석십자수 코팅제 120ml", 5500, ("코팅제", "코팅액")),
    AddonSpec("B7000 보석십자수본드 110ml", 5000, ("b7000", "b-7000")),
    AddonSpec("보석십자수 보조눈금자 11.5cm", 5000, ("보조눈금자", "눈금자")),
)

# 셀러오피스 화면 안내의 추가상품명 길이. API 최대 길이는 미확인이라 화면 기준으로 막는다.
MAX_NAME_CHARS = 25

# 8578012899 를 셀러오피스에서 손으로 맞춘 값과 같게 999.
DEFAULT_ADDON_STOCK = 999
MIN_ADDON_STOCK = 1
MAX_ADDON_STOCK = 1000
# 셀러오피스에서 재고를 9999로 잘못 넣는 경우가 있어 그 값은 어떤 경우에도 받지 않는다.
FORBIDDEN_STOCKS = frozenset({9999, 99999})

# 새 줄에만 넣는다. 01 = 과세. 기존 줄의 부가세 코드는 유지한다.
NEW_COMPONENT_VAT = "01"

# 목표 4종은 모두 이 그룹 이름(addPrdGrpNm)으로 맞춘다. 셀러오피스 직접 등록 화면 기본값과 같다.
ADDON_GROUP = "추가구성"


class StockPolicyError(ValueError):
    pass


class SpecError(ValueError):
    pass


def validate_stock(stock: int) -> int:
    if isinstance(stock, bool) or not isinstance(stock, int):
        raise StockPolicyError("추가구성 재고는 정수여야 합니다.")
    if stock in FORBIDDEN_STOCKS:
        raise StockPolicyError(
            f"추가구성 재고 {stock}은 입력 실수로 보고 거부합니다. "
            f"기본값은 {DEFAULT_ADDON_STOCK}입니다."
        )
    if stock < MIN_ADDON_STOCK or stock > MAX_ADDON_STOCK:
        raise StockPolicyError(
            f"추가구성 재고는 {MIN_ADDON_STOCK}~{MAX_ADDON_STOCK}만 허용합니다. 받은 값: {stock}"
        )
    return stock


def validate_specs(specs: tuple[AddonSpec, ...] = CANONICAL_ADDONS) -> None:
    seen: set[str] = set()
    for spec in specs:
        if spec.name in seen:
            raise SpecError(f"추가구성 이름이 중복됩니다: {spec.name}")
        seen.add(spec.name)
        if len(spec.name) > MAX_NAME_CHARS:
            raise SpecError(
                f"추가구성 이름이 {MAX_NAME_CHARS}자를 넘습니다: {spec.name}"
            )
        if spec.price < 0:
            raise SpecError(f"추가금액이 음수입니다: {spec.name}")
        if not spec.keywords:
            raise SpecError(f"이름 맞춤 키워드가 없습니다: {spec.name}")


def normalize_label(value: str) -> str:
    return value.casefold().replace(" ", "").replace("-", "")


def match_spec(names: list[str], specs: tuple[AddonSpec, ...] = CANONICAL_ADDONS) -> AddonSpec | None:
    """이름 후보가 가리키는 목표 추가구성. 두 종류 이상이면 SpecError."""
    blob = " ".join(normalize_label(name) for name in names if name and name.strip())
    if not blob:
        return None
    hits = [
        spec
        for spec in specs
        if any(normalize_label(keyword) in blob for keyword in spec.keywords)
    ]
    if len(hits) > 1:
        joined = ", ".join(spec.name for spec in hits)
        raise SpecError(f"한 추가구성이 여러 목표와 겹칩니다 ({joined}): {names}")
    return hits[0] if hits else None
