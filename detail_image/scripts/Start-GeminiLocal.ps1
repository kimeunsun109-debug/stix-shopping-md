# 로컬 Chrome 창 + Gemini + P0/P1 자동 생성 (Windows)
# 더블클릭 또는: powershell -ExecutionPolicy Bypass -File detail_image\scripts\Start-GeminiLocal.ps1

$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Daesijejak = "$env:USERPROFILE\OneDrive\Desktop\상세페이지사진\짧은_구식_상세페이지\제작_산출물\다시제작"

$chromeCandidates = @(
  "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$chrome = $chromeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $chrome) { throw "Chrome을 찾을 수 없습니다." }

$userData = "$env:LOCALAPPDATA\STIX-Gemini-CDP"
New-Item -ItemType Directory -Force -Path $userData | Out-Null

Write-Host "Chrome 창을 엽니다 (CDP 9222). Gemini 로그인이 필요하면 창에서 로그인하세요."
Start-Process -FilePath $chrome -ArgumentList @(
  "--remote-debugging-port=9222",
  "--user-data-dir=$userData",
  "https://gemini.google.com/app",
  "https://www.google.com/search?udm=50"
)

if (Test-Path $Daesijejak) {
  Start-Process explorer.exe $Daesijejak
}

Write-Host "15초 대기 (로그인·탭 로딩)..."
Start-Sleep -Seconds 15

& (Join-Path $PSScriptRoot "Run-P0Regen.ps1")
