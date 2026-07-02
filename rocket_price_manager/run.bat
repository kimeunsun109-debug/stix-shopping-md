@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".env" (
  echo [ERROR] .env 파일이 없습니다.
  echo         .env.example 을 복사해 .env 를 만드세요.
  pause
  exit /b 1
)

python --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python 이 PATH 에 없습니다. Python 3.12 설치 후 다시 실행하세요.
  pause
  exit /b 1
)

pip install -r requirements.txt -q
python main.py
pause
