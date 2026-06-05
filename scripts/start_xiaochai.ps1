param(
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"

$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BridgeUrl = "http://127.0.0.1:$Port"
$LogDir = Join-Path $ProjectDir ".tmp_tests"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Host "Project: $ProjectDir"
Write-Host "Starting Xiaochai bridge..."

$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" } |
    Select-Object -ExpandProperty OwningProcess -Unique

foreach ($processId in $existing) {
    try {
        Write-Host "Stopping old process on port ${Port}: PID $processId"
        Stop-Process -Id $processId -Force -ErrorAction Stop
    } catch {
        Write-Host "Could not stop PID ${processId}: $($_.Exception.Message)"
    }
}

$bridgeCommand = @"
Set-Location -LiteralPath '$ProjectDir'
python scripts\feishu_bridge.py --port $Port --mode auto --ask-prefix ?
"@

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $bridgeCommand
) -WindowStyle Normal

Write-Host "Waiting for bridge health check..."
$bridgeOk = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "$BridgeUrl/health" -TimeoutSec 2
        if ($response.ok) {
            $bridgeOk = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $bridgeOk) {
    Write-Host ""
    Write-Host "Bridge failed to start."
    Write-Host "Try running this manually:"
    Write-Host "cd /d `"$ProjectDir`""
    Write-Host "python scripts\feishu_bridge.py --port $Port --mode auto --ask-prefix ?"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Bridge is running: $BridgeUrl/health"

$cloudflaredCommand = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflaredCommand) {
    $fallback = "F:\ruanjian\cloudflared.exe"
    if (Test-Path -LiteralPath $fallback) {
        $cloudflaredPath = $fallback
    } else {
        Write-Host ""
        Write-Host "cloudflared was not found."
        Write-Host "Bridge is running, but Feishu public events still need cloudflared."
        Read-Host "Press Enter to exit"
        exit 2
    }
} else {
    $cloudflaredPath = $cloudflaredCommand.Source
}

Write-Host "Starting cloudflared tunnel..."
Write-Host "If it shows https://xxxxx.trycloudflare.com, set Feishu event URL to:"
Write-Host "https://xxxxx.trycloudflare.com/feishu/events"
Write-Host "Temporary trycloudflare URLs may change every time."

$tunnelCommand = @"
& '$cloudflaredPath' tunnel --url $BridgeUrl
"@

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $tunnelCommand
) -WindowStyle Normal

Write-Host ""
Write-Host "Startup commands sent."
Write-Host "Keep both windows open:"
Write-Host "- Xiaochai bridge"
Write-Host "- cloudflared tunnel"
Write-Host ""
Write-Host "This launcher window will close in 3 seconds."
Start-Sleep -Seconds 3
