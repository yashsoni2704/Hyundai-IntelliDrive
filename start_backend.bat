@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0backend"

echo.
echo ================================
echo Hyundai Chatbot - Backend Start
echo ================================
echo.

REM Check if Excel file exists
if not exist "..\data\hyundai_faq.xlsx" (
    echo.
    echo [ERROR] Excel file not found: .\data\hyundai_faq.xlsx
    echo [FIX] Please move hyundai_faq.xlsx from project root to the data/ folder
    echo.
    pause
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python not found. Please install Python 3.10+
    echo.
    pause
    exit /b 1
)

echo [INFO] Starting backend on http://localhost:8000
echo [INFO] Press Ctrl+C to stop
echo [INFO] First startup: Knowledge base initialization may take 2-5 minutes
echo [INFO] (Downloading embedding model 2GB on first run, then never again)
echo.
echo [IMPORTANT] Do NOT restart/Ctrl+C during initialization!
echo.

REM Run WITHOUT --reload to prevent file watcher from interrupting initialization
python -m uvicorn app:app --port 8000
pause
