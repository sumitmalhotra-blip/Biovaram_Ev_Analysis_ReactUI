<#
.SYNOPSIS
    Builds individual BioVaram module EXEs for distribution.

.DESCRIPTION
    This script builds one or more BioVaram modules as standalone desktop
    applications. Each module gets its own EXE with a module-specific
    frontend build (tabs restricted to that module only).

    Modules available:
      nanofacs       - NanoFACS + Dashboard + AI Chat
      nta            - NTA Analysis + Dashboard + AI Chat
      full_platform  - Full platform (all features)

.PARAMETER Module
    Which module(s) to build. Use "all" to build everything.
    Default: "all"

.PARAMETER SkipFrontend
    Skip the Next.js frontend build (reuse existing out_<module>/ directory).

.PARAMETER SkipClean
    Skip cleaning previous build artifacts.

.PARAMETER Version
    Version string to embed in the build. Default: "1.0.0"

.EXAMPLE
    .\packaging\build_modules.ps1 -Module nanofacs
    .\packaging\build_modules.ps1 -Module nanofacs,nta -Version "1.2.0"
    .\packaging\build_modules.ps1 -Module all
    .\packaging\build_modules.ps1 -Module nanofacs -SkipFrontend
#>

param(
    [string[]]$Module = @("all"),
    [switch]$SkipFrontend,
    [switch]$SkipClean,
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"

# =============================================================================
# Module Definitions
# =============================================================================

$ModuleDefinitions = @{
    nanofacs = @{
        Name     = "nanofacs"
        Title    = "NanoFACS Analysis"
        ExeName  = "BioVaram_NanoFACS"
        EnvVar   = "nanofacs"
    }
    nta = @{
        Name     = "nta"
        Title    = "NTA Analysis"
        ExeName  = "BioVaram_NTA"
        EnvVar   = "nta"
    }
    full_platform = @{
        Name     = "full_platform"
        Title    = "EV Analysis Platform"
        ExeName  = "BioVaram"
        EnvVar   = "full"
    }
}

# Resolve "all"
if ($Module -contains "all") {
    $Module = @("nanofacs", "nta", "full_platform")
}

# =============================================================================
# Project root
# =============================================================================

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $ProjectRoot "package.json"))) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  BioVaram Module Builder" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Project root:  $ProjectRoot"
Write-Host "  Modules:       $($Module -join ', ')"
Write-Host "  Version:       $Version"
Write-Host "  Skip frontend: $SkipFrontend"
Write-Host ""

Push-Location $ProjectRoot

