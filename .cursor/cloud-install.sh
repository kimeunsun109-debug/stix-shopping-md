#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[cloud-install] Python deps..."
pip3 install --break-system-packages -q -r requirements.txt

echo "[cloud-install] Verify imports..."
python3 - <<'PY'
import pandas, openpyxl, xlrd, fastapi, uvicorn, httpx
print("OK: pandas", pandas.__version__, "| fastapi", fastapi.__version__)
PY

# Playwright browser binary is only used by local CDP scraping (Chrome 9233),
# per AGENTS.md rule #3. Cloud web/analysis/report flows never need it, so it is
# skipped by default to keep boot fast. Opt in by exporting
# PLAYWRIGHT_INSTALL_BROWSERS=1 before install if you need headless Chromium.
if [ "${PLAYWRIGHT_INSTALL_BROWSERS:-0}" = "1" ]; then
  echo "[cloud-install] Playwright chromium (opt-in)..."
  python3 -m playwright install --with-deps chromium
else
  echo "[cloud-install] Skipping Playwright chromium (local CDP only; set PLAYWRIGHT_INSTALL_BROWSERS=1 to enable)."
fi

echo "[cloud-install] Done."
