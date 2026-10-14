@echo off
REM pickmetalk-pc: Chrome 9222 CDP + Gemini 로그인 후 실행
cd /d "%~dp0"
python scripts\gemini_pdp_4split_batch.py --login-check
if errorlevel 1 (
  echo Gemini 로그인 확인 실패 — Chrome 9222 CDP 확인
  exit /b 1
)
if "%GEMINI_PDP_LIMIT%"=="" set GEMINI_PDP_LIMIT=1
python scripts\gemini_pdp_4split_batch.py --manifest scripts\gemini_pdp_manifest_win.csv --limit %GEMINI_PDP_LIMIT%
pause
