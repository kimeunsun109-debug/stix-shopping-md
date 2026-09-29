#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "[cloud-install] Python deps..."
pip3 install --break-system-packages -r requirements.txt
echo "[cloud-install] Verify imports..."
python3 -c "import pandas, openpyxl, xlrd, fastapi, uvicorn, httpx; print('OK:', pandas.__version__, fastapi.__version__)"
