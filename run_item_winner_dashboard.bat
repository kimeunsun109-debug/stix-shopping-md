@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo STIX Item Winner Dashboard + External Tunnel + Alerts
python md_item_winner_dashboard.py --tunnel
pause
