param(
    [int]$Port = 8787,
    [string]$TunnelName = $env:XIAOCHAI_TUNNEL_NAME,
    [string]$CloudflaredConfig = $env:XIAOCHAI_CLOUDFLARED_CONFIG,
    [string]$PublicHost = $env:XIAOCHAI_PUBLIC_HOST,
    [int]$MaxMessageAgeMinutes = 15,
    [int]$CheckIntervalSeconds = 10
)

$ErrorActionPreference = "Continue"

$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BridgeUrl = "http://127.0.0.1:$Port"
$LogDir = Join-Path $ProjectDir ".tmp_tests"
$BridgeLog = Join-Path $LogDir "xiaochai_bridge.log"
$TunnelLog = Join-Path $LogDir "xiaochai_tunnel.log"
$StatusFile = Join-Path $LogDir "xiaochai_status.txt"
$BridgePidFile = Join-Path $LogDir "xiaochai_bridge.pid"
$TunnelPidFile = Join-Path $LogDir "xiaochai_tunnel.pid"
$LatestCloudflaredLog = Join-Path $LogDir "cloudflared.latest.log"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Status {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    Add-Content -LiteralPath $StatusFile -Value $line -Encoding UTF8
}

function Get-PidFromFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    $pidText = Get-Content -LiteralPath $Path -Raw -ErrorAction SilentlyContinue
    $processIdValue = 0
    if ([int]::TryParse(($pidText -as [string]).Trim(), [ref]$processIdValue)) {
        return $processIdValue
    }
    return $null
}

function Test-ProcessRunning {
    param([string]$PidFile)
    $processIdValue = Get-PidFromFile -Path $PidFile
    if (-not $processIdValue) {
        return $false
    }
    return [bool](Get-Process -Id $processIdValue -ErrorAction SilentlyContinue)
}

function Stop-PortProcess {
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
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Write-Status "Stopped stale process on port ${Port}: PID $processId"
    }
}

function Test-BridgeHealth {
    try {
        $response = Invoke-RestMethod -Uri "$BridgeUrl/health" -TimeoutSec 2
        return [bool]$response.ok
    } catch {
        return $false
    }
}

function Start-Bridge {
    Stop-PortProcess
    $command = @"
Set-Location -LiteralPath '$ProjectDir'
python scripts\feishu_bridge.py --port $Port --mode auto --ask-prefix '?' --max-message-age-minutes $MaxMessageAgeMinutes *> '$BridgeLog'
"@
    $process = Start-Process powershell.exe `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $command) `
        -WorkingDirectory $ProjectDir `
        -WindowStyle Hidden `
        -PassThru
    Set-Content -LiteralPath $BridgePidFile -Value $process.Id -Encoding ASCII
    Write-Status "Started Feishu bridge: PID $($process.Id)"
}

function Resolve-CloudflaredPath {
    $command = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    $fallback = "F:\ruanjian\cloudflared.exe"
    if (Test-Path -LiteralPath $fallback) {
        return $fallback
    }
    return $null
}

function Write-FeishuUrl {
    param([string]$EventUrl, [string]$Mode)
    Write-Status "Feishu event URL ($mode): $EventUrl"
}

function Start-Tunnel {
    $cloudflaredPath = Resolve-CloudflaredPath
    if (-not $cloudflaredPath) {
        Write-Status "cloudflared not found. Bridge is local only."
        return
    }

    $runStamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $runCloudflaredLog = Join-Path $LogDir "cloudflared-$runStamp.log"
    Remove-Item -LiteralPath $LatestCloudflaredLog -Force -ErrorAction SilentlyContinue
    $args = @()
    $mode = "temporary"

    if ($CloudflaredConfig -and $TunnelName) {
        $args = @("tunnel", "--config", $CloudflaredConfig, "run", $TunnelName)
        $mode = "named tunnel with config"
    } elseif ($CloudflaredConfig) {
        $args = @("tunnel", "--config", $CloudflaredConfig, "run")
        $mode = "named tunnel with config"
    } elseif ($TunnelName) {
        $args = @("tunnel", "run", $TunnelName)
        $mode = "named tunnel"
    } else {
        $args = @("tunnel", "--protocol", "http2", "--url", $BridgeUrl, "--logfile", $runCloudflaredLog)
        $mode = "temporary trycloudflare"
    }

    $escapedArgs = ($args | ForEach-Object {
        if ($_ -match "[\s'`"]") {
            "'" + ($_ -replace "'", "''") + "'"
        } else {
            $_
        }
    }) -join " "
    $command = @"
Set-Location -LiteralPath '$ProjectDir'
& '$cloudflaredPath' $escapedArgs *> '$TunnelLog'
"@
    $process = Start-Process powershell.exe `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $command) `
        -WorkingDirectory $ProjectDir `
        -WindowStyle Hidden `
        -PassThru
    Set-Content -LiteralPath $TunnelPidFile -Value $process.Id -Encoding ASCII
    Write-Status "Started cloudflared ($mode): PID $($process.Id)"

    if ($PublicHost) {
        Write-FeishuUrl -EventUrl "https://$PublicHost/feishu/events" -Mode $mode
        return
    }

    if ($mode -eq "temporary trycloudflare") {
        for ($i = 0; $i -lt 30; $i++) {
            if (Test-Path -LiteralPath $runCloudflaredLog) {
                Copy-Item -LiteralPath $runCloudflaredLog -Destination $LatestCloudflaredLog -Force -ErrorAction SilentlyContinue
                $logText = Get-Content -LiteralPath $runCloudflaredLog -Raw -ErrorAction SilentlyContinue
                $matches = [regex]::Matches($logText, "https://[a-z0-9-]+\.trycloudflare\.com")
                if ($matches.Count -gt 0) {
                    $publicUrl = $matches[$matches.Count - 1].Value
                    Write-FeishuUrl -EventUrl "$publicUrl/feishu/events" -Mode $mode
                    Write-Status "Temporary Feishu event URL: $publicUrl/feishu/events"
                    return
                }
            }
            Start-Sleep -Seconds 1
        }
        Write-Status "Could not detect temporary trycloudflare URL yet."
    } else {
        Write-Status "Named tunnel started. Set XIAOCHAI_PUBLIC_HOST so the status file can show the Feishu URL."
    }
}

Write-Status "Watchdog started. Project=$ProjectDir Port=$Port TunnelName=$TunnelName PublicHost=$PublicHost MaxMessageAgeMinutes=$MaxMessageAgeMinutes"

while ($true) {
    if (-not (Test-BridgeHealth)) {
        Write-Status "Bridge health check failed; restarting bridge."
        Start-Bridge
        for ($i = 0; $i -lt 15; $i++) {
            if (Test-BridgeHealth) {
                Write-Status "Bridge health check passed."
                break
            }
            Start-Sleep -Seconds 1
        }
    }

    if (-not (Test-ProcessRunning -PidFile $TunnelPidFile)) {
        Write-Status "Tunnel process is not running; restarting tunnel."
        Start-Tunnel
    }

    Start-Sleep -Seconds $CheckIntervalSeconds
}
