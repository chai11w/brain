param(
    [string]$TaskName = "XiaochaiDailyReport",
    [string]$Time = "10:00",
    [int]$LastHours = 24
)

$ErrorActionPreference = "Stop"

$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RunScript = Join-Path $ProjectDir "scripts\run_daily_report.ps1"

if (-not (Test-Path -LiteralPath $RunScript)) {
    throw "Missing daily report runner: $RunScript"
}

$taskAction = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$RunScript`" -LastHours $LastHours"

schtasks /Create /TN $TaskName /SC DAILY /ST $Time /TR $taskAction /F | Out-Host

Write-Host ""
Write-Host "Installed scheduled task: $TaskName"
Write-Host "Time: $Time"
Write-Host "LastHours: $LastHours"
Write-Host "Action: $taskAction"
Write-Host ""
Write-Host "This task only runs daily-report extraction."
Write-Host "It does not call AI, read reports, diagnose, edit data, or repair anything."
