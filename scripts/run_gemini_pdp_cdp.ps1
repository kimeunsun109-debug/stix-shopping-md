# pickmetalk-pc: Chrome 9222 CDP + Gemini 로그인 후 4분할 배치 (별마크 우선)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "CDP probe http://127.0.0.1:9222 ..."
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version" -TimeoutSec 3 | Out-Null
} catch {
    Write-Host @"
Chrome CDP(9222)에 연결되지 않습니다.
Chrome을 remote-debugging으로 실행한 뒤 다시 시도하세요.
예: chrome.exe --remote-debugging-port=9222
Gemini(gemini.google.com) 탭에서 로그인 완료 상태여야 합니다.
"@
    exit 1
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "python이 PATH에 없습니다."
    exit 1
}

python -m pip install -q playwright 2>$null
python scripts/gemini_pdp_4split_batch.py --login-check
if ($LASTEXITCODE -ne 0) {
    Write-Host "Gemini 로그인 확인 실패 — CDP Chrome / Gemini 탭 확인"
    exit $LASTEXITCODE
}

$limit = if ($env:GEMINI_PDP_LIMIT) { $env:GEMINI_PDP_LIMIT } else { "1" }
python scripts/gemini_pdp_4split_batch.py --manifest scripts/gemini_pdp_manifest_win.csv --limit $limit
exit $LASTEXITCODE
