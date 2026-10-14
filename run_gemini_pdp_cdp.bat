@echo off
setlocal
cd /d "%~dp0"

set "_PY=python"
where python >nul 2>&1
if errorlevel 1 set "_PY=py -3"

%_PY% scripts\gemini_pdp_4split_batch.py --login-check
if errorlevel 1 (
  echo Login check failed. Use Chrome with remote-debugging-port=9222 and Gemini signed in.
  exit /b 1
)

if "%GEMINI_PDP_LIMIT%"=="" set GEMINI_PDP_LIMIT=1
%_PY% scripts\gemini_pdp_4split_batch.py --manifest scripts\gemini_pdp_manifest_win.csv --limit %GEMINI_PDP_LIMIT%
pause
