param(
    [string]$Date = "today",
    [string]$OutputDir = "reports"
)

$ErrorActionPreference = "Stop"

$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogDir = Join-Path $ProjectDir ".tmp_tests"
$LogPath = Join-Path $LogDir "daily_report_task.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Set-Location -LiteralPath $ProjectDir

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value "[$timestamp] start daily-report date=$Date output_dir=$OutputDir"

$output = & python brain.py daily-report --date $Date --output-dir $OutputDir 2>&1
$exitCode = $LASTEXITCODE

$output | Add-Content -LiteralPath $LogPath -Encoding UTF8
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value "[$timestamp] exit_code=$exitCode"

if ($exitCode -ne 0) {
    throw "daily-report failed with exit code $exitCode"
}
