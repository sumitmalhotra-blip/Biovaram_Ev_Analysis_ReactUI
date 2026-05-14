param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$ArtifactsDir = "dist-electron"
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

function Get-YamlScalarValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Content,
        [Parameter(Mandatory = $true)]
        [string]$Key
    )

    $match = [regex]::Match($Content, "(?m)^${Key}:\s*([^\r\n]+)\s*$")
    if (-not $match.Success) {
        return $null
    }

    return $match.Groups[1].Value.Trim().Trim("'").Trim('"')
}

Write-Host "Validating release artifacts for v$Version" -ForegroundColor Yellow

$backendExe = Join-Path $ProjectRoot "dist/BioVaram/BioVaram.exe"
$frontendIndex = Join-Path $ProjectRoot "out/index.html"
$installerExe = Join-Path $ProjectRoot "$ArtifactsDir/BioVaram-Setup-$Version.exe"
$installerMsi = Join-Path $ProjectRoot "$ArtifactsDir/BioVaram-Setup-$Version.msi"
$latestYml = Join-Path $ProjectRoot "$ArtifactsDir/latest.yml"
$installerBlockmap = Join-Path $ProjectRoot "$ArtifactsDir/BioVaram-Setup-$Version.exe.blockmap"

Assert-Exists -Path $backendExe -Label "Backend desktop binary"
Assert-Exists -Path $frontendIndex -Label "Frontend static export"
Assert-Exists -Path $installerExe -Label "Electron installer"
Assert-Exists -Path $installerMsi -Label "MSI installer"
Assert-Exists -Path $latestYml -Label "Updater metadata (latest.yml)"

$latestYmlContent = Get-Content $latestYml -Raw
$latestVersion = Get-YamlScalarValue -Content $latestYmlContent -Key "version"
if (-not $latestVersion) {
    throw "Could not read version from latest.yml"
}
if ($latestVersion -ne $Version) {
    throw "latest.yml version mismatch. Expected $Version but found $latestVersion"
}

$latestPath = Get-YamlScalarValue -Content $latestYmlContent -Key "path"
$expectedInstaller = "BioVaram-Setup-$Version.exe"
if ($latestPath -and $latestPath -ne $expectedInstaller) {
    throw "latest.yml path mismatch. Expected $expectedInstaller but found $latestPath"
}

if (Test-Path $installerBlockmap) {
    Write-Host "OK: Installer blockmap" -ForegroundColor Green
}
else {
    Write-Host "WARN: Installer blockmap not found (expected when nsis.differentialPackage is disabled)." -ForegroundColor DarkYellow
}

Write-Host "All required rollout artifacts are present for v$Version." -ForegroundColor Green
