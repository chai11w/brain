param(
    [int]$LastHours = 24,
    [string]$OutputDir = "reports",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogDir = Join-Path $ProjectDir ".tmp_tests"
$LogPath = Join-Path $LogDir "daily_report_task.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Set-Location -LiteralPath $ProjectDir

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value "[$timestamp] start daily-report last_hours=$LastHours output_dir=$OutputDir"

if (-not $Force -and $LastHours -eq 24) {
    $today = Get-Date -Format "yyyy-MM-dd"
    $existing = Get-ChildItem -LiteralPath $OutputDir -Filter "last-24h-$today-*.md" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($existing) {
        Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value "[$timestamp] skip existing_daily_report=$($existing.FullName)"
        Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value "[$timestamp] exit_code=0"
        return
    }
}

$output = & python brain.py daily-report --last-hours $LastHours --output-dir $OutputDir 2>&1
$exitCode = $LASTEXITCODE

$output | Add-Content -LiteralPath $LogPath -Encoding UTF8
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value "[$timestamp] exit_code=$exitCode"

if ($exitCode -ne 0) {
    throw "daily-report failed with exit code $exitCode"
}
