# BioVaram EV Analysis Platform - Startup Script
# This script starts both the FastAPI backend and Next.js frontend

Write-Host "🚀 Starting BioVaram EV Analysis Platform..." -ForegroundColor Cyan

# Start FastAPI backend
Write-Host "`n📦 Starting FastAPI Backend on http://localhost:8000..." -ForegroundColor Green
$backendDir = "$PSScriptRoot\backend"
$pythonExe = "$backendDir\venv\Scripts\python.exe"

if (Test-Path $pythonExe) {
    Start-Process -FilePath $pythonExe -ArgumentList "$backendDir\run_api.py" -WindowStyle Normal
    Write-Host "   ✓ Backend started" -ForegroundColor Green
} else {
    Write-Host "   ✗ Backend venv not found. Run: cd backend; python -m venv venv; .\venv\Scripts\pip install -r requirements.txt" -ForegroundColor Red
}

Start-Sleep -Seconds 2

# Start Next.js frontend
Write-Host "`n🎨 Starting Next.js Frontend on http://localhost:3000..." -ForegroundColor Blue
Set-Location $PSScriptRoot
Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WindowStyle Normal
Write-Host "   ✓ Frontend started" -ForegroundColor Blue

Write-Host "`n✅ Platform Started!" -ForegroundColor Green
Write-Host "`n📊 Access the application:"
Write-Host "   Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "   Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
