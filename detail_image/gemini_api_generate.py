# -*- coding: utf-8 -*-
"""
Gemini API로 4분할 합성 이미지 생성 (로컬/Cloud — GOOGLE_API_KEY 또는 구글 api 시크릿).

Usage:
  export GOOGLE_API_KEY=...
  python3 detail_image/gemini_api_generate.py 썸네일.jpg -o 합성.jpg
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    from detail_image.prompts import GEMINI_4SPLIT_PROMPT_FULL
except ImportError:
    from prompts import GEMINI_4SPLIT_PROMPT_FULL  # type: ignore

MODEL = "gemini-2.0-flash-preview-image-generation"


def _api_key() -> str:
    for name in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "구글 api"):
        v = os.environ.get(name)
        if v:
            return v.strip()
    raise SystemExit(
        "GOOGLE_API_KEY (또는 Cloud Agent 시크릿 '구글 api')가 없습니다. "
        "Cursor Cloud → Secrets에 키를 넣고 Agent를 다시 실행하세요."
    )


def generate(thumb_path: Path) -> bytes:
    key = _api_key()
    img_b64 = base64.standard_b64encode(thumb_path.read_bytes()).decode("ascii")
    body = {
        "contents": [
            {
                "parts": [
                    {"text": GEMINI_4SPLIT_PROMPT_FULL},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_b64,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
        f"?key={key}"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:800]
        raise SystemExit(f"Gemini API HTTP {e.code}: {err}") from e

    for cand in data.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.standard_b64decode(inline["data"])
    raise SystemExit("응답에 이미지가 없습니다. 모델/쿼터/프롬프트를 확인하세요.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("thumbnail", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    args = ap.parse_args()
    out_bytes = generate(args.thumbnail)
    args.out.write_bytes(out_bytes)
    print(f"wrote {args.out} ({len(out_bytes)} bytes)")


if __name__ == "__main__":
    main()
