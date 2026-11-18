@echo off
chcp 65001 >nul
title WorkBuddy Multi-Account Manager
cd /d "%~dp0"

echo ============================================
echo   WorkBuddy 多账号管理面板
echo   启动后访问 http://127.0.0.1:8000
echo   每天 09:00 自动签到 · 每 5 分钟状态监控
echo   关闭本窗口即停止服务
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 python，请先安装 Python 3.11+
    pause
    exit /b 1
)

python -c "import fastapi, uvicorn, sqlalchemy, apscheduler" 2>nul
if errorlevel 1 (
    echo [提示] 首次运行，安装依赖中...
    pip install -r requirements.txt
    echo.
)

python server.py
pause
