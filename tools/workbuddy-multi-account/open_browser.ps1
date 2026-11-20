# open_browser.ps1
# Wait until the local Web panel /health responds, then open the panel URL in
# the default browser. Mirrors french-learner's "wait_http then start '' url"
# pattern, adapted to a background helper because this tool's server.py runs
# in the FOREGROUND (start.bat blocks at `python server.py`).
# Set MULTIACCT_NO_BROWSER=1 before launching start.bat to skip this helper.
# Keep this file ASCII-only: Windows PowerShell 5.1 reads BOM-less .ps1 as ANSI
# and mangles non-ASCII text (TASK-0041 lesson).
param(
    [int]$Port         = 8000,
    [string]$Url       = '',   # optional override; empty => built from Port
    [string]$HealthUrl = '',   # optional override; empty => built from Port
    [int]$TimeoutSec   = 30,
    [switch]$DryRun    # report readiness only, never launch a browser
)

$ErrorActionPreference = 'SilentlyContinue'
if (-not $Url)       { $Url       = ('http://127.0.0.1:{0}/' -f $Port) }
if (-not $HealthUrl) { $HealthUrl = ('http://127.0.0.1:{0}/health' -f $Port) }

function Test-Ready {
    # curl.exe ships with Windows 10+; --fail makes any non-2xx a failure.
    $null = & curl.exe -s --fail --max-time 2 -o NUL $HealthUrl 2>$null
    return ($LASTEXITCODE -eq 0)
}

if ($DryRun) {
    if (Test-Ready) {
        Write-Host ("[browser][dryrun] health OK ({0}); would open {1}" -f $HealthUrl, $Url)
    } else {
        Write-Host ("[browser][dryrun] health NOT ready ({0}); would wait up to {1}s then open {2}" -f $HealthUrl, $TimeoutSec, $Url)
    }
    exit 0
}

$deadline = (Get-Date).AddSeconds($TimeoutSec)
$ready = $false
while ((Get-Date) -lt $deadline) {
    if (Test-Ready) { $ready = $true; break }
    Start-Sleep -Milliseconds 800
}

if ($ready) {
    Write-Host ("[browser] service ready, opening {0}" -f $Url)
    Start-Process -FilePath $Url
} else {
    Write-Host ("[browser] service not ready within {0}s; skip opening browser (check server log)" -f $TimeoutSec)
}
