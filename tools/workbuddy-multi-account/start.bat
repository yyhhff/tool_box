@echo off
chcp 65001 >nul
title WorkBuddy Multi-Account Manager
cd /d "%~dp0"

rem NOTE: keep this file ASCII-only. cmd pre-reads a buffer using the system
rem ANSI code page BEFORE chcp takes effect; non-ASCII text near the top gets
rem mangled and can break the powershell calls below (TASK-0041/0044).

echo ============================================
echo   WorkBuddy Multi-Account Manager
echo   Auto check-in daily 09:00 / status watch every 5 min
echo   Close this window to stop the service
echo ============================================
echo.

rem === Step 1: decide the preferred port (TASK-0044) ===
rem WORKBUDDY_MA_PORT fixes the port (no auto-fallback); otherwise start at 8000.
set "PORT=8000"
set "PORT_MANUAL="
if defined WORKBUDDY_MA_PORT (
    set "PORT=%WORKBUDDY_MA_PORT%"
    set "PORT_MANUAL=1"
)

rem === Step 2: best-effort cleanup of stale service on the preferred port ===
echo [cleanup] Checking port %PORT% for a stale service...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0cleanup_old_service.ps1" -Port %PORT%
if errorlevel 1 echo [cleanup] WARN: cleanup script failed, continuing to start anyway

rem === Step 3: port must be free; auto-pick a fallback if occupied ===
call :port_busy %PORT%
if errorlevel 1 goto port_ok
rem -- port is occupied --
if defined PORT_MANUAL (
    echo [port] ERROR: fixed port %PORT% is occupied.
    echo [port] Unset WORKBUDDY_MA_PORT to allow auto-fallback, or pick a free port.
    pause
    exit /b 1
)
echo [port] %PORT% is occupied by a stale or other service, picking a fallback...
call :pick_fallback
if errorlevel 1 (
    echo [port] ERROR: no free port found in 8001-8019.
    pause
    exit /b 1
)

:port_ok
echo [port] using port %PORT%
set "WORKBUDDY_MA_PORT=%PORT%"
echo.

rem === Step 4: dependency check ===
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] python not found, install Python 3.11+ first
    pause
    exit /b 1
)
python -c "import fastapi, uvicorn, sqlalchemy, apscheduler" 2>nul
if errorlevel 1 (
    echo [INFO] first run, installing dependencies...
    pip install -r requirements.txt
    echo.
)

rem === Step 5: auto-open browser in background once health is ready ===
if defined MULTIACCT_NO_BROWSER (
    echo [browser] auto-open disabled by MULTIACCT_NO_BROWSER
) else (
    echo [browser] will open the panel once the service is ready...
    start "" /min powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0open_browser.ps1" -Port %PORT%
)

echo [start] launching server on port %PORT% ...
python server.py
pause
exit /b 0

rem ============ subroutines ============
:port_busy
rem returns: exit /b 0 = occupied, exit /b 1 = free
netstat -ano -p tcp | findstr /r /c:":%1 .*LISTENING" >nul 2>nul
if errorlevel 1 (
    exit /b 1
)
exit /b 0

:pick_fallback
rem find the first free port in 8001-8019, store it in PORT; exit /b 1 if none
set /a CAND=8001
:fallback_loop
if %CAND% GTR 8019 exit /b 1
netstat -ano -p tcp | findstr /r /c:":%CAND% .*LISTENING" >nul 2>nul
if errorlevel 1 (
    set "PORT=%CAND%"
    echo [port] picked fallback port %CAND%
    exit /b 0
)
set /a CAND+=1
goto fallback_loop
