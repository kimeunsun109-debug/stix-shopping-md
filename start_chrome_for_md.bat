@echo off
chcp 65001 >nul
set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
set "USERDATA=%LOCALAPPDATA%\Google\Chrome\User Data"
set PORT=9233

echo STIX MD Chrome debug port %PORT%
start "" "%CHROME%" --remote-debugging-port=%PORT% --user-data-dir="%USERDATA%" --profile-directory=Default https://wing.coupang.com/
