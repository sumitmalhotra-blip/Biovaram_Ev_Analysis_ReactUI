param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$ElectronOutputDir = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $ElectronOutputDir) {
    $ElectronOutputDir = "dist-electron-$Version"
}

function Test-SigningProvisioned {
    if ($env:WIN_CSC_LINK -or $env:WIN_CSC_KEY_PASSWORD) {
        return $true
    }
    if ($env:CSC_LINK -or $env:CSC_KEY_PASSWORD) {
        return $true
    }
    if ($env:CSC_NAME) {
        return $true
    }

    return $false
}

if (-not (Test-SigningProvisioned)) {
    throw "No signing configuration found. Set WIN_CSC_LINK/WIN_CSC_KEY_PASSWORD or CSC_LINK/CSC_KEY_PASSWORD or CSC_NAME."
}

Write-Host "Building signed desktop candidate v$Version" -ForegroundColor Yellow
npx.cmd electron-builder --win nsis --publish never --config.directories.output=$ElectronOutputDir
if ($LASTEXITCODE -ne 0) {
    throw "Signed candidate build failed with exit code $LASTEXITCODE"
}

& "$ProjectRoot\scripts\validate-code-signing.ps1" -Version $Version -ArtifactsDir $ElectronOutputDir -RequireValid

Write-Host "Signed candidate build and signature validation passed for v$Version." -ForegroundColor Green
