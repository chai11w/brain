@echo off
setlocal
chcp 65001 >nul

set "PROJECT_DIR=F:\cc\13khoj第二大脑-记忆"
set "PORT=8787"
set "BRIDGE_URL=http://127.0.0.1:%PORT%"
set "LOG_DIR=%PROJECT_DIR%\.tmp_tests"

cd /d "%PROJECT_DIR%"
if errorlevel 1 (
  echo 无法进入项目目录：%PROJECT_DIR%
  pause
  exit /b 1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo 正在启动小柴本地 bridge...
start "小柴 bridge - 请勿关闭" cmd /k "cd /d ""%PROJECT_DIR%"" && python scripts\feishu_bridge.py --port %PORT% --mode auto --ask-prefix ? 1>>""%LOG_DIR%\feishu_bridge.out.log"" 2>>""%LOG_DIR%\feishu_bridge.err.log"""

echo 等待 bridge 健康检查...
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
  echo 小柴 bridge 没有启动成功。
  echo 请查看日志：
  echo %LOG_DIR%\feishu_bridge.err.log
  echo %LOG_DIR%\feishu_bridge.out.log
  echo.
  pause
  exit /b 1
)
echo bridge 已启动：%BRIDGE_URL%/health

echo 正在查找 cloudflared...
set "CLOUDFLARED="
where cloudflared >nul 2>nul
if not errorlevel 1 set "CLOUDFLARED=cloudflared"
if not defined CLOUDFLARED if exist "F:\ruanjian\cloudflared.exe" set "CLOUDFLARED=F:\ruanjian\cloudflared.exe"
if not defined CLOUDFLARED if exist "%LOCALAPPDATA%\cloudflared\cloudflared.exe" set "CLOUDFLARED=%LOCALAPPDATA%\cloudflared\cloudflared.exe"
if not defined CLOUDFLARED if exist "%ProgramFiles%\cloudflared\cloudflared.exe" set "CLOUDFLARED=%ProgramFiles%\cloudflared\cloudflared.exe"

if not defined CLOUDFLARED (
  echo.
  echo 没找到 cloudflared。
  echo 小柴 bridge 已经尝试启动，但飞书公网消息还需要 cloudflared 隧道。
  echo 如果你之前有 cloudflared.exe，请把它放到 F:\ruanjian\cloudflared.exe，或加入 PATH。
  echo.
  pause
  exit /b 2
)

echo 正在启动 cloudflared 隧道...
echo 如果窗口里出现 https://*.trycloudflare.com，请确认飞书后台事件 URL 指向：
echo https://你的公网地址/feishu/events
echo 注意：如果使用的是 trycloudflare 临时地址，每次重启可能都会变，飞书后台 URL 也要同步改。
start "小柴 cloudflared - 请勿关闭" cmd /k """%CLOUDFLARED%"" tunnel --url %BRIDGE_URL%"

echo.
echo 小柴启动命令已发出。
echo 请保持“小柴 bridge”和“小柴 cloudflared”两个窗口打开。
echo 本地健康检查地址：%BRIDGE_URL%/health
echo.
pause
