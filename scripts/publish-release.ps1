param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [switch]$BuildBackend,
    [switch]$SkipBuild,
    [switch]$SkipValidate,
    [string]$ReleaseNotesPath = "scripts/release-notes-template.md"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Required command not found: git"
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "Required command not found: npm.cmd"
}

if (-not $env:GITHUB_TOKEN) {
    throw "GITHUB_TOKEN is required for publishing updates to GitHub Releases."
}

if (-not (Test-Path $ReleaseNotesPath)) {
    throw "Release notes file not found: $ReleaseNotesPath"
}

Write-Host "[1/7] Updating app version to $Version" -ForegroundColor Yellow
npm.cmd version $Version --no-git-tag-version | Out-Null

if ($BuildBackend) {
    Write-Host "[2/6] Building backend desktop executable" -ForegroundColor Yellow
    & "$ProjectRoot\packaging\build.ps1" -SkipFrontend -Version $Version
}
else {
    Write-Host "[2/6] Skipping backend build (use -BuildBackend to include it)" -ForegroundColor DarkGray
}

if (-not $SkipBuild) {
    Write-Host "[3/6] Building static frontend" -ForegroundColor Yellow
    npm.cmd run build
}
else {
    Write-Host "[3/6] Skipping frontend build" -ForegroundColor DarkGray
}

if (-not (Test-Path "$ProjectRoot\dist\BioVaram\BioVaram.exe")) {
    throw "Missing backend binary: dist/BioVaram/BioVaram.exe"
}
if (-not (Test-Path "$ProjectRoot\out\index.html")) {
    throw "Missing static frontend output: out/index.html"
}

Write-Host "[4/7] Building Electron installer and publishing update artifacts" -ForegroundColor Yellow
npm.cmd run desktop:dist:publish

if (-not $SkipValidate) {
    Write-Host "[5/7] Validating published release artifacts" -ForegroundColor Yellow
    & "$ProjectRoot\scripts\validate-release-artifacts.ps1" -Version $Version
}
else {
    Write-Host "[5/7] Skipping post-build artifact validation" -ForegroundColor DarkGray
}

Write-Host "[6/7] Creating git commit and tag" -ForegroundColor Yellow
git add package.json package-lock.json
git commit -m "release: v$Version" | Out-Null
git tag "v$Version"

Write-Host "[7/7] Pushing commit/tag and publishing release" -ForegroundColor Yellow
git push
git push origin "v$Version"

Write-Host "Release build complete. Upload release notes from: $ReleaseNotesPath" -ForegroundColor Green
Write-Host "Artifacts directory: dist-electron" -ForegroundColor Green
