@echo off
rem Start h1_2026 dashboard: run self-check first, open the page only if all checks pass.
chcp 65001 >nul
cd /d "%~dp0"
python -X utf8 selfcheck.py
echo.
pause
