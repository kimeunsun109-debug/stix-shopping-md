# -*- coding: utf-8 -*-
"""30ml 구조 기반 상세페이지 HTML 생성."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent

COMMON_STYLE = """
    :root { --ink:#141414; --mute:#5a5a5a; --paper:#f7f7f8; --line:rgba(20,20,20,.1); --red:#d71920; --max:860px; }
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:"Noto Sans KR",system-ui,sans-serif;color:var(--ink);background:#fff;line-height:1.6}
    .detail-wrap{max-width:var(--max);margin:0 auto}
    .capture-area{overflow:hidden}
    .section-title{font-family:Outfit,"Noto Sans KR",sans-serif;font-size:.78rem;letter-spacing:.18em;text-transform:uppercase;color:var(--red);font-weight:700;margin-bottom:10px}
    .hero{background:#ececee;padding:44px 28px 0;text-align:center}
    .hero .badge{display:inline-block;font-size:.72rem;font-weight:800;letter-spacing:.22em;color:var(--red);border:2px solid var(--red);padding:5px 14px;margin-bottom:18px}
    .hero h1{font-size:clamp(1.5rem,5vw,2rem);font-weight:800;letter-spacing:-.02em;line-height:1.25;margin-bottom:10px}
    .hero .sub{color:var(--mute);font-size:.98rem;margin-bottom:24px;line-height:1.65}
    .hero-image-box{margin:0 -28px;background:#ececee;overflow:hidden;line-height:0}
    .hero-image-box img{width:100%;height:auto;display:block}
    .panel{padding:44px 28px;border-bottom:1px solid var(--line)}
    .panel h2{font-size:clamp(1.2rem,3.5vw,1.55rem);font-weight:800;letter-spacing:-.02em;margin-bottom:14px}
    .panel .lead{color:var(--mute);margin-bottom:22px}
    .size-card{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;text-align:center}
    .size-card div{padding:18px 10px;border:1px solid var(--line);border-radius:4px}
    .size-card .active{border-color:var(--red);background:rgba(215,25,32,.04)}
    .size-card strong{display:block;font-family:Outfit,sans-serif;font-size:1.2rem;margin-bottom:4px}
    .size-card span{font-size:.82rem;color:var(--mute);font-weight:600}
    .media{width:100%;display:block;border-radius:4px;background:var(--paper);margin-bottom:14px}
    .use-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
    .use-grid img{width:100%;display:block;border-radius:4px}
    .use-caption{margin-top:14px;font-size:.9rem;color:var(--mute);font-weight:600;text-align:center}
    .recommend-list{list-style:none;display:grid;gap:12px;margin-bottom:22px}
    .recommend-list li{padding:12px 14px;background:var(--paper);border-radius:4px;font-weight:600;font-size:.95rem;line-height:1.5}
    .callout{background:linear-gradient(135deg,#fff5f5 0%,#f7f7f8 100%);border-left:4px solid var(--red);padding:20px 18px;border-radius:4px}
    .callout p{margin-bottom:10px;font-weight:600;line-height:1.65}
    .callout p:last-child{margin-bottom:0}
    .callout strong{color:var(--red)}
    .safety-note{margin-top:18px;padding:16px 18px;background:var(--paper);border-radius:4px;font-size:1.05rem;font-weight:700;color:var(--ink);text-align:center}
    .faq-item{padding:16px 0;border-bottom:1px solid var(--line)}
    .faq-item:last-child{border-bottom:0}
    .faq-item h3{font-size:1rem;font-weight:700;margin-bottom:8px}
    .faq-item p{color:var(--mute);font-size:.95rem;line-height:1.65}
    .points{list-style:none;display:grid;gap:12px}
    .points li{display:grid;grid-template-columns:2rem 1fr;gap:10px;padding:14px 0;border-bottom:1px solid var(--line);font-weight:600}
    .points li span{font-family:Outfit,sans-serif;font-weight:800;color:var(--red)}
    .spec-grid{display:grid;grid-template-columns:110px 1fr;border-top:1px solid var(--line);font-size:.95rem}
    .spec-grid div{padding:12px 0;border-bottom:1px solid var(--line)}
    .spec-grid dt{font-weight:700;color:var(--mute)}
    .spec-grid dd{font-weight:600}
    .closing{background:linear-gradient(160deg,#1a1a1a 0%,#2a2a2a 100%);color:#fff;text-align:center}
    .closing h2{color:#fff;margin-bottom:10px}
    .closing p{color:rgba(255,255,255,.75)}
    .brand-foot{margin-top:20px;font-family:Outfit,sans-serif;font-weight:800;letter-spacing:.2em;font-size:.85rem;color:var(--red)}
"""

SUB_COPY = (
    "DIY 리폼부터 전문가의 산업용 작업까지 이거 하나면 끝!<br>"
    "나무, 금속, 유리, 플라스틱, 가죽, 패브릭까지 재질을 가리지 않고 완벽하게 결합합니다."
)
RECOMMEND = """
      <li>💎 큐빅, 비즈, 파츠 등 정교한 공예/액세서리 작가님</li>
      <li>👟 뜯어진 운동화 밑창, 구두 굽을 셀프로 고치고 싶은 분</li>
      <li>🪵 가구 가공, 타일 보수 등 셀프 인테리어 DIY족</li>
      <li>🚗 진동이 많은 차량 내부 용품을 단단히 고정하고 싶은 운전자</li>"""


def render_page(cfg: dict) -> str:
    use_imgs = "\n".join(
        f'      <img src="{cfg["img_prefix"]}{n}" alt="{cfg["brand"]} 활용" />'
        for n in cfg["use_images"]
    )
    faq = "\n".join(
        f"""      <div class="faq-item">
        <h3>{q}</h3>
        <p>{a}</p>
      </div>"""
        for q, a in cfg["faq"]
    )
    points = "\n".join(
        f'      <li><span>{i:02d}</span>{t}</li>' for i, t in enumerate(cfg["why_points"], 1)
    )
    specs = "\n".join(f"      <dt>{k}</dt><dd>{v}</dd>" for k, v in cfg["specs"])

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>스팃스 · {cfg['title']}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@600;700;800&family=Noto+Sans+KR:wght@400;500;700;800&display=swap" rel="stylesheet" />
  <style>{COMMON_STYLE}</style>
</head>
<body>
<div class="detail-wrap">

  <section class="capture-area hero" id="sec-01">
    <div class="badge">{cfg['badge']}</div>
    <h1>{cfg['h1']}</h1>
    <p class="sub">{SUB_COPY}</p>
    <div class="hero-image-box">
      <img src="{cfg['hero_image']}" alt="{cfg['hero_alt']}" />
    </div>
  </section>

  <section class="capture-area panel" id="sec-02">
    <p class="section-title">Size Guide</p>
    <h2>{cfg['size_h2']}</h2>
    <p class="lead">{cfg['size_lead']}</p>
    <div class="size-card">
      <div class="active"><strong>{cfg['size_active']}</strong><span>✔️만능접착제</span></div>
      <div><strong>내구성</strong><span>✔️다양한 재질에 사용</span></div>
      <div><strong>색상</strong><span>✔️깔끔한 마감</span></div>
    </div>
  </section>

  <section class="capture-area panel" id="sec-03">
    <p class="section-title">Product Shot</p>
    <h2>제품 사진</h2>
    <img class="media" src="{cfg['product_image']}" alt="{cfg['brand']} 제품 사진" />
  </section>

  <section class="capture-area panel" id="sec-04">
    <p class="section-title">Cap Guide</p>
    <h2>사용 후 캡을 꼭 끼워 주세요</h2>
    <p class="lead">{cfg['cap_lead']}</p>
    <img class="media" src="{cfg['cap_image']}" alt="{cfg['brand']} 캡 보관" />
    <p class="use-caption">{cfg['cap_caption']}</p>
  </section>

  <section class="capture-area panel" id="sec-05">
    <p class="section-title">Use Case</p>
    <h2>실생활 활용</h2>
    <p class="lead">이런 분들께 강력 추천합니다!</p>
    <ul class="recommend-list">{RECOMMEND}
    </ul>
    <div class="use-grid">
{use_imgs}
    </div>
    <p class="use-caption">도자기 · 신발 · 핸드메이드 · DIY</p>
  </section>

  <section class="capture-area panel" id="sec-06">
    <p class="section-title">Curing Time</p>
    <h2>경화 시간 안내</h2>
    <div class="callout">
      <p>{cfg['brand']}은 초기 고정 후 완전히 굳기까지 <strong>24~72시간</strong>이 걸립니다.</p>
      <p>초기 접착 후 하루 동안 단단히 고정해 주시면 평생 가는 접착력을 경험할 수 있습니다.</p>
    </div>
  </section>

  <section class="capture-area panel" id="sec-07">
    <p class="section-title">{cfg['why_title']}</p>
    <h2>{cfg['why_h2']}</h2>
    <ul class="points">
{points}
    </ul>
  </section>

  <section class="capture-area panel" id="sec-08">
    <p class="section-title">Specification</p>
    <h2>제품 사양</h2>
    <dl class="spec-grid">
{specs}
    </dl>
    <p class="safety-note">생활화학제품 안전관리신고번호 — 제 FB25-11-0011호</p>
  </section>

  <section class="capture-area panel" id="sec-09">
    <p class="section-title">FAQ</p>
    <h2>자주 묻는 질문</h2>
    <div class="faq">
{faq}
    </div>
  </section>

  <section class="capture-area panel closing" id="sec-10">
    <h2>STIX · {cfg['closing']}</h2>
    <p>{cfg['closing_sub']}</p>
    <p class="brand-foot">STIX</p>
  </section>

</div>
</body>
</html>
"""


PRODUCTS = [
    {
        "out": ROOT / "detail_pages/e6000/E6000_110ml_상세페이지.html",
        "title": "E6000 110ml 다용도 접착제",
        "badge": "BEST SIZE · 110ML",
        "h1": "E6000 다용도 접착제<br>110ml 대용량",
        "hero_image": "images/e6000-110ml-front-box.jpg",
        "hero_alt": "E6000 110ml 대용량 제품사진",
        "size_h2": "넉넉한 작업량에는<br>110ml가 정답입니다",
        "size_lead": "110ml / 3.7 fl.oz. · 대용량·반복 작업용",
        "size_active": "110ml",
        "product_image": "images/e6000-110ml-angle.jpg",
        "cap_lead": (
            "E6000은 사용이 끝나면 <strong>흰색 캡을 노즐에 단단히 끼워</strong> 보관해야 합니다.<br>"
            "캡을 제대로 닫아 두면 접착제가 마르면서 노즐이 막히는 것을 막고, 다음에도 깔끔하게 짜낼 수 있습니다."
        ),
        "cap_image": "images/e6000-110ml-nozzle.jpg",
        "cap_caption": "노즐에 캡을 끼운 상태로 보관 · 개봉 후 뚜껑 필수",
        "img_prefix": "images/e6000-110ml-use-0",
        "use_images": ["1.jpg", "2.jpg", "3.jpg", "4.jpg"],
        "brand": "E6000",
        "why_title": "Why 110ml",
        "why_h2": "대용량이 유리한 이유",
        "why_points": [
            "여러 번·넓은 면적 작업에 한 통으로 충분",
            "30ml 대비 가성비 좋은 스테디셀러 용량",
            "보석십자수·수리·DIY 반복 작업에 적합",
            "30ml와 동일한 Clear · Self-Leveling 성능",
        ],
        "specs": [
            ("제품명", "E6000 Industrial Strength Adhesive"),
            ("용량", "110ml / 3.7 fl.oz."),
            ("색상", "Clear (투명)"),
            ("점도", "Medium Viscosity"),
            ("특징", "Waterproof · Flexible · Paintable · Non-flammable"),
            ("권장 용도", "비즈·큐빅 고정, 파츠 접착, 신발·가구 수리, DIY"),
        ],
        "faq": [
            ("30ml과 110ml 중 어떤 걸 사야 하나요?", "처음 써보거나 소량·디테일 작업이면 30ml, 여러 번·넓은 면적 작업이면 110ml이 경제적입니다."),
            ("B7000과 차이가 있나요?", "E6000은 산업용 다용도 접착제로 접착력·내구성이 더 강한 편입니다."),
            ("순간접착제 대신 쓰는 이유는?", "굳기 전 위치 조정이 가능하고, 건조 후 탄성이 있어 충격에 강합니다."),
        ],
        "closing": "E6000 110ml",
        "closing_sub": "다용도 접착제 대용량 · 공예·수리 필수",
    },
    {
        "out": ROOT / "detail_pages/e6000/USA_E6000_110ml_상세페이지.html",
        "title": "USA E6000 110ml 정품 다용도 접착제",
        "badge": "USA OFFICIAL · 110ML",
        "h1": "USA E6000<br>정품 다용도 접착제 110ml",
        "hero_image": "images/usa-e6000-front-box.jpg",
        "hero_alt": "USA E6000 110ml 정품 제품사진",
        "size_h2": "미국 정품 USA E6000,<br>110ml 대용량",
        "size_lead": "110ml / 3.7 fl.oz. · HIGH TRANSPARENCY · 정품",
        "size_active": "USA",
        "product_image": "images/usa-e6000-angle.jpg",
        "cap_lead": (
            "USA E6000은 사용이 끝나면 <strong>흰색 캡을 메탈 노즐에 단단히 끼워</strong> 보관해야 합니다.<br>"
            "캡 안 핀이 노즐을 막아 건조·막힘을 방지하고, 다음에도 정밀하게 짜낼 수 있습니다."
        ),
        "cap_image": "images/usa-e6000-cap-detail.jpg",
        "cap_caption": "메탈 노즐 + 핀 캡 보관 · 개봉 후 뚜껑 필수",
        "img_prefix": "images/usa-e6000-use-0",
        "use_images": ["1.jpg", "2.jpg", "3.jpg", "4.jpg"],
        "brand": "USA E6000",
        "why_title": "Why USA",
        "why_h2": "USA 정품이 유리한 이유",
        "why_points": [
            "HIGH TRANSPARENCY — 투명 마감이 뛰어남",
            "미국 Eclectic Products 정품 USA 마킹",
            "정밀 메탈 노즐 + 핀 캡으로 막힘 방지",
            "110ml 대용량 — DIY·수리·공예 작업에 충분",
        ],
        "specs": [
            ("브랜드", "USA E6000 (정품)"),
            ("용량", "110ml / 3.7 fl.oz."),
            ("색상", "Clear · Medium Viscosity"),
            ("특징", "Waterproof · Flexible · Paintable · High Transparency"),
            ("권장 용도", "보석십자수, 핸드메이드, 가죽·플라스틱·금속 접합, 소품 수리"),
        ],
        "faq": [
            ("USA E6000과 일반 E6000 차이가 있나요?", "USA E6000은 미국 정품 라인으로 공식 USA 마킹과 HIGH TRANSPARENCY 표기가 확인됩니다."),
            ("보석십자수에 써도 되나요?", "네. 투명하게 굳고 탄성이 있어 큐빅·비즈 고정, 캔버스 마감에 많이 사용됩니다."),
            ("냄새가 강한데 안전한가요?", "휘발성 성분이 있어 환기가 잘 되는 곳에서 사용하세요."),
        ],
        "closing": "USA E6000 110ml",
        "closing_sub": "정품 다용도 접착제 · 공예·수리·DIY 필수템",
    },
    {
        "out": ROOT / "detail_pages/b6000/B6000_15ml_상세페이지.html",
        "title": "B6000 15ml 소용량 다용도 접착제",
        "badge": "DETAIL SIZE · 15ML",
        "h1": "B6000 다용도 접착제<br>15ml 소용량",
        "hero_image": "images/b6000-15ml-front-box.jpg",
        "hero_alt": "B6000 15ml 소용량 제품사진",
        "size_h2": "좁은 틈새·정밀 작업엔<br>15ml가 딱 맞습니다",
        "size_lead": "15ml / 0.5 fl.oz. · 디테일·테스트·소량 작업용",
        "size_active": "15ml",
        "product_image": "images/b6000-15ml-angle.jpg",
        "cap_lead": (
            "B6000은 사용이 끝나면 <strong>핀 캡을 메탈 노즐에 단단히 끼워</strong> 보관해야 합니다.<br>"
            "캡 안 핀이 노즐 구멍을 막아 말라 붙는 것을 방지하고, 다음에도 0.8mm 초정밀 도포가 가능합니다."
        ),
        "cap_image": "images/b6000-15ml-cap-detail.jpg",
        "cap_caption": "0.8mm 초정밀 노즐 · 막힘 방지 핀 캡 필수",
        "img_prefix": "images/b6000-15ml-use-0",
        "use_images": ["1.jpg", "2.jpg", "3.jpg", "4.jpg"],
        "brand": "B6000",
        "why_title": "Why 15ml",
        "why_h2": "소용량이 유리한 이유",
        "why_points": [
            "0.8mm 초정밀 메탈 노즐 — 큐빅·비즈·파츠 작업",
            "핸드폰·액세서리 소형 수리에 최적",
            "한 번에 조금만 쓰는 작업 — 남은 양 부담 없음",
            "투명 젤 타입 — 건조 후 깔끔한 마감",
        ],
        "specs": [
            ("제품명", "B6000 Multi-purpose Adhesive"),
            ("용량", "15ml / 0.5 fl.oz."),
            ("색상", "Clear (투명)"),
            ("노즐", "0.8mm 초정밀 메탈 노즐 (침핀형)"),
            ("특징", "Waterproof · Flexible · Anti-vibration"),
            ("권장 용도", "큐빅·비즈 고정, 핸드폰 수리, 파츠 접착, 소형 DIY"),
        ],
        "faq": [
            ("B6000과 B7000 차이가 있나요?", "B6000은 0.8mm 초정밀 메탈 노즐이 특징인 소용량 정밀 접착제입니다. B7000은 공예·수리용으로 더 널리 쓰입니다."),
            ("한 번 열면 얼마나 쓸 수 있나요?", "큐빅·파츠 소량 접착 기준으로 수십 회 사용 가능합니다. 사용 후 핀 캡을 꼭 닫아 보관하세요."),
            ("어린이 공예용으로 괜찮나요?", "휘발성 성분이 있어 환기가 필요합니다. 보호자 동반·환기된 공간에서 사용해 주세요."),
        ],
        "closing": "B6000 15ml",
        "closing_sub": "소용량 정밀 접착제 · 큐빅·수리·DIY 최적",
    },
]


def main() -> None:
    for cfg in PRODUCTS:
        cfg["out"].parent.mkdir(parents=True, exist_ok=True)
        cfg["out"].write_text(render_page(cfg), encoding="utf-8")
        print(cfg["out"])


if __name__ == "__main__":
    main()
