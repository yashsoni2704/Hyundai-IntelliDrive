# Stop Hyundai Knowledge Assistant servers (backend + frontend)
Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Stopping all servers..." -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

Write-Host "Checking ports: 8000 (backend), 5173-5175 (frontend)..." -ForegroundColor Gray

$portsToKill = @(8000, 8001, 5173, 5174, 5175)
$foundProcesses = 0
$failedProcesses = 0

foreach ($port in $portsToKill) {
    $connections = netstat -ano 2>$null | Select-String ":$port\s" | Select-String "LISTENING"
    foreach ($line in $connections) {
        $processId = ($line -split '\s+')[-1]
        if ($processId -match '^\d+$') {
            Write-Host "  [KILL] Port $port - PID $processId" -ForegroundColor Yellow
            taskkill /PID $processId /F | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $foundProcesses += 1
            } else {
                Write-Host "  [ERROR] Could not stop PID $processId. Run this script as Administrator." -ForegroundColor Red
                $failedProcesses += 1
            }
        }
    }
}

if ($foundProcesses -eq 0 -and $failedProcesses -eq 0) {
    Write-Host "[INFO] No processes found on monitored ports" -ForegroundColor Green
} elseif ($failedProcesses -gt 0) {
    Write-Host "[WARNING] Stopped $foundProcesses process(es), failed to stop $failedProcesses process(es)" -ForegroundColor Yellow
} else {
    Write-Host "[SUCCESS] Killed $foundProcesses process(es)" -ForegroundColor Green
}

Write-Host "`n[DONE] You can start fresh with:" -ForegroundColor Cyan
Write-Host "  - start_backend.ps1" -ForegroundColor Gray
Write-Host "  - start_frontend.ps1" -ForegroundColor Gray
Write-Host ""
