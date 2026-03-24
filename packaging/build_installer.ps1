<#
.SYNOPSIS
    Builds a Windows Installer (.exe) for a BioVaram module using Inno Setup.

.DESCRIPTION
    Takes the PyInstaller dist output for a module and packages it into
    a professional Windows installer with:
      - Desktop shortcut
      - Start Menu entry
      - Uninstaller
      - LZMA2 compression
      - Previous version detection

    Prerequisites:
      - Inno Setup 6 installed (ISCC.exe)
      - Module already built via build_modules.ps1 or manual PyInstaller

.PARAMETER Module
    Which module to create an installer for: nanofacs, nta, full_platform
    Default: nanofacs

.PARAMETER Version
    Version string to embed. Default: 1.0.0

.PARAMETER SkipBuild
    Skip the PyInstaller build step (assumes dist/ already exists).

.EXAMPLE
    .\packaging\build_installer.ps1 -Module nanofacs -Version "1.0.0"
    .\packaging\build_installer.ps1 -Module full_platform -Version "1.2.0"
    .\packaging\build_installer.ps1 -Module nanofacs -SkipBuild
#>

param(
    [ValidateSet("nanofacs", "nta", "full_platform", "all")]
    [string]$Module = "nanofacs",
    [string]$Version = "1.0.0",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

# Module definitions
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

# Resolve project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $ProjectRoot "package.json"))) {
    Write-Host "ERROR: Cannot find project root (package.json not found at $ProjectRoot)" -ForegroundColor Red
    exit 1
}

# Find Inno Setup compiler
$ISCC = $null
$isccPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
foreach ($p in $isccPaths) {
    if (Test-Path $p) { $ISCC = $p; break }
}
if (-not $ISCC) {
    # Try PATH
    $isccCmd = Get-Command iscc -ErrorAction SilentlyContinue
    if ($isccCmd) { $ISCC = $isccCmd.Source }
}
if (-not $ISCC) {
    Write-Host "ERROR: Inno Setup 6 not found. Install from https://jrsoftware.org/isdl.php" -ForegroundColor Red
    exit 1
}
Write-Host "  Inno Setup: $ISCC" -ForegroundColor DarkGray

# Handle "all" 
if ($Module -eq "all") {
    $modules = @("nanofacs", "nta", "full_platform")
} else {
    $modules = @($Module)
}

Push-Location $ProjectRoot

try {
    foreach ($mod in $modules) {
        $def = $ModuleDefinitions[$mod]
        
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host "  Building Installer: BioVaram $($def.Title)" -ForegroundColor Cyan
        Write-Host "  Module: $($def.Name) | Version: $Version" -ForegroundColor Cyan
        Write-Host "============================================================" -ForegroundColor Cyan

        $distDir = Join-Path $ProjectRoot "dist\$($def.ExeName)"
        $exePath = Join-Path $ProjectRoot "dist\$($def.ExeName).exe"

        # Step 1: Build if needed
        if (-not $SkipBuild) {
            Write-Host ""
            Write-Host "  [1/3] Building module EXE..." -ForegroundColor Yellow
            & (Join-Path $ProjectRoot "packaging\build_modules.ps1") -Module $mod -Version $Version
            
            if (-not (Test-Path $exePath)) {
                Write-Host "  FAILED: EXE not found at $exePath after build" -ForegroundColor Red
                continue
            }
        } else {
            Write-Host ""
            Write-Host "  [1/3] Skipping build (-SkipBuild)" -ForegroundColor DarkGray
            
            if (-not (Test-Path $exePath)) {
                Write-Host "  ERROR: EXE not found at $exePath. Run without -SkipBuild first." -ForegroundColor Red
                continue
            }
        }

        # Step 2: Create version metadata if missing
        $versionJson = Join-Path $ProjectRoot "dist\$($def.ExeName).version.json"
        if (-not (Test-Path $versionJson)) {
            Write-Host "  [2/3] Creating version.json..." -ForegroundColor Yellow
            $buildDate = Get-Date -Format "yyyy-MM-dd"
            $gitCommit = ""
            try { $gitCommit = (git rev-parse --short HEAD 2>$null) } catch {}
            
            @{
                version    = $Version
                module     = $def.Name
                build_date = $buildDate
                git_commit = $gitCommit
                platform   = "windows-x64"
                packaging  = "onefile"
            } | ConvertTo-Json -Depth 2 | Out-File -FilePath $versionJson -Encoding utf8
        } else {
            Write-Host "  [2/3] version.json exists" -ForegroundColor DarkGray
        }

        # Step 3: Run Inno Setup
        Write-Host "  [3/3] Creating installer..." -ForegroundColor Yellow
        
        $outputDir = Join-Path $ProjectRoot "installer_output"
        if (-not (Test-Path $outputDir)) {
            New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        }

        $issFile = Join-Path $ProjectRoot "packaging\biovaram_installer.iss"

        $isccArgs = @(
            "/DMODULE_NAME=$($def.Name)",
            "/DMODULE_TITLE=$($def.Title)",
            "/DEXE_NAME=$($def.ExeName)",
            "/DAPP_VERSION=$Version",
            "/DDIST_EXE=$exePath",
            "/DVERSION_JSON=$versionJson",
            "/DOUTPUT_DIR=$outputDir",
            "/Q",
            $issFile
        )

        Write-Host "  Running: ISCC $($isccArgs -join ' ')" -ForegroundColor DarkGray
        & $ISCC @isccArgs

        if ($LASTEXITCODE -ne 0) {
            Write-Host "  FAILED: Inno Setup returned exit code $LASTEXITCODE" -ForegroundColor Red
            continue
        }

        $installerName = "BioVaram_$($def.Name)_Setup_v$Version.exe"
        $installerPath = Join-Path $outputDir $installerName
        
        if (Test-Path $installerPath) {
            $installerSize = [math]::Round((Get-Item $installerPath).Length / 1MB, 2)
            Write-Host ""
            Write-Host "  ✅ Installer created: $installerPath" -ForegroundColor Green
            Write-Host "     Size: $installerSize MB" -ForegroundColor Green
        } else {
            Write-Host "  ❌ Installer not found at expected path: $installerPath" -ForegroundColor Red
        }
    }

    # Summary
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  Installer Output Directory:" -ForegroundColor Cyan
    Write-Host "  $outputDir" -ForegroundColor White
    Write-Host "============================================================" -ForegroundColor Cyan
    
    if (Test-Path $outputDir) {
        Get-ChildItem -Path $outputDir -Filter "*.exe" | ForEach-Object {
            $size = [math]::Round($_.Length / 1MB, 2)
            Write-Host "  📦 $($_.Name) — $size MB" -ForegroundColor Green
        }
    }
    
    Write-Host ""

} finally {
    Pop-Location
}
