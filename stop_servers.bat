@echo off
echo.
echo ================================
echo Stopping all servers...
echo ================================
echo.
echo Checking ports: 8000 (backend), 5173-5175 (frontend)...

setlocal enabledelayedexpansion
set "found=0"
set "failed=0"

for %%p in (8000 8001 5173 5174 5175) do (
  for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%%p " ^| findstr LISTENING') do (
    echo   [KILL] Port %%p - PID %%a
    taskkill /PID %%a /F >nul
    if !errorlevel! equ 0 (
      set /a found=!found!+1
    ) else (
      echo   [ERROR] Could not stop PID %%a. Run this script as Administrator.
      set /a failed=!failed!+1
    )
  )
)

if !found! equ 0 if !failed! equ 0 (
    echo [INFO] No processes found on monitored ports
) else if !failed! gtr 0 (
    echo [WARNING] Stopped !found! process(es), failed to stop !failed! process(es)
) else (
    echo [SUCCESS] Killed !found! process(es)
)

echo.
echo [DONE] You can start fresh with:
echo   - start_backend.bat
echo   - start_frontend.bat
echo.
