@echo off
setlocal

set "PROJECT_DIR="
for /d %%I in ("F:\cc\13khoj*") do (
  if exist "%%~fI\scripts\start_xiaochai.ps1" set "PROJECT_DIR=%%~fI"
)

if not defined PROJECT_DIR (
  echo Could not find Xiaochai project under F:\cc\13khoj*
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_DIR%\scripts\start_xiaochai.ps1"
