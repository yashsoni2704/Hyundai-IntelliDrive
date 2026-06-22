@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0frontend"

echo.
echo ================================
echo Hyundai Chatbot - Frontend Start
echo ================================
echo.

REM Check if node_modules exists
if not exist "node_modules" (
    echo [INFO] Installing dependencies...
    call npm install
    if !errorlevel! neq 0 (
        echo.
        echo [ERROR] Failed to install npm dependencies
        pause
        exit /b 1
    )
)

echo [INFO] Starting frontend (Vite) on http://127.0.0.1:5173
echo [INFO] Press Ctrl+C to stop
echo.

npm run dev
pause