try {
    # Verify tools
    if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
        throw "pnpm not found. Install with: npm install -g pnpm"
    }
    if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
        throw "PyInstaller not found. Install with: pip install pyinstaller"
    }

    # Install Node dependencies if needed
    if (-not (Test-Path "node_modules") -and -not $SkipFrontend) {
        Write-Host "  Installing Node dependencies..." -ForegroundColor Yellow
        pnpm install
    }

    $totalModules = $Module.Count
    $currentModule = 0
    $results = @()

    foreach ($mod in $Module) {
        $currentModule++
        $def = $ModuleDefinitions[$mod]
        
        if (-not $def) {
            Write-Host "  Unknown module '$mod' -- skipping" -ForegroundColor Red
            $results += @{ Module = $mod; Status = "SKIPPED"; Reason = "Unknown module" }
            continue
        }

        Write-Host ""
        Write-Host "------------------------------------------------------------" -ForegroundColor Cyan
        Write-Host "  [$currentModule/$totalModules] Building: $($def.Title)" -ForegroundColor Cyan
        Write-Host "  Module: $($def.Name) => $($def.ExeName).exe" -ForegroundColor Cyan
        Write-Host "------------------------------------------------------------" -ForegroundColor Cyan

        $outDir = "out_$($def.Name)"
        $distDir = "dist\$($def.ExeName)"

        # =================================================================
        # Step A: Build module-specific frontend
        # =================================================================
        if (-not $SkipFrontend) {
            Write-Host "  [A] Building frontend (NEXT_PUBLIC_MODULE=$($def.EnvVar))..." -ForegroundColor Yellow
            
            $env:NEXT_PUBLIC_MODULE = $def.EnvVar
            
            # Build Next.js
            pnpm build
            
            if (-not (Test-Path "out\index.html")) {
                Write-Host "  FAILED: out/index.html not found after build" -ForegroundColor Red
                $results += @{ Module = $mod; Status = "FAILED"; Reason = "Frontend build failed" }
                continue
            }
            
            # Move out/ to out_<module>/
            if (Test-Path $outDir) {
                Remove-Item -Recurse -Force $outDir
            }
            Rename-Item -Path "out" -NewName $outDir
            
            $fileCount = (Get-ChildItem -Path $outDir -Recurse -File).Count
            $totalSize = [math]::Round((Get-ChildItem -Path $outDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
            Write-Host "  Frontend: $fileCount files, ${totalSize} MB => $outDir/" -ForegroundColor Green
            
            # Reset env var
            Remove-Item Env:\NEXT_PUBLIC_MODULE -ErrorAction SilentlyContinue
        } else {
            Write-Host "  [A] Skipping frontend build (-SkipFrontend)" -ForegroundColor DarkGray
            if (-not (Test-Path "$outDir\index.html")) {
                # Fall back to default out/
                if (-not (Test-Path "out\index.html")) {
                    Write-Host "  WARN: No frontend at $outDir/ or out/. API-only build." -ForegroundColor Yellow
                } else {
                    $outDir = "out"
                }
            }
        }

        # =================================================================
        # Step B: Clean previous build
        # =================================================================
        if (-not $SkipClean) {
            Write-Host "  [B] Cleaning previous $($def.ExeName) build..." -ForegroundColor Yellow
            if (Test-Path $distDir) {
                Remove-Item -Recurse -Force $distDir
            }
            $buildDir = "build\$($def.ExeName)"
            if (Test-Path $buildDir) {
                Remove-Item -Recurse -Force $buildDir
            }
        }

        # =================================================================
        # Step C: Run PyInstaller with module spec
        # =================================================================
        Write-Host "  [C] Running PyInstaller => $($def.ExeName).exe..." -ForegroundColor Yellow
        
        $env:BIOVARAM_MODULE_NAME = $def.Name
        $env:BIOVARAM_MODULE_TITLE = $def.Title
        $env:BIOVARAM_EXE_NAME = $def.ExeName
        $env:BIOVARAM_FRONTEND_DIR = Join-Path $ProjectRoot $outDir
        
        pyinstaller packaging\biovaram_module.spec --noconfirm --clean
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  FAILED: PyInstaller returned exit code $LASTEXITCODE" -ForegroundColor Red
            $results += @{ Module = $mod; Status = "FAILED"; Reason = "PyInstaller error" }
            
            # Clean up env vars
            Remove-Item Env:\BIOVARAM_MODULE_NAME -ErrorAction SilentlyContinue
            Remove-Item Env:\BIOVARAM_MODULE_TITLE -ErrorAction SilentlyContinue
            Remove-Item Env:\BIOVARAM_EXE_NAME -ErrorAction SilentlyContinue
            Remove-Item Env:\BIOVARAM_FRONTEND_DIR -ErrorAction SilentlyContinue
            continue
        }
        
        # Clean up env vars
        Remove-Item Env:\BIOVARAM_MODULE_NAME -ErrorAction SilentlyContinue
        Remove-Item Env:\BIOVARAM_MODULE_TITLE -ErrorAction SilentlyContinue
        Remove-Item Env:\BIOVARAM_EXE_NAME -ErrorAction SilentlyContinue
        Remove-Item Env:\BIOVARAM_FRONTEND_DIR -ErrorAction SilentlyContinue

        # =================================================================
        # Step D: Create version.json
        # =================================================================
        Write-Host "  [D] Creating version metadata..." -ForegroundColor Yellow
        
        $buildDate = Get-Date -Format "yyyy-MM-dd"
        $gitCommit = ""
        try { $gitCommit = (git rev-parse --short HEAD 2>$null) } catch {}
        
        $versionInfo = @{
            version    = $Version
            module     = $def.Name
            build_date = $buildDate
            git_commit = $gitCommit
            platform   = "windows-x64"
        } | ConvertTo-Json -Depth 2
        
        $versionPath = Join-Path $distDir "version.json"
        $versionInfo | Out-File -FilePath $versionPath -Encoding utf8

        # =================================================================
        # Step E: Validate
        # =================================================================
        $exePath = Join-Path $distDir "$($def.ExeName).exe"
        if (Test-Path $exePath) {
            $exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 2)
            $totalSize = [math]::Round((Get-ChildItem -Path $distDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
            Write-Host "  [OK] $($def.ExeName).exe -- $exeSize MB (total: $totalSize MB)" -ForegroundColor Green
            $results += @{ Module = $mod; Status = "OK"; ExeSize = "$exeSize MB"; TotalSize = "$totalSize MB"; Path = $exePath }
        } else {
            Write-Host "  [FAIL] $($def.ExeName).exe NOT FOUND at $exePath" -ForegroundColor Red
            $results += @{ Module = $mod; Status = "FAILED"; Reason = "EXE not found" }
        }
    }

    # =====================================================================
    # Summary
    # =====================================================================
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  Build Summary" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    
    foreach ($r in $results) {
        if ($r.Status -eq "OK") {
            Write-Host "  [OK]   $($r.Module.PadRight(16)) => dist\$($ModuleDefinitions[$r.Module].ExeName)\$($ModuleDefinitions[$r.Module].ExeName).exe ($($r.TotalSize))" -ForegroundColor Green
        } elseif ($r.Status -eq "SKIPPED") {
            Write-Host "  [SKIP] $($r.Module.PadRight(16)) => SKIPPED: $($r.Reason)" -ForegroundColor Yellow
        } else {
            Write-Host "  [FAIL] $($r.Module.PadRight(16)) => FAILED: $($r.Reason)" -ForegroundColor Red
        }
    }

    $successCount = ($results | Where-Object { $_.Status -eq "OK" }).Count
    Write-Host ""
    if ($successCount -eq $totalModules) { $statusColor = "Green" } else { $statusColor = "Yellow" }
    $msg = "  " + $successCount + "/" + $totalModules + " modules built successfully."
    Write-Host $msg -ForegroundColor $statusColor
    Write-Host ""
    Write-Host '  To run a module:  .\dist\<ExeName>\<ExeName>.exe'
    Write-Host ""

} finally {
    Pop-Location
}
