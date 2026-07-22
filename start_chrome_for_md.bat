@echo off
chcp 65001 >nul
set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
set "USERDATA=%LOCALAPPDATA%\Google\Chrome\STIX_MD_CDP"
set PORT=9233

echo STIX MD Chrome CDP port %PORT% profile STIX_MD_CDP
echo Close all Chrome first, then run this bat. Login Wing + Coupang once.
start "" "%CHROME%" --remote-debugging-port=%PORT% --remote-debugging-address=127.0.0.1 --remote-allow-origins=* --user-data-dir="%USERDATA%" --profile-directory=Default https://wing.coupang.com/ https://www.coupang.com/
