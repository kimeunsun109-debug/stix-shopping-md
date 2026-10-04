# STIX 다시제작 P0/P1 Gemini 4분할 (Windows + Chrome CDP 9222)
# 사용: PowerShell -ExecutionPolicy Bypass -File detail_image\scripts\Run-P0Regen.ps1

$ErrorActionPreference = "Stop"
$Root = "$env:USERPROFILE\OneDrive\Desktop\상세페이지사진\짧은_구식_상세페이지\제작_산출물\다시제작"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$NodeScript = Join-Path $Repo "detail_image\scripts\gemini_4split_cdp.mjs"
$SplitPy = Join-Path $Repo "detail_image\split_composite.py"

$tabs = Invoke-RestMethod "http://127.0.0.1:9222/json"
$page = $tabs | Where-Object {
  $_.type -eq "page" -and (
    ($_.url -like "*gemini.google.com*") -or ($_.url -like "*google.com/search*udm=50*")
  )
} | Select-Object -First 1
if (-not $page) {
  $page = $tabs | Where-Object { $_.type -eq "page" } | Select-Object -First 1
}
if (-not $page) { throw "Chrome CDP 9222 에 page 탭이 없습니다. Start-GeminiLocal.ps1 로 Chrome을 먼저 실행하세요." }
$ws = $page.webSocketDebuggerUrl
Write-Host "CDP tab: $($page.url)"

$priorityFile = Join-Path $Repo "detail_image\MD_다시제작_재생성_우선순위.txt"
$lines = Get-Content $priorityFile -Encoding UTF8 | Where-Object { $_ -match '^P\d' }

foreach ($line in $lines) {
  $name = ($line -split '\|', 3)[1].Trim()
  $dir = Join-Path $Root $name
  if (-not (Test-Path $dir)) { Write-Warning "skip missing $dir"; continue }

  $thumb = @(
    (Join-Path $dir "썸네일.jpg"),
    (Join-Path $dir "thumb.jpg")
  ) | Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $thumb) { Write-Warning "skip no thumb $name"; continue }

  $composite = Join-Path $dir "상세페이지_4분할_합성.jpg"
  $splitDir = Join-Path $dir "4분할"
  New-Item -ItemType Directory -Force -Path $splitDir | Out-Null

  Write-Host "==> $name"
  node $NodeScript $ws $thumb $composite
  if ($LASTEXITCODE -ne 0) { Write-Warning "gemini failed $name"; continue }
  python $SplitPy $composite -o $splitDir
}

Write-Host "Done."
