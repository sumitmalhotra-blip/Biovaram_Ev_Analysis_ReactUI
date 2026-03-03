<#
.SYNOPSIS
    Builds the BioVaram EV Analysis Platform desktop application.

.DESCRIPTION
    This script:
    1. Builds the Next.js frontend (static export to out/)
    2. Runs PyInstaller to create the desktop EXE bundle
    3. Validates the output

.EXAMPLE
    .\packaging\build.ps1
    .\packaging\build.ps1 -SkipFrontend
#>

param(
    [switch]$SkipFrontend,
    [switch]$SkipClean
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $ProjectRoot "package.json"))) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  BioVaram EV Analysis Platform — Desktop Build" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Project root: $ProjectRoot"
Write-Host ""

# Navigate to project root
Push-Location $ProjectRoot

try {
    # =============================================
    # Step 1: Build Frontend (unless skipped)
    # =============================================
    if (-not $SkipFrontend) {
        Write-Host "[1/4] Building frontend (Next.js static export)..." -ForegroundColor Yellow
        
        if (-not (Test-Path "node_modules")) {
            Write-Host "  Installing dependencies..."
            pnpm install
        }

        pnpm build
        
        if (-not (Test-Path "out\index.html")) {
            throw "Frontend build failed — out/index.html not found!"
        }
        
        $fileCount = (Get-ChildItem -Path "out" -Recurse -File).Count
        $totalSize = [math]::Round((Get-ChildItem -Path "out" -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
        Write-Host "  Frontend built: $fileCount files, ${totalSize} MB" -ForegroundColor Green
    } else {
        Write-Host "[1/4] Skipping frontend build (--SkipFrontend)" -ForegroundColor DarkGray
        if (-not (Test-Path "out\index.html")) {
            throw "Frontend not found at out/. Run without -SkipFrontend first!"
        }
    }

    # =============================================
    # Step 2: Clean previous build (unless skipped)
    # =============================================
    if (-not $SkipClean) {
        Write-Host "[2/4] Cleaning previous build artifacts..." -ForegroundColor Yellow
        
        if (Test-Path "dist\BioVaram") {
            Remove-Item -Recurse -Force "dist\BioVaram"
            Write-Host "  Removed dist/BioVaram/"
        }
        if (Test-Path "build\BioVaram") {
            Remove-Item -Recurse -Force "build\BioVaram"
            Write-Host "  Removed build/BioVaram/"
        }
    } else {
        Write-Host "[2/4] Skipping clean (--SkipClean)" -ForegroundColor DarkGray
    }

    # =============================================
    # Step 3: Run PyInstaller
    # =============================================
    Write-Host "[3/4] Running PyInstaller..." -ForegroundColor Yellow
    
    # Verify PyInstaller is available
    $pyinstaller = Get-Command pyinstaller -ErrorAction SilentlyContinue
    if (-not $pyinstaller) {
        throw "PyInstaller not found. Install with: pip install pyinstaller"
    }

    pyinstaller packaging\biovaram.spec --noconfirm --clean
    
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed with exit code $LASTEXITCODE"
    }

    # =============================================
    # Step 4: Validate Output
    # =============================================
    Write-Host "[4/4] Validating build output..." -ForegroundColor Yellow
    
    $exePath = "dist\BioVaram\BioVaram.exe"
    if (-not (Test-Path $exePath)) {
        throw "Build validation failed — BioVaram.exe not found!"
    }
    
    $checks = @(
        @{ Path = "dist\BioVaram\BioVaram.exe";           Label = "Executable" },
        @{ Path = "dist\BioVaram\frontend\index.html";     Label = "Frontend" },
        @{ Path = "dist\BioVaram\config\channel_config.json"; Label = "Config" }
    )
    
    $allPassed = $true
    foreach ($check in $checks) {
        if (Test-Path $check.Path) {
            Write-Host "  ✅ $($check.Label): $($check.Path)" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $($check.Label): $($check.Path) NOT FOUND" -ForegroundColor Red
            $allPassed = $false
        }
    }

    # Calculate total size
    $totalSize = [math]::Round((Get-ChildItem -Path "dist\BioVaram" -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    $exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 2)
    
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  Build Complete!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  EXE:         dist\BioVaram\BioVaram.exe ($exeSize MB)"
    Write-Host "  Total Size:  $totalSize MB"
    Write-Host ""
    Write-Host "  To run:      .\dist\BioVaram\BioVaram.exe"
    Write-Host ""
    
    if (-not $allPassed) {
        Write-Host "  ⚠️  Some files missing — check the build output above." -ForegroundColor Yellow
    }
    
} finally {
    Pop-Location
}
