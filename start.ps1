# BioVaram EV Analysis Platform - Startup Script
# This script starts both the FastAPI backend and Next.js frontend

Write-Host "Starting BioVaram EV Analysis Platform..." -ForegroundColor Cyan

function Test-PortInUse {
    param([int]$Port)
    try {
        $connection = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop | Select-Object -First 1
        return $null -ne $connection
    }
    catch {
        return $false
    }
}

function Get-NextDevProcess {
    try {
        return Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
            Where-Object { $_.CommandLine -like "*next*dev*" }
    }
    catch {
        return @()
    }
}

# Start FastAPI backend
Write-Host "`nStarting FastAPI Backend on http://localhost:8000..." -ForegroundColor Green
$backendDir = "$PSScriptRoot\backend"
$pythonExe = "$backendDir\venv\Scripts\python.exe"

if (Test-Path $pythonExe) {
    if (Test-PortInUse -Port 8000) {
        Write-Host "   [INFO] Port 8000 already in use; backend appears to be running. Skipping duplicate start." -ForegroundColor Yellow
    }
    else {
        Start-Process -FilePath $pythonExe -ArgumentList "$backendDir\run_api.py" -WindowStyle Normal
        Write-Host "   [OK] Backend started" -ForegroundColor Green
    }
}
else {
    Write-Host "   [ERROR] Backend venv not found. Run: cd backend; python -m venv venv; .\venv\Scripts\pip install -r requirements.txt" -ForegroundColor Red
}

Start-Sleep -Seconds 2

# Start Next.js frontend
Write-Host "`nStarting Next.js Frontend on http://localhost:3000..." -ForegroundColor Blue
Set-Location $PSScriptRoot

$nextProcesses = @(Get-NextDevProcess)
if ($nextProcesses.Count -gt 0) {
    Write-Host "   [INFO] Next.js dev server already running; skipping duplicate start." -ForegroundColor Yellow
}
else {
    $nextLockPath = "$PSScriptRoot\.next\dev\lock"
    if (Test-Path $nextLockPath) {
        Remove-Item $nextLockPath -Force
        Write-Host "   [INFO] Removed stale Next.js lock file." -ForegroundColor Yellow
    }

    $frontendCommand = Get-Command pnpm -ErrorAction SilentlyContinue
    if ($frontendCommand) {
        Start-Process -FilePath "pnpm" -ArgumentList "dev" -WorkingDirectory $PSScriptRoot -WindowStyle Normal
    }
    else {
        Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory $PSScriptRoot -WindowStyle Normal
    }
    Write-Host "   [OK] Frontend started" -ForegroundColor Blue
}

Write-Host "`nPlatform startup script completed." -ForegroundColor Green
Write-Host "`nAccess the application:"
Write-Host "   Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "   Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
