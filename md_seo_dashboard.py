# -*- coding: utf-8 -*-
"""STIX AI SEO Dashboard CLI."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    from seo_engine.engines.dashboard import Dashboard

    text = Dashboard().format_text()
    print(text)
    out = ROOT / "SEO_DASHBOARD.txt"
    out.write_text(text, encoding="utf-8")
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
