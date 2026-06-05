@echo off
setlocal

set "PORT=8787"
set "BRIDGE_URL=http://127.0.0.1:%PORT%"

set "PROJECT_DIR="
for /d %%I in ("F:\cc\13khoj*") do (
  if exist "%%~fI\scripts\feishu_bridge.py" set "PROJECT_DIR=%%~fI"
)

if not defined PROJECT_DIR (
  echo Could not find project directory under F:\cc\13khoj*
  pause
  exit /b 1
)

set "LOG_DIR=%PROJECT_DIR%\.tmp_tests"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo Project: %PROJECT_DIR%
echo Starting Xiaochai bridge...
start "Xiaochai bridge - keep open" cmd /k "cd /d ""%PROJECT_DIR%"" && python scripts\feishu_bridge.py --port %PORT% --mode auto --ask-prefix ? 1>>""%LOG_DIR%\feishu_bridge.out.log"" 2>>""%LOG_DIR%\feishu_bridge.err.log"""

echo Waiting for bridge health check...
set "BRIDGE_OK="
for /l %%i in (1,1,12) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-RestMethod -Uri '%BRIDGE_URL%/health' -TimeoutSec 2; if ($r.ok) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
  if not errorlevel 1 (
    set "BRIDGE_OK=1"
    goto bridge_ready
  )
  timeout /t 1 /nobreak >nul
)

:bridge_ready
if not defined BRIDGE_OK (
  echo.
  echo Bridge failed to start.
  echo Check logs:
  echo %LOG_DIR%\feishu_bridge.err.log
  echo %LOG_DIR%\feishu_bridge.out.log
  echo.
  pause
  exit /b 1
)
echo Bridge is running: %BRIDGE_URL%/health

echo Looking for cloudflared...
set "CLOUDFLARED="
where cloudflared >nul 2>nul
if not errorlevel 1 set "CLOUDFLARED=cloudflared"
if not defined CLOUDFLARED if exist "F:\ruanjian\cloudflared.exe" set "CLOUDFLARED=F:\ruanjian\cloudflared.exe"
if not defined CLOUDFLARED if exist "%LOCALAPPDATA%\cloudflared\cloudflared.exe" set "CLOUDFLARED=%LOCALAPPDATA%\cloudflared\cloudflared.exe"
if not defined CLOUDFLARED if exist "%ProgramFiles%\cloudflared\cloudflared.exe" set "CLOUDFLARED=%ProgramFiles%\cloudflared\cloudflared.exe"

if not defined CLOUDFLARED (
  echo.
  echo cloudflared was not found.
  echo Bridge is running, but Feishu public events still need cloudflared.
  echo Install cloudflared or add it to PATH.
  echo.
  pause
  exit /b 2
)

echo Starting cloudflared tunnel...
echo If it shows https://xxxxx.trycloudflare.com, set Feishu event URL to:
echo https://xxxxx.trycloudflare.com/feishu/events
echo Temporary trycloudflare URLs may change every time you restart this script.
start "Xiaochai cloudflared - keep open" cmd /k """%CLOUDFLARED%"" tunnel --url %BRIDGE_URL%"

echo.
echo Startup commands sent.
echo Keep both windows open:
echo - Xiaochai bridge
echo - Xiaochai cloudflared
echo.
pause
