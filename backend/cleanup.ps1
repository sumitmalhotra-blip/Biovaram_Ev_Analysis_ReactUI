# CRMIT Project Cleanup Script
# Removes temporary files, caches, and generated data

Write-Host "🧹 Cleaning CRMIT Project..." -ForegroundColor Cyan

# Remove Python cache
Write-Host "Removing Python __pycache__ directories..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Remove pytest cache
Write-Host "Removing pytest cache..." -ForegroundColor Yellow
Remove-Item -Path .pytest_cache -Recurse -Force -ErrorAction SilentlyContinue

# Clean uploads directory (keep structure)
Write-Host "Cleaning uploads directory..." -ForegroundColor Yellow
Get-ChildItem -Path uploads -File -ErrorAction SilentlyContinue | Where-Object { 
    $_.Extension -in @('.fcs', '.parquet', '.csv') 
} | Remove-Item -Force

# Clean generated images (keep structure)
Write-Host "Cleaning generated images..." -ForegroundColor Yellow
Get-ChildItem -Path images -File -Filter "*.png" -ErrorAction SilentlyContinue | Remove-Item -Force

# Remove log files
Write-Host "Removing log files..." -ForegroundColor Yellow
Get-ChildItem -Path logs -File -Filter "*.csv" -ErrorAction SilentlyContinue | Remove-Item -Force

# Remove temporary notebooks outputs
Write-Host "Cleaning notebook outputs..." -ForegroundColor Yellow
Get-ChildItem -Path notebooks -Recurse -Directory -Filter ".ipynb_checkpoints" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Remove empty files
Write-Host "Removing empty files..." -ForegroundColor Yellow
Get-ChildItem -Recurse -File | Where-Object { $_.Length -eq 0 } | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "✅ Cleanup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Cleaned:" -ForegroundColor Cyan
Write-Host "  - Python cache files (__pycache__)" -ForegroundColor Gray
Write-Host "  - Test cache (.pytest_cache)" -ForegroundColor Gray
Write-Host "  - Temporary uploads (*.fcs, *.parquet)" -ForegroundColor Gray
Write-Host "  - Generated images (*.png)" -ForegroundColor Gray
Write-Host "  - Log files (*.csv)" -ForegroundColor Gray
Write-Host "  - Empty files" -ForegroundColor Gray
