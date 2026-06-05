param(
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"

$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BridgeUrl = "http://127.0.0.1:$Port"
$LogDir = Join-Path $ProjectDir ".tmp_tests"
$CloudflaredLog = Join-Path $LogDir "cloudflared.log"
$DesktopDir = [Environment]::GetFolderPath("Desktop")
$FeishuUrlFile = $null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$FeishuUrlFileName = ((0x5C0F, 0x67F4, 0x98DE, 0x4E66, 0x6700, 0x65B0, 0x5730, 0x5740 | ForEach-Object { [char]$_ }) -join "") + ".txt"
$FeishuUrlFile = Join-Path $DesktopDir $FeishuUrlFileName

Write-Host "Project: $ProjectDir"
Write-Host "Starting Xiaochai bridge..."

$existing = @()
$existing += Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" } |
    Select-Object -ExpandProperty OwningProcess -Unique

$netstatPattern = "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$"
$existing += netstat -ano |
    ForEach-Object {
        $match = [regex]::Match($_, $netstatPattern)
        if ($match.Success) { [int]$match.Groups[1].Value }
    }

$existing = $existing | Where-Object { $_ -and $_ -ne 0 } | Sort-Object -Unique

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

Get-Process cloudflared -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        Write-Host "Stopping old cloudflared: PID $($_.Id)"
        Stop-Process -Id $_.Id -Force -ErrorAction Stop
    } catch {
        Write-Host "Could not stop cloudflared PID $($_.Id): $($_.Exception.Message)"
    }
}

Remove-Item -LiteralPath $CloudflaredLog -ErrorAction SilentlyContinue
$tunnelCommand = @"
& '$cloudflaredPath' tunnel --protocol http2 --url $BridgeUrl --logfile '$CloudflaredLog'
"@

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $tunnelCommand
) -WindowStyle Normal

$publicUrl = $null
for ($i = 0; $i -lt 20; $i++) {
    if (Test-Path -LiteralPath $CloudflaredLog) {
        $logText = Get-Content -LiteralPath $CloudflaredLog -Raw -ErrorAction SilentlyContinue
        $matches = [regex]::Matches($logText, "https://[a-z0-9-]+\.trycloudflare\.com")
        if ($matches.Count -gt 0) {
            $publicUrl = $matches[$matches.Count - 1].Value
            break
        }
    }
    Start-Sleep -Seconds 1
}

if ($publicUrl) {
    $eventUrl = "$publicUrl/feishu/events"
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backupFeishuUrlFile = Join-Path $DesktopDir ($FeishuUrlFileName -replace "\.txt$", "-$stamp.txt")
    $fileLines = @(
        $eventUrl,
        "",
        "Xiaochai Feishu event URL. Copy the first line into Feishu event subscription settings.",
        "Updated at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
        "",
        "Keep both Xiaochai bridge and cloudflared tunnel windows open."
    )
    try {
        $fileLines | Set-Content -LiteralPath $FeishuUrlFile -Encoding UTF8 -ErrorAction Stop
        $fileLines | Set-Content -LiteralPath $backupFeishuUrlFile -Encoding UTF8 -ErrorAction Stop
    } catch {
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $FeishuUrlFile = $backupFeishuUrlFile
        $fileLines | Set-Content -LiteralPath $FeishuUrlFile -Encoding UTF8
    }
    Write-Host ""
    Write-Host "Feishu event URL:"
    Write-Host $eventUrl
    Write-Host "Also saved to: $FeishuUrlFile"
} else {
    Write-Host ""
    Write-Host "Could not find trycloudflare URL yet."
    Write-Host "Check cloudflared window or log:"
    Write-Host $CloudflaredLog
}

Write-Host ""
Write-Host "Startup commands sent."
Write-Host "Keep both windows open:"
Write-Host "- Xiaochai bridge"
Write-Host "- cloudflared tunnel"
Write-Host ""
Write-Host "This launcher window will close in 3 seconds."
Start-Sleep -Seconds 3
