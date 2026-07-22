@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo STIX B7000 Item Winner Monitor (30min, continuous)
python md_item_winner_monitor.py
