# cleanup_old_service.ps1
# Kill stale service processes before restart so edited code actually takes effect (TASK-0041).
# Only kills processes that LISTEN on $Port AND whose command line has BOTH
# 'uvicorn' and 'server:app'. Anything else on $Port is left alone; the
# WorkBuddy client itself is never touched. Keep this file ASCII-only because
# Windows PowerShell 5.1 reads BOM-less .ps1 as ANSI and mangles non-ASCII text.
# NOTE (TASK-0044): a half-dead/zombie listener may not be visible to CIM and thus
# cannot be matched here; start.bat detects that case via the health check and
# falls back to a different port. This script is best-effort only.
param(
    [int]$Port      = 8000,   # port to inspect (start.bat passes the selected port)
    [switch]$DryRun           # report what would be killed, do not actually stop anything
)

$ErrorActionPreference = 'SilentlyContinue'
$targets = @()

# Primary: Get-NetTCPConnection (precise: local port $Port, state Listen)
try {
    $conns = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    for ($i = 0; $i -lt $conns.Count; $i++) {
        $targets += [int]$conns[$i].OwningProcess
    }
} catch {}

# Fallback for old systems without Get-NetTCPConnection: parse netstat line by line
if ($targets.Count -eq 0) {
    $lines = @(netstat -ano -p tcp)
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $ln = [string]$lines[$i]
        if ($ln.Contains(':' + $Port + ' ') -and $ln.Contains('LISTENING')) {
            $parts = $ln.Trim().Split()
            $targets += [int]$parts[$parts.Length - 1]
        }
    }
}

$seen = @()
$killed = 0
$skipped = 0
for ($i = 0; $i -lt $targets.Count; $i++) {
    $pid2 = $targets[$i]
    if ($seen -contains $pid2) { continue }
    $seen += $pid2
    $cl = (Get-CimInstance Win32_Process -Filter ('ProcessId=' + $pid2)).CommandLine
    if ($cl -and $cl.Contains('uvicorn') -and $cl.Contains('server:app')) {
        if ($DryRun) {
            Write-Host ("[cleanup][dryrun] would kill stale service PID={0}" -f $pid2)
            $killed++
        } else {
            Write-Host ("[cleanup] found stale service PID={0}, stopping..." -f $pid2)
            try {
                Stop-Process -Id $pid2 -Force -ErrorAction Stop
                $killed++
            } catch {
                Write-Host ("[cleanup] WARN: failed to stop PID={0}: {1}" -f $pid2, $_.Exception.Message)
            }
        }
    } else {
        $skipped++
    }
}

if ($killed -gt 0 -and -not $DryRun) {
    Start-Sleep -Seconds 1
    Write-Host ("[cleanup] stopped {0} stale service(s), port will be free shortly" -f $killed)
} elseif ($seen.Count -eq 0) {
    Write-Host ("[cleanup] port {0} is free, nothing to do" -f $Port)
} elseif ($killed -eq 0) {
    Write-Host ("[cleanup] port {0} used by other program(s) ({1}), skipped to avoid collateral damage" -f $Port, $skipped)
}
