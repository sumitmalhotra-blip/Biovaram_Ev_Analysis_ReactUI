param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$ArtifactsDir = "dist-electron",
    [switch]$RequireValid
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$installerPath = Join-Path $ProjectRoot "$ArtifactsDir/BioVaram-Setup-$Version.exe"
if (-not (Test-Path $installerPath)) {
    throw "Installer not found for signature validation: $installerPath"
}

$signature = Get-AuthenticodeSignature $installerPath

Write-Host "Signature validation for: $installerPath" -ForegroundColor Yellow
Write-Host "Status: $($signature.Status)" -ForegroundColor Yellow
if ($signature.SignerCertificate) {
    Write-Host "Subject: $($signature.SignerCertificate.Subject)" -ForegroundColor DarkGray
}

if ($RequireValid -and $signature.Status -ne "Valid") {
    throw "Code-signing validation failed. Expected Status=Valid but got Status=$($signature.Status)."
}

if ($signature.Status -eq "Valid") {
    Write-Host "OK: Installer signature is valid." -ForegroundColor Green
}
else {
    Write-Host "WARNING: Installer signature is not valid for production rollout." -ForegroundColor DarkYellow
}
