param(
    [int]$Port = 8787,
    [string]$TunnelName = $env:XIAOCHAI_TUNNEL_NAME,
    [string]$CloudflaredConfig = $env:XIAOCHAI_CLOUDFLARED_CONFIG,
    [string]$PublicHost = $env:XIAOCHAI_PUBLIC_HOST,
    [switch]$NoMonitorWindows
)

$ErrorActionPreference = "Stop"

$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogDir = Join-Path $ProjectDir ".tmp_tests"
$WatchdogScript = Join-Path $PSScriptRoot "xiaochai_watchdog.ps1"
$WatchdogPidFile = Join-Path $LogDir "xiaochai_watchdog.pid"
$StatusFile = Join-Path $LogDir "xiaochai_status.txt"
$BridgeLog = Join-Path $LogDir "xiaochai_bridge.log"
$TunnelLatestLog = Join-Path $LogDir "cloudflared.latest.log"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Stop-OldWatchdog {
    if (-not (Test-Path -LiteralPath $WatchdogPidFile)) {
        return
    }
    $oldPidText = Get-Content -LiteralPath $WatchdogPidFile -Raw -ErrorAction SilentlyContinue
    $oldPid = 0
    if ([int]::TryParse(($oldPidText -as [string]).Trim(), [ref]$oldPid)) {
        $oldProcess = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
        if ($oldProcess) {
            Write-Host "Stopping old Xiaochai watchdog: PID $oldPid"
            Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
        }
    }
    Remove-Item -LiteralPath $WatchdogPidFile -ErrorAction SilentlyContinue
}

function Stop-ExistingRuntime {
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
        Write-Host "Stopping old Xiaochai bridge on port ${Port}: PID $processId"
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }

    Get-Process cloudflared -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "Stopping old cloudflared: PID $($_.Id)"
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path -LiteralPath $WatchdogScript)) {
    throw "Missing watchdog script: $WatchdogScript"
}

Stop-OldWatchdog
Stop-ExistingRuntime

foreach ($path in @($StatusFile, $BridgeLog, $TunnelLatestLog)) {
    if (-not (Test-Path -LiteralPath $path)) {
        New-Item -ItemType File -Path $path -Force | Out-Null
    }
}

$arguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $WatchdogScript,
    "-Port", $Port
)

if ($TunnelName) {
    $arguments += @("-TunnelName", $TunnelName)
}
if ($CloudflaredConfig) {
    $arguments += @("-CloudflaredConfig", $CloudflaredConfig)
}
if ($PublicHost) {
    $arguments += @("-PublicHost", $PublicHost)
}

$watchdog = Start-Process powershell.exe `
    -ArgumentList $arguments `
    -WorkingDirectory $ProjectDir `
    -WindowStyle Hidden `
    -PassThru

Set-Content -LiteralPath $WatchdogPidFile -Value $watchdog.Id -Encoding ASCII

if (-not $NoMonitorWindows) {
    $monitors = @(
        @{
            Title = "Xiaochai Status"
            Path = $StatusFile
        },
        @{
            Title = "Xiaochai Bridge"
            Path = $BridgeLog
        },
        @{
            Title = "Xiaochai Tunnel"
            Path = $TunnelLatestLog
        }
    )

    foreach ($monitor in $monitors) {
        $title = $monitor.Title
        $path = $monitor.Path
        $command = @"
`$Host.UI.RawUI.WindowTitle = '$title'
Write-Host '$title'
Write-Host '$path'
Write-Host ''
Write-Host 'This is a monitor window. Closing it will not stop Xiaochai.'
Write-Host ''
Get-Content -LiteralPath '$path' -Wait -Tail 40 -Encoding UTF8
"@
        Start-Process powershell.exe -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command", $command
        ) -WindowStyle Normal | Out-Null
    }
}

Write-Host "Xiaochai watchdog started: PID $($watchdog.Id)"
Write-Host "Status file: $StatusFile"
Write-Host ""

if ($TunnelName -or $CloudflaredConfig -or $PublicHost) {
    Write-Host "Fixed tunnel mode is enabled."
    if ($PublicHost) {
        Write-Host "Feishu event URL should stay fixed:"
        Write-Host "https://$PublicHost/feishu/events"
    } else {
        Write-Host "Set XIAOCHAI_PUBLIC_HOST to show the fixed Feishu event URL here."
    }
} else {
    Write-Host "Temporary tunnel fallback is enabled."
    Write-Host "This can recover the local process, but trycloudflare URLs may still change."
    Write-Host "For stable Feishu use, configure Cloudflare Named Tunnel and XIAOCHAI_PUBLIC_HOST."
}

Write-Host ""
Write-Host "You can close this window. Xiaochai keeps running in the background."
Start-Sleep -Seconds 5
