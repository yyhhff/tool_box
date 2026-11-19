@echo off
rem ============================================================
rem  h1_2026 dashboard self-check launcher (standalone bat tool)
rem  - Python found : full 22-item selfcheck via selfcheck.py
rem  - No Python    : built-in basic checks (tags / chart funcs / JS syntax via node)
rem  - Usage        : start.bat [--check-only]  (check only, do not open page)
rem ============================================================
setlocal
cd /d "%~dp0"
set HTML=h1_2026.html
set FAIL=0
set OPEN=1
if "%~1"=="--check-only" set OPEN=0

if not exist "%HTML%" (
    echo [FAIL] %HTML% not found in %CD%
    set FAIL=1
    goto :summary
)
echo [PASS] %HTML% exists

where python >nul 2>nul
if not errorlevel 1 (
    echo [INFO] Python found - running full selfcheck ^(22 items^)...
    python -X utf8 selfcheck.py %*
    if errorlevel 1 set FAIL=1
    goto :summary
)

echo [INFO] Python not found - running built-in basic checks...

for %%T in ("<script>" "</script>" "</body>" "</html>") do (
    findstr /c:"%%~T" "%HTML%" >nul 2>nul
    if errorlevel 1 (
        echo [FAIL] missing tag %%~T
        set FAIL=1
    ) else (
        echo [PASS] tag %%~T
    )
)

for %%F in (svgDivergingBars renderLinkProfitChart renderIndexYTDChart techMiniSvg mountChart injectMicroCharts) do (
    findstr /c:"function %%F(" "%HTML%" >nul 2>nul
    if errorlevel 1 (
        echo [FAIL] missing chart function %%F
        set FAIL=1
    ) else (
        echo [PASS] chart function %%F
    )
)

if exist "..\..\data\output\h1_2026\h1_2026_market.csv" (
    echo [PASS] market CSV present
) else (
    echo [FAIL] market CSV missing: data\output\h1_2026\h1_2026_market.csv
    set FAIL=1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [INFO] node not found - skip JS syntax check
) else (
    node -e "const fs=require('fs');const s=fs.readFileSync('h1_2026.html','utf8');const m=s.match(/<script>\r?\n([\s\S]*)\r?\n<\/script>/);if(!m){console.log('[FAIL] cannot extract script block');process.exit(1)}fs.writeFileSync('.selfcheck_tmp.js',m[1]);try{require('child_process').execSync('node --check .selfcheck_tmp.js',{stdio:'inherit'});console.log('[PASS] JS syntax (node --check)')}catch(e){process.exit(1)}finally{try{fs.unlinkSync('.selfcheck_tmp.js')}catch(e){}}"
    if errorlevel 1 set FAIL=1
)

:summary
echo.
if "%FAIL%"=="1" (
    echo ===== Self-check FAILED. Page NOT opened. =====
    if "%OPEN%"=="0" exit /b 1
    pause
    exit /b 1
)
echo ===== Self-check passed. =====
if "%OPEN%"=="0" (
    echo --check-only: page not opened.
) else (
    echo Opening page...
    start "" "%HTML%"
)
pause
exit /b 0
