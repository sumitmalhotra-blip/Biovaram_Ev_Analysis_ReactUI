param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Assert-Exists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    if (-not (Test-Path $Path)) {
        throw "Missing $Label at path: $Path"
    }

    Write-Host "OK: $Label" -ForegroundColor Green
}

Write-Host "Validating release artifacts for v$Version" -ForegroundColor Yellow

$backendExe = Join-Path $ProjectRoot "dist/BioVaram/BioVaram.exe"
$frontendIndex = Join-Path $ProjectRoot "out/index.html"
$installerExe = Join-Path $ProjectRoot "dist-electron/BioVaram-Setup-$Version.exe"
$latestYml = Join-Path $ProjectRoot "dist-electron/latest.yml"
$installerBlockmap = Join-Path $ProjectRoot "dist-electron/BioVaram-Setup-$Version.exe.blockmap"

Assert-Exists -Path $backendExe -Label "Backend desktop binary"
Assert-Exists -Path $frontendIndex -Label "Frontend static export"
Assert-Exists -Path $installerExe -Label "Electron installer"
Assert-Exists -Path $latestYml -Label "Updater metadata (latest.yml)"
Assert-Exists -Path $installerBlockmap -Label "Installer blockmap"

Write-Host "All required rollout artifacts are present for v$Version." -ForegroundColor Green
