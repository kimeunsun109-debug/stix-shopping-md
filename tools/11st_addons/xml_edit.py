"""상품 XML에서 ProductComponent 블록만 바꾸고, 바깥 토큰은 그대로 둔다.

전체 트리를 다시 직렬화하지 않는다. 상세 HTML 의 CDATA 와 옵션 블록 바이트를
보존하기 위해서다. 근거와 한계는 docs/11st-api-notes.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

from spec import (
    CANONICAL_ADDONS,
    NEW_COMPONENT_VAT,
    AddonSpec,
    SpecError,
    match_spec,
    validate_specs,
    validate_stock,
)


class XmlShapeError(ValueError):
    pass


class UnsafeProductDiff(ValueError):
    pass


_COMPONENT_OPEN = re.compile(r"<(?P<prefix>[\w.-]+:)?ProductComponent\b")
_PRODUCT_CLOSE = re.compile(r"</(?:[\w.-]+:)?Product\s*>")
_SUSPICIOUS = re.compile(
    r"<(?:[\w.-]+:)?([A-Za-z0-9_]*(?:Component|AddPrd|addPrd|CompPrd|addComp)[A-Za-z0-9_]*)\b"
)

# 적용 후 재조회에서 같아야 하는 단일 필드. 전체 문서 비교는 조회시각 같은 변동 필드 때문에 하지 않는다.
EXACT_FIELDS = (
    "prdNm",
    "htmlDetail",
    "sellerPrdCd",
    "dispCtgrNo",
    "prdImage01",
    "prdImage02",
    "prdImage03",
    "prdImage04",
    "prdImage05",
    "selMthdCd",
    "orgnTypCd",
    "brand",
)
NUMERIC_FIELDS = ("selPrc", "prdSelQty")
PREFIX_FIELDS = ("dlv", "cupon", "cupn", "dsc", "mileage", "point", "pnt")
BLOCK_TAGS = ("ProductOption", "ProductOptionExt", "ProductCustOption", "ProductStock")


@dataclass
class AddonView:
    group: str
    name: str
    price: int | None
    qty: int | None
    use_yn: str

    def label(self) -> str:
        return self.name.strip() or self.group.strip()

    def render(self) -> str:
        price = "" if self.price is None else f"+{self.price}"
        qty = "" if self.qty is None else str(self.qty)
        return f"{self.label()}|{price}|재고{qty}"


@dataclass
class Change:
    action: str  # rename, add, keep
    before: str
    after: str


@dataclass
class Plan:
    xml: str
    before: list[AddonView]
    after: list[AddonView]
    changes: list[Change] = field(default_factory=list)

    @property
    def unchanged(self) -> bool:
        return not any(change.action != "keep" for change in self.changes)


@dataclass(frozen=True)
class _Block:
    start: int
    end: int
    text: str
    prefix: str


def plan_update(
    xml: str,
    stock: int,
    specs: tuple[AddonSpec, ...] = CANONICAL_ADDONS,
) -> Plan:
    validate_stock(stock)
    validate_specs(specs)
    _require_product(xml)
    blocks = _component_blocks(xml)
    _reject_unknown_addon_markup(xml, blocks)
    parsed = [_read_component(block.text) for block in blocks]
    shared_groups = _shared_groups(parsed)
    assignments = _assign(parsed, specs)

    pieces: list[str] = []
    cursor = 0
    changes: list[Change] = []
    after: list[AddonView] = []
    used_specs: set[str] = set()

    for block, view in zip(blocks, parsed):
        pieces.append(xml[cursor:block.start])
        spec = assignments[id(view)]
        if spec is None:
            pieces.append(block.text)
            after.append(view)
            changes.append(Change("keep", view.render(), view.render()))
        else:
            updated, new_view, changed = _rewrite_block(block, view, spec, stock, shared_groups)
            pieces.append(updated)
            after.append(new_view)
            changes.append(
                Change("rename" if changed else "keep", view.render(), new_view.render())
            )
            used_specs.add(spec.name)
        cursor = block.end

    pieces.append(xml[cursor:])
    missing = [spec for spec in specs if spec.name not in used_specs]
    prefix = blocks[0].prefix if blocks else ""
    if missing:
        insertion = "".join(_new_component(prefix, spec, stock) for spec in missing)
        close = _last_product_close(pieces[-1] if pieces else xml)
        # pieces[-1] 은 마지막 블록 뒤의 꼬리다. 닫는 Product 는 거기에 있다.
        tail = pieces[-1]
        pieces[-1] = tail[: close.start()] + insertion + tail[close.start() :]
        for spec in missing:
            created = AddonView(spec.name, spec.name, spec.price, stock, "Y")
            after.append(created)
            changes.append(Change("add", "(없음)", created.render()))

    updated_xml = "".join(pieces)
    assert_only_addon_markup_changed(xml, updated_xml)
    return Plan(xml=updated_xml, before=parsed, after=after, changes=changes)


def assert_only_addon_markup_changed(before_xml: str, after_xml: str) -> None:
    """ProductComponent 를 뺀 나머지 토큰이 같아야 한다."""
    before_left = _mask_components(before_xml)
    after_left = _mask_components(after_xml)
    before_tokens = re.findall(r"\S+", before_left)
    after_tokens = re.findall(r"\S+", after_left)
    if before_tokens != after_tokens:
        detail = _first_token_diff(before_tokens, after_tokens)
        raise UnsafeProductDiff(
            "추가구성 바깥 글자가 달라 이 상품은 쓰지 않습니다. " + detail
        )


def verify_reread(
    before_xml: str,
    after_xml: str,
    stock: int,
    specs: tuple[AddonSpec, ...] = CANONICAL_ADDONS,
) -> list[str]:
    """적용 후 재조회가 본상품 주요 필드를 유지하고 목표 추가구성만 바뀌었는지."""
    problems: list[str] = []
    before_plain = _mask_components(before_xml)
    after_plain = _mask_components(after_xml)
    for name in EXACT_FIELDS:
        if _field_inner(before_plain, name) != _field_inner(after_plain, name):
            problems.append(f"{name} 이 달라졌습니다")
    for name in NUMERIC_FIELDS:
        if _field_number(before_plain, name) != _field_number(after_plain, name):
            problems.append(f"{name} 이 달라졌습니다")
    for name in _prefixed_names(before_plain) | _prefixed_names(after_plain):
        if _field_inner(before_plain, name) != _field_inner(after_plain, name):
            problems.append(f"{name} 이 달라졌습니다")
    for tag in BLOCK_TAGS:
        if _block_tokens(before_plain, tag) != _block_tokens(after_plain, tag):
            problems.append(f"{tag} 블록이 달라졌습니다")

    before_views = [_read_component(block.text) for block in _component_blocks(before_xml)]
    after_views = [_read_component(block.text) for block in _component_blocks(after_xml)]
    managed = {spec.name for spec in specs}
    before_extra = sorted(_unmanaged(before_views, specs))
    after_extra = sorted(view.render() for view in after_views if view.label() not in managed)
    if before_extra != after_extra:
        problems.append("목표 외 추가구성이 달라졌습니다")
    for spec in specs:
        matches = [view for view in after_views if view.label() == spec.name]
        if len(matches) != 1:
            problems.append(f"{spec.name} 이 {len(matches)}개입니다")
            continue
        view = matches[0]
        if view.price != spec.price:
            problems.append(f"{spec.name} 가격이 {view.price}입니다")
        if view.qty != stock:
            problems.append(f"{spec.name} 재고가 {view.qty}입니다")
        if view.qty in {9999, 99999}:
            problems.append(f"{spec.name} 재고가 금지 값입니다")
    return problems


def format_diff(plan: Plan, prd_no: str) -> str:
    lines = [f"[{prd_no}] 추가구성 diff"]
    for change in plan.changes:
        if change.action == "keep":
            lines.append(f"  유지  {change.before}")
        elif change.action == "add":
            lines.append(f"  추가  {change.before}  →  {change.after}")
        else:
            lines.append(f"  변경  {change.before}  →  {change.after}")
    if plan.unchanged:
        lines.append("  바꿀 추가구성이 없습니다.")
    lines.append("  추가구성 바깥 XML 토큰은 동일합니다.")
    return "\n".join(lines)


def format_addon_list(views: list[AddonView]) -> str:
    return " ; ".join(view.render() for view in views)


def _assign(views: list[AddonView], specs: tuple[AddonSpec, ...]) -> dict[int, AddonSpec | None]:
    found: dict[str, int] = {}
    assigned: dict[int, AddonSpec | None] = {}
    for view in views:
        spec = match_spec([view.group, view.name], specs)
        if spec is not None:
            if spec.name in found:
                raise SpecError(
                    f"목표 '{spec.name}' 에 해당하는 기존 추가구성이 둘 이상입니다."
                )
            found[spec.name] = id(view)
        assigned[id(view)] = spec
    return assigned


def _rewrite_block(
    block: _Block,
    view: AddonView,
    spec: AddonSpec,
    stock: int,
    shared_groups: set[str],
) -> tuple[str, AddonView, bool]:
    text = block.text
    group_shared = bool(view.group.strip()) and view.group.strip() in shared_groups
    new_group = view.group if group_shared else spec.name
    text = _set_child(text, "compPrdNm", spec.name)
    if not group_shared:
        text = _set_child(text, "addPrdGrpNm", spec.name)
    text = _set_child(text, "addCompPrc", str(spec.price))
    text = _set_child(text, "compPrdQty", str(stock))
    if _child_text(text, "addUseYn") is not None:
        text = _set_child(text, "addUseYn", "Y")
    new_view = AddonView(new_group, spec.name, spec.price, stock, "Y" if _child_text(text, "addUseYn") else view.use_yn)
    return text, new_view, text != block.text


def _new_component(prefix: str, spec: AddonSpec, stock: int) -> str:
    tag = f"{prefix}ProductComponent"
    rows = (
        ("addPrdGrpNm", spec.name),
        ("compPrdNm", spec.name),
        ("addCompPrc", str(spec.price)),
        ("compPrdQty", str(stock)),
        ("compPrdVatCd", NEW_COMPONENT_VAT),
        ("addUseYn", "Y"),
    )
    inner = "".join(f"\n    <{prefix}{name}>{escape(value)}</{prefix}{name}>" for name, value in rows)
    return f"\n  <{tag}>{inner}\n  </{tag}>"


def _read_component(block: str) -> AddonView:
    return AddonView(
        group=_child_text(block, "addPrdGrpNm") or "",
        name=_child_text(block, "compPrdNm") or "",
        price=_parse_won(_child_text(block, "addCompPrc")),
        qty=_parse_won(_child_text(block, "compPrdQty")),
        use_yn=(_child_text(block, "addUseYn") or "").strip(),
    )


def _shared_groups(views: list[AddonView]) -> set[str]:
    counts: dict[str, int] = {}
    for view in views:
        group = view.group.strip()
        if group:
            counts[group] = counts.get(group, 0) + 1
    return {group for group, count in counts.items() if count >= 2}


def _component_blocks(xml: str) -> list[_Block]:
    blocks: list[_Block] = []
    pos = 0
    while True:
        match = _COMPONENT_OPEN.search(xml, pos)
        if not match:
            return blocks
        start = match.start()
        gt = xml.find(">", match.end())
        if gt < 0:
            raise XmlShapeError("ProductComponent 태그가 닫히지 않았습니다.")
        prefix = match.group("prefix") or ""
        if xml[gt - 1] == "/":
            end = gt + 1
        else:
            close = f"</{prefix}ProductComponent>"
            found = xml.find(close, gt + 1)
            if found < 0:
                raise XmlShapeError("ProductComponent 닫는 태그가 없습니다.")
            end = found + len(close)
        blocks.append(_Block(start, end, xml[start:end], prefix))
        pos = end


def _mask_components(xml: str) -> str:
    blocks = _component_blocks(xml)
    parts: list[str] = []
    cursor = 0
    for block in blocks:
        parts.append(xml[cursor:block.start])
        cursor = block.end
    parts.append(xml[cursor:])
    return "".join(parts)


def _reject_unknown_addon_markup(xml: str, blocks: list[_Block]) -> None:
    plain = _mask_components(xml)
    unknown = sorted(set(_SUSPICIOUS.findall(plain)))
    if unknown:
        raise XmlShapeError(
            "해석하지 않는 추가구성 태그가 있어 쓰지 않습니다: " + ", ".join(unknown)
        )
    if blocks and not plain:
        raise XmlShapeError("상품 XML 이 추가구성만으로 이루어져 있습니다.")


def _require_product(xml: str) -> None:
    if _PRODUCT_CLOSE.search(xml) is None:
        raise XmlShapeError("상품 XML 에 Product 닫는 태그가 없습니다.")
    if "<" not in xml:
        raise XmlShapeError("상품 XML 이 아닙니다.")


def _last_product_close(tail: str) -> re.Match[str]:
    matches = list(_PRODUCT_CLOSE.finditer(tail))
    if not matches:
        raise XmlShapeError("추가구성을 넣을 Product 닫는 태그를 찾지 못했습니다.")
    return matches[-1]


def _set_child(block: str, field: str, value: str) -> str:
    pair = re.compile(
        rf"(<(?:[\w.-]+:)?{field}\b[^>]*>)(.*?)(</(?:[\w.-]+:)?{field}>)",
        re.DOTALL,
    )
    found = list(pair.finditer(block))
    if len(found) > 1:
        raise XmlShapeError(f"{field} 태그가 한 추가구성 안에 둘 이상입니다.")
    if len(found) == 1:
        match = found[0]
        return block[: match.start(2)] + escape(value) + block[match.end(2) :]
    empty = re.compile(rf"<(?:[\w.-]+:)?{field}\b[^>]*/>")
    emptied = list(empty.finditer(block))
    if len(emptied) > 1:
        raise XmlShapeError(f"{field} 태그가 한 추가구성 안에 둘 이상입니다.")
    if len(emptied) == 1:
        match = emptied[0]
        prefix = _prefix_of(match.group(0))
        replacement = f"<{prefix}{field}>{escape(value)}</{prefix}{field}>"
        return block[: match.start()] + replacement + block[match.end() :]
    close = re.search(rf"</(?P<prefix>[\w.-]+:)?ProductComponent>", block)
    if not close:
        raise XmlShapeError("ProductComponent 닫는 태그가 없습니다.")
    prefix = close.group("prefix") or ""
    inserted = f"\n    <{prefix}{field}>{escape(value)}</{prefix}{field}>"
    return block[: close.start()] + inserted + block[close.start() :]


def _child_text(block: str, field: str) -> str | None:
    match = re.search(
        rf"<(?:[\w.-]+:)?{field}\b[^>]*>(.*?)</(?:[\w.-]+:)?{field}>",
        block,
        re.DOTALL,
    )
    if not match:
        return None
    return _unescape(match.group(1).strip())


def _field_inner(xml: str, field: str) -> str | None:
    match = re.search(
        rf"<(?:[\w.-]+:)?{field}\b[^>]*>(.*?)</(?:[\w.-]+:)?{field}>",
        xml,
        re.DOTALL,
    )
    if not match:
        return None
    return match.group(1).strip()


def _field_number(xml: str, field: str) -> int | None:
    return _parse_won(_field_inner(xml, field))


def _prefixed_names(xml: str) -> set[str]:
    names: set[str] = set()
    for match in re.finditer(r"<(?:[\w.-]+:)?([A-Za-z][\w.-]*)\b", xml):
        name = match.group(1)
        if name.startswith(PREFIX_FIELDS):
            names.add(name)
    return names


def _block_tokens(xml: str, tag: str) -> tuple[str, ...]:
    pattern = re.compile(
        rf"<(?:[\w.-]+:)?{tag}\b[^>]*>.*?</(?:[\w.-]+:)?{tag}>",
        re.DOTALL,
    )
    return tuple(re.sub(r"\s+", "", match.group(0)) for match in pattern.finditer(xml))


def _unmanaged(views: list[AddonView], specs: tuple[AddonSpec, ...]) -> list[str]:
    rendered: list[str] = []
    for view in views:
        try:
            spec = match_spec([view.group, view.name], specs)
        except SpecError:
            spec = None
        if spec is None and view.label() not in {item.name for item in specs}:
            rendered.append(view.render())
    return rendered


def _parse_won(value: str | None) -> int | None:
    if value is None:
        return None
    digits = value.replace(",", "").strip()
    if not digits:
        return None
    if re.fullmatch(r"-?\d+\.0+", digits):
        digits = digits.split(".", 1)[0]
    if re.fullmatch(r"-?\d+", digits):
        return int(digits)
    return None


def _unescape(value: str) -> str:
    return (
        value.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&apos;", "'")
        .replace("&amp;", "&")
    )


def _prefix_of(tag_open: str) -> str:
    match = re.match(r"<(?P<prefix>[\w.-]+:)?", tag_open)
    return match.group("prefix") or "" if match else ""


def _first_token_diff(before: list[str], after: list[str]) -> str:
    for index, (left, right) in enumerate(zip(before, after)):
        if left != right:
            return f"위치 {index}: {left[:60]!r} → {right[:60]!r}"
    return f"토큰 수 {len(before)} → {len(after)}"
