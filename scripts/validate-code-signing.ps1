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
$msiPath = Join-Path $ProjectRoot "$ArtifactsDir/BioVaram-Setup-$Version.msi"
$pathsToValidate = @($installerPath, $msiPath)

foreach ($path in $pathsToValidate) {
    if (-not (Test-Path $path)) {
        throw "Release artifact not found for signature validation: $path"
    }

    $signature = Get-AuthenticodeSignature $path

    Write-Host "Signature validation for: $path" -ForegroundColor Yellow
    Write-Host "Status: $($signature.Status)" -ForegroundColor Yellow
    if ($signature.SignerCertificate) {
        Write-Host "Subject: $($signature.SignerCertificate.Subject)" -ForegroundColor DarkGray
    }

    if ($RequireValid -and $signature.Status -ne "Valid") {
        throw "Code-signing validation failed for $path. Expected Status=Valid but got Status=$($signature.Status)."
    }

    if ($signature.Status -eq "Valid") {
        Write-Host "OK: Signature is valid." -ForegroundColor Green
    }
    else {
        Write-Host "WARNING: Signature is not valid for production rollout." -ForegroundColor DarkYellow
    }
}
