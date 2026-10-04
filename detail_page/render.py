# -*- coding: utf-8 -*-
"""상품 콜라주(2x2) → 패널 분리 + 스팃스 하우스 스타일 상세페이지 HTML 생성."""
from __future__ import annotations

import html
from pathlib import Path

import numpy as np
from PIL import Image

from .catalog import CATEGORY_NOTICE, Product

PAGE_W = 860
SECTION_IDS = [
    ("sec-01", "01_상단타이틀"),
    ("sec-02", "02_대표이미지"),
    ("sec-03", "03_포인트안내"),
    ("sec-04", "04_WHY"),
    ("sec-05", "05_활용컷"),
    ("sec-06", "06_핵심기능_스펙"),
]

FONT_STACK = "'Malgun Gothic','Apple SD Gothic Neo','Noto Sans CJK KR','NanumGothic',sans-serif"


def _gutter(profile: np.ndarray, lo: int, hi: int, thr: float = 4.0):
    """lo~hi 구간에서 가장 긴 '거의 단색' 줄(칸 사이 여백) 구간을 반환. 없으면 None."""
    best, run_start = None, None
    for i in range(lo, hi + 1):
        flat = profile[i] < thr
        if flat and run_start is None:
            run_start = i
        if (not flat or i == hi) and run_start is not None:
            end = i if flat else i - 1
            if best is None or end - run_start > best[1] - best[0]:
                best = (run_start, end)
            run_start = None
    return best


