@echo off
REM 스마트스토어 태그 1→2→3 순서 실행 (로컬 CDP Chrome 9233 필요)
cd /d "%~dp0"
call start_chrome_for_md.bat
timeout /t 5 /nobreak >nul
python md_smartstore_tags_run_123.py
pause
