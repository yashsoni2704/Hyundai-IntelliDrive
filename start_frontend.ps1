# Start Hyundai Knowledge Assistant — Frontend
$frontendDir = Join-Path $PSScriptRoot "frontend"
Set-Location $frontendDir

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Hyundai Chatbot - Frontend Start" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "[INFO] Installing dependencies..." -ForegroundColor Gray
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install npm dependencies" -ForegroundColor Red
        Read-Host "`nPress Enter to exit"
        exit 1
    }
}

Write-Host "[INFO] Starting frontend (Vite) on http://127.0.0.1:5173" -ForegroundColor Green
Write-Host "[INFO] Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

npm run dev
