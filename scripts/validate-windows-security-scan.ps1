param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$ArtifactsDir = "",
    [switch]$RequireDefender,
    [switch]$RequireClean
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $ArtifactsDir) {
    $ArtifactsDir = "dist-electron-$Version"
}

$artifacts = @(
    (Join-Path $ProjectRoot "$ArtifactsDir/BioVaram-Setup-$Version.exe"),
    (Join-Path $ProjectRoot "$ArtifactsDir/BioVaram-Setup-$Version.msi")
)

foreach ($artifact in $artifacts) {
    if (-not (Test-Path $artifact)) {
        throw "Release artifact not found for malware scan: $artifact"
    }
}

$mpCmdCandidates = @(
    "$env:ProgramFiles\Windows Defender\MpCmdRun.exe",
    "$env:ProgramFiles\Microsoft Defender\MpCmdRun.exe",
    "$env:ProgramFiles(x86)\Windows Defender\MpCmdRun.exe"
) | Select-Object -Unique

$mpCmdRun = $mpCmdCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if (-not $mpCmdRun) {
    if ($RequireDefender) {
        throw "Microsoft Defender CLI (MpCmdRun.exe) was not found. Install/enable Defender before release."
    }

    Write-Host "WARNING: Defender CLI not found. Skipping malware scan." -ForegroundColor DarkYellow
    return
}

Write-Host "Using Defender CLI: $mpCmdRun" -ForegroundColor DarkGray

foreach ($artifact in $artifacts) {
    $hash = Get-FileHash -Algorithm SHA256 -Path $artifact
    Write-Host "SHA256 $($hash.Path): $($hash.Hash)" -ForegroundColor DarkGray

    Write-Host "Scanning artifact with Microsoft Defender: $artifact" -ForegroundColor Yellow
    & $mpCmdRun -Scan -ScanType 3 -File $artifact
    $scanExitCode = $LASTEXITCODE

    if ($scanExitCode -ne 0) {
        $message = "Defender scan returned exit code $scanExitCode for $artifact"
        if ($RequireClean) {
            throw $message
        }
        Write-Host "WARNING: $message" -ForegroundColor DarkYellow
        continue
    }

    Write-Host "OK: Defender scan completed without detection for $artifact" -ForegroundColor Green
}
