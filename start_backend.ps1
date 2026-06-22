# Start Hyundai Knowledge Assistant — Backend
$backendDir = Join-Path $PSScriptRoot "backend"
$excelFile = Join-Path $PSScriptRoot "data" "hyundai_faq.xlsx"

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Hyundai Chatbot - Backend Start" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

# Check if Excel file exists
if (-not (Test-Path $excelFile)) {
    Write-Host "[ERROR] Excel file not found: $excelFile" -ForegroundColor Red
    Write-Host "[FIX] Please move hyundai_faq.xlsx from project root to the data/ folder" -ForegroundColor Yellow
    Read-Host "`nPress Enter to exit"
    exit 1
}

# Check if Python is available
try {
    python --version | Out-Null
} catch {
    Write-Host "[ERROR] Python not found. Please install Python 3.10+" -ForegroundColor Red
    Read-Host "`nPress Enter to exit"
    exit 1
}

Set-Location $backendDir

$port = 8000
Write-Host "[INFO] Starting backend on http://localhost:$port" -ForegroundColor Green
Write-Host "[INFO] Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host "[INFO] First startup: Knowledge base initialization may take 2-5 minutes" -ForegroundColor Gray
Write-Host "[INFO] (Downloading embedding model 2GB on first run, then never again)" -ForegroundColor Gray
Write-Host ""
Write-Host "[IMPORTANT] Do NOT restart/Ctrl+C during initialization!" -ForegroundColor Yellow
Write-Host ""

# Run WITHOUT --reload to prevent file watcher from interrupting initialization
python -m uvicorn app:app --port $port
