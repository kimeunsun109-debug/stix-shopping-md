@echo off
setlocal
cd /d "%~dp0"

set "_PY=python"
where python >nul 2>&1
if errorlevel 1 set "_PY=py -3"

set "ROOT=%USERPROFILE%\OneDrive\Desktop\상세페이지사진\짧은_구식_상세페이지\다시제작"
set "MANIFEST=scripts\gemini_pdp_manifest_dasijejak_win.csv"

if not exist "%MANIFEST%" (
  %_PY% scripts\build_gemini_pdp_manifest.py --root "%ROOT%" --out "%MANIFEST%"
  if errorlevel 1 exit /b 1
) else (
  echo Using manifest: %MANIFEST%
)

%_PY% scripts\gemini_pdp_4split_batch.py --login-check
if errorlevel 1 (
  echo Login check failed. Chrome CDP 9222 + Gemini login required.
  exit /b 1
)

if "%GEMINI_PDP_LIMIT%"=="" set GEMINI_PDP_LIMIT=1
%_PY% scripts\gemini_pdp_4split_batch.py --manifest %MANIFEST% --limit %GEMINI_PDP_LIMIT%
pause