def split_panels(img: Image.Image) -> list[Image.Image]:
    """2x2 콜라주를 좌상·우상·좌하·우하 4장으로 자른다(칸 사이 여백 자동 감지)."""
    img = img.convert("RGB")
    a = np.asarray(img).astype(float)
    h, w = a.shape[:2]
    col_std = a.std(axis=0).mean(axis=1)
    row_std = a.std(axis=1).mean(axis=1)
    gx = _gutter(col_std, int(w * 0.4), int(w * 0.6))
    gy = _gutter(row_std, int(h * 0.4), int(h * 0.6))
    mx = (gx[0] - 1, gx[1] + 2) if gx else (w // 2, w // 2)
    my = (gy[0] - 1, gy[1] + 2) if gy else (h // 2, h // 2)
    m = 6
    xs = [(m, mx[0] - m), (mx[1] + m, w - m)]
    ys = [(m, my[0] - m), (my[1] + m, h - m)]
    out = []
    for (y0, y1) in ys:
        for (x0, x1) in xs:
            out.append(img.crop((x0, y0, x1, y1)))
    return out


def cover_square(im: Image.Image, size: int) -> Image.Image:
    im = im.convert("RGB")
    w, h = im.size
    s = min(w, h)
    left, top = (w - s) // 2, (h - s) // 2
    return im.crop((left, top, left + s, top + s)).resize((size, size), Image.LANCZOS)


def prepare_images(prod: Product, collage: Path, hero: Path | None, img_dir: Path, slug: str) -> dict[str, str]:
    img_dir.mkdir(parents=True, exist_ok=True)
    panels = split_panels(Image.open(collage))
    names = {}

    def save(tag: str, im: Image.Image):
        fn = f"{slug}_{tag}.jpg"
        cover_square(im, 860).save(img_dir / fn, quality=92, optimize=True)
        names[tag] = f"../images/{fn}"

    if hero is not None:
        save("main", Image.open(hero))
    else:
        save("main", panels[0])
    save("why", panels[1] if hero is None else panels[0])
    save("use1", panels[2])
    save("use2", panels[3])
    return names


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:%(font)s;background:#fff;color:#2b2b2b;padding-bottom:120px;-webkit-font-smoothing:antialiased}
.wrap{width:%(w)dpx;max-width:100%%;margin:0 auto}
.capture-area{background:#fff}
.hero{padding:72px 40px 56px;text-align:center;background:#faf9f7}
.hero .eng{font-size:12px;letter-spacing:5px;color:#a89d8e;margin-bottom:16px;text-transform:uppercase}
.hero h1{font-size:34px;font-weight:700;letter-spacing:-1.5px;margin-bottom:18px;line-height:1.35}
.hero .lead{font-size:15px;line-height:1.75;color:#666;margin-bottom:32px}
.hero-benefits{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
.hero-benefits span{padding:10px 20px;background:#fff;border:1px solid #e8e4de;border-radius:40px;font-size:13px;color:#444;letter-spacing:-.3px}
.main-img{width:100%%}
.main-img img{width:100%%;display:block;aspect-ratio:1/1;object-fit:cover}
.points{padding:48px 40px;border-top:1px solid #eee;border-bottom:1px solid #eee}
.point-row{display:flex;align-items:flex-start;gap:28px;padding:24px 0;border-bottom:1px solid #f0f0f0}
.point-row:last-child{border-bottom:none}
.point-row .num{flex-shrink:0;width:56px;text-align:center;font-size:22px;font-weight:700;color:#d8cdb9;padding-top:2px}
.point-row .tit{font-size:16px;font-weight:700;margin-bottom:6px;letter-spacing:-.3px}
.point-row .txt{font-size:13px;color:#777;line-height:1.65}
.section{padding:68px 40px;border-bottom:1px solid #f5f5f5}
.section h2{font-size:22px;font-weight:700;text-align:center;margin-bottom:8px;letter-spacing:-.5px}
.section .sub{font-size:13px;color:#999;text-align:center;margin-bottom:36px;line-height:1.6}
.empathy-box{max-width:560px;margin:0 auto 36px;padding:28px 32px;background:#f8f7f5;border-radius:4px;font-size:14px;line-height:1.85;color:#555;text-align:center}
.empathy-box strong{color:#2b2b2b}
.section img.full{width:100%%;display:block;border-radius:4px;aspect-ratio:1/1;object-fit:cover}
.ba-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.ba-card{text-align:center}
.ba-card .label{font-size:11px;letter-spacing:3px;color:#c4a882;margin-bottom:12px}
.ba-card img{width:100%%;display:block;border-radius:4px;aspect-ratio:1/1;object-fit:cover;margin-bottom:14px}
.ba-card p{font-size:13px;color:#666;line-height:1.6}
.features{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.feat{padding:32px 24px;background:#faf9f7;border-radius:4px;text-align:center}
.feat-icon{width:48px;height:48px;margin:0 auto 18px;border-radius:50%%;background:#fff;border:1px solid #e8e4de;display:flex;align-items:center;justify-content:center;font-size:20px}
.feat h3{font-size:15px;font-weight:700;margin-bottom:10px;letter-spacing:-.3px}
.feat p{font-size:12px;color:#777;line-height:1.65}
.spec{margin-top:48px}
.spec h3{font-size:14px;letter-spacing:4px;text-align:center;color:#a89d8e;margin-bottom:18px}
.spec table{width:100%%;border-collapse:collapse;font-size:13px}
.spec th{width:120px;text-align:left;padding:14px 16px;background:#faf9f7;color:#555;font-weight:700;border-top:1px solid #eee;vertical-align:top}
.spec td{padding:14px 16px;color:#444;border-top:1px solid #eee;line-height:1.6}
.spec tr:last-child th,.spec tr:last-child td{border-bottom:1px solid #eee}
.notice{margin-top:40px;padding:26px 28px;background:#f8f7f5;border-radius:4px}
.notice h4{font-size:12px;letter-spacing:3px;color:#a89d8e;margin-bottom:12px}
.notice li{font-size:12px;color:#777;line-height:1.8;margin-left:16px}
.save-panel{position:fixed;bottom:20px;right:20px;background:rgba(30,30,30,.95);color:#fff;padding:16px;border-radius:8px;z-index:9999;display:flex;flex-direction:column;gap:6px;width:200px}
.save-panel h4{font-size:13px;margin-bottom:8px;color:#c4a882;text-align:center}
.save-panel button{background:#333;color:#eee;border:1px solid #555;padding:7px 10px;font-size:11px;border-radius:4px;cursor:pointer}
.save-panel button.all-btn{background:#c4a882;color:#111;font-weight:bold;border:none;margin-top:6px}
@media(max-width:859px){.hero,.points,.section{padding-left:20px;padding-right:20px}.hero h1{font-size:26px}.ba-grid,.features{grid-template-columns:1fr}}
""" % {"font": FONT_STACK, "w": PAGE_W}

ICONS = ["◇", "○", "□"]


def _plain(s: str) -> str:
    return s.replace("<br>", " ")


def render_html(prod: Product, imgs: dict[str, str], slug: str, with_tools: bool = True) -> str:
    e = html.escape
    title = _plain(prod.name)
    chips = "".join(f"<span>{e(c)}</span>" for c in prod.chips)
    points = "".join(
        f'<div class="point-row"><div class="num">{i:02d}</div><div>'
        f'<div class="tit">{e(t)}</div><div class="txt">{e(d)}</div></div></div>'
        for i, (t, d) in enumerate(prod.points, 1)
    )
    feats = "".join(
        f'<div class="feat"><div class="feat-icon">{ICONS[i % 3]}</div><h3>{e(t)}</h3><p>{d}</p></div>'
        for i, (t, d) in enumerate(prod.feats)
    )
    spec_rows = "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in prod.specs)
    notices = "".join(f"<li>{e(n)}</li>" for n in CATEGORY_NOTICE.get(prod.cat, CATEGORY_NOTICE["general"]))
    short = prod.name.split("<br>")[0]
    cap1 = cap2 = f"{short} 스타일링 컷"
    why_sub, why_body = prod.why

    tools = ""
    script = ""
    if with_tools:
        script = '<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>'
        btns = "".join(
            f"<button onclick=\"saveSection('{sid}','{slug}_{label}')\">{label.replace('_', '. ', 1)}</button>"
            for sid, label in SECTION_IDS
        )
        tools = f"""
<div class="save-panel"><h4>상세페이지 분할 저장</h4>{btns}
<button class="all-btn" onclick="saveAll()">전체 순서대로 저장</button></div>
<script>
async function saveSection(id,name){{
  const el=document.getElementById(id);
  const c=await html2canvas(el,{{scale:2,useCORS:true,backgroundColor:'#ffffff'}});
  const a=document.createElement('a');a.download=name+'.jpg';a.href=c.toDataURL('image/jpeg',0.92);a.click();
}}
async function saveAll(){{
  const ids={[sid for sid, _ in SECTION_IDS]!r};
  const names={[f"{slug}_{l}" for _, l in SECTION_IDS]!r};
  for(let i=0;i<ids.length;i++){{await saveSection(ids[i],names[i]);await new Promise(r=>setTimeout(r,400));}}
}}
</script>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} | STIX</title>
{script}
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<div id="sec-01" class="capture-area"><section class="hero">
<div class="eng">{e(prod.eng)}</div>
<h1>{prod.name}</h1>
<p class="lead">{prod.lead}</p>
<div class="hero-benefits">{chips}</div>
</section></div>

<div id="sec-02" class="capture-area"><div class="main-img"><img src="{imgs['main']}" alt="{e(title)}"></div></div>

<div id="sec-03" class="capture-area"><div class="points">{points}</div></div>

<div id="sec-04" class="capture-area"><section class="section">
<h2>WHY YOU NEED THIS</h2>
<div class="sub">{why_sub}</div>
<div class="empathy-box">{why_body}</div>
<img class="full" src="{imgs['why']}" alt="{e(title)} 사용 이미지">
</section></div>

<div id="sec-05" class="capture-area"><section class="section">
<h2>IN USE</h2>
<div class="sub">이렇게 활용해 보세요</div>
<div class="ba-grid">
<div class="ba-card"><div class="label">CUT 01</div><img src="{imgs['use1']}" alt="{e(cap1)}"><p>{e(cap1)}</p></div>
<div class="ba-card"><div class="label">CUT 02</div><img src="{imgs['use2']}" alt="{e(cap2)}"><p>{e(cap2)}</p></div>
</div>
</section></div>

<div id="sec-06" class="capture-area"><section class="section">
<h2>CORE FEATURES</h2>
<div class="sub">{e(title)}</div>
<div class="features">{feats}</div>
<div class="spec"><h3>PRODUCT INFO</h3><table>{spec_rows}</table></div>
<div class="notice"><h4>NOTICE</h4><ul>{notices}</ul></div>
</section></div>

</div>
{tools}
</body>
</html>
"""


def render_index(rows: list[dict]) -> str:
    e = html.escape
    cards = "".join(
        f'<a class="card" href="pages/{e(r["slug"])}.html"><img src="long_thumb/{e(r["slug"])}.jpg" loading="lazy">'
        f'<div class="t">{e(_plain(r["name"]))}</div><div class="k">{e(r["slug"])}'
        + ('<span class="qa">확인 필요</span>' if r["qa"] else "")
        + "</div></a>"
        for r in rows
    )
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><title>STIX 상세페이지 인덱스</title>
<style>body{{font-family:{FONT_STACK};background:#faf9f7;color:#2b2b2b;margin:0;padding:40px}}
h1{{font-size:24px;margin-bottom:6px}}p{{color:#777;font-size:13px;margin-bottom:28px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:18px}}
.card{{background:#fff;border:1px solid #eee;border-radius:6px;padding:10px;text-decoration:none;color:inherit}}
.card img{{width:100%;aspect-ratio:3/4;object-fit:cover;object-position:top;border-radius:4px;background:#f2f0ec}}
.t{{font-size:13px;font-weight:700;margin-top:8px;line-height:1.4}}.k{{font-size:11px;color:#aaa;margin-top:4px}}
.qa{{background:#c4543c;color:#fff;border-radius:10px;padding:1px 8px;margin-left:6px}}</style></head>
<body><h1>STIX 상세페이지 {len(rows)}종</h1><p>제작_산출물 콜라주 이미지 기반 · 6섹션 하우스 스타일</p><div class="grid">{cards}</div></body></html>"""
