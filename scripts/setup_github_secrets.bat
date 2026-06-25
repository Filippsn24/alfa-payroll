@echo off
chcp 65001 >nul
echo === Настройка секретов GitHub Actions ===
echo.

set GH="C:\Program Files\GitHub CLI\gh.exe"
if not exist %GH% (
  echo GitHub CLI не найден. Установите: winget install GitHub.cli
  pause
  exit /b 1
)

%GH% auth status >nul 2>&1
if errorlevel 1 (
  echo Сначала войдите в GitHub:
  %GH% auth login
  echo.
)

set /p EMAIL=ALFACRM email: 
set /p APIKEY=ALFACRM API key: 

%GH% secret set ALFACRM_EMAIL --repo Filippsn24/alfa-payroll --body "%EMAIL%"
%GH% secret set ALFACRM_API_KEY --repo Filippsn24/alfa-payroll --body "%APIKEY%"
%GH% secret set ALFACRM_BASE_URL --repo Filippsn24/alfa-payroll --body "https://meteor.s20.online"
%GH% secret set ALFACRM_BRANCH_ID --repo Filippsn24/alfa-payroll --body "1"

echo.
echo Готово! Откройте Actions и запустите Calculate Payroll.
pause
