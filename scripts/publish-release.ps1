param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [switch]$BuildBackend,
    [switch]$RequireSigning,
    [switch]$SkipBuild,
    [switch]$SkipValidate,
    [string]$ElectronOutputDir = "",
    [string]$ReleaseNotesPath = "scripts/release-notes-template.md"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $ElectronOutputDir) {
    $ElectronOutputDir = "dist-electron-$Version"
}

function Assert-LastExitCode {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Step
    )

    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

function Test-SigningProvisioned {
    # electron-builder supports these env vars for Windows signing discovery.
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

function Stop-LockingDesktopProcesses {
    # Ensure no running desktop/build processes keep app.asar locked.
    $processNames = @("BioVaram", "electron", "app-builder", "electron-builder")
    foreach ($name in $processNames) {
        Get-Process -Name $name -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    }

    $winUnpackedPath = (Join-Path $ProjectRoot "$ElectronOutputDir\win-unpacked").ToLowerInvariant()
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -and $_.ExecutablePath.ToLowerInvariant().StartsWith($winUnpackedPath) } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Clear-ElectronOutput {
    $electronOutputPath = Join-Path $ProjectRoot $ElectronOutputDir
    if (Test-Path $electronOutputPath) {
        try {
            Remove-Item $electronOutputPath -Recurse -Force -ErrorAction Stop
        }
        catch {
            Write-Host "Could not fully clear $ElectronOutputDir (likely file lock). Continuing with retry flow..." -ForegroundColor DarkYellow
        }
    }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Required command not found: git"
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "Required command not found: npm.cmd"
}
if (-not (Get-Command npx.cmd -ErrorAction SilentlyContinue)) {
    throw "Required command not found: npx.cmd"
}

if (-not $env:GITHUB_TOKEN) {
    throw "GITHUB_TOKEN is required for publishing updates to GitHub Releases."
}

if (-not (Test-Path $ReleaseNotesPath)) {
    throw "Release notes file not found: $ReleaseNotesPath"
}

if ($RequireSigning -and -not (Test-SigningProvisioned)) {
    throw "RequireSigning was set, but no signing configuration was found. Set WIN_CSC_LINK/WIN_CSC_KEY_PASSWORD or CSC_LINK/CSC_KEY_PASSWORD or CSC_NAME."
}

$frontendBuiltByBackend = $false

Write-Host "[1/7] Updating app version to $Version" -ForegroundColor Yellow
npm.cmd version $Version --no-git-tag-version | Out-Null
if ($LASTEXITCODE -ne 0) {
    $currentVersion = (Get-Content "$ProjectRoot\package.json" -Raw | ConvertFrom-Json).version
    if ($currentVersion -eq $Version) {
        Write-Host "Version already set to $Version, continuing." -ForegroundColor DarkGray
    }
    else {
        throw "Failed to set package version to $Version"
    }
}

if ($BuildBackend) {
    Write-Host "[2/6] Building backend desktop executable" -ForegroundColor Yellow
    # Build backend with bundled frontend to keep in-app UI assets in sync.
    & "$ProjectRoot\packaging\build.ps1" -Version $Version
    Assert-LastExitCode -Step "Backend desktop build"
    $frontendBuiltByBackend = $true
}
else {
    Write-Host "[2/6] Skipping backend build (use -BuildBackend to include it)" -ForegroundColor DarkGray
}

if (-not $SkipBuild -and -not $frontendBuiltByBackend) {
    Write-Host "[3/6] Building static frontend" -ForegroundColor Yellow
    npm.cmd run build
    Assert-LastExitCode -Step "Frontend build"
}
elseif ($frontendBuiltByBackend) {
    Write-Host "[3/6] Skipping standalone frontend build (already built during backend packaging)" -ForegroundColor DarkGray
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
Stop-LockingDesktopProcesses
Clear-ElectronOutput

$publishAttempts = 0
$maxPublishAttempts = 2
do {
    $publishAttempts++
    npx.cmd electron-builder --win nsis --publish always --config.directories.output=$ElectronOutputDir
    if ($LASTEXITCODE -eq 0) {
        break
    }

    if ($publishAttempts -ge $maxPublishAttempts) {
        Assert-LastExitCode -Step "Electron packaging/publish"
    }

    Write-Host "Electron packaging failed (attempt $publishAttempts/$maxPublishAttempts). Retrying after cleanup..." -ForegroundColor DarkYellow
    Stop-LockingDesktopProcesses
    Clear-ElectronOutput
} while ($true)

if (-not $SkipValidate) {
    Write-Host "[5/7] Validating published release artifacts" -ForegroundColor Yellow
    & "$ProjectRoot\scripts\validate-release-artifacts.ps1" -Version $Version -ArtifactsDir $ElectronOutputDir

    if ($RequireSigning) {
        Write-Host "[5/7] Validating code signature" -ForegroundColor Yellow
        & "$ProjectRoot\scripts\validate-code-signing.ps1" -Version $Version -ArtifactsDir $ElectronOutputDir -RequireValid
    }
}
else {
    Write-Host "[5/7] Skipping post-build artifact validation" -ForegroundColor DarkGray
}

Write-Host "[6/7] Creating git commit and tag" -ForegroundColor Yellow
git add package.json package-lock.json
git commit -m "release: v$Version" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "No version file changes to commit for release v$Version." -ForegroundColor DarkGray
}
git tag "v$Version"
Assert-LastExitCode -Step "Tag creation"

Write-Host "[7/7] Pushing commit/tag and publishing release" -ForegroundColor Yellow
git push
Assert-LastExitCode -Step "Git push (branch)"
git push origin "v$Version"
Assert-LastExitCode -Step "Git push (tag)"

Write-Host "Release build complete. Upload release notes from: $ReleaseNotesPath" -ForegroundColor Green
Write-Host "Artifacts directory: $ElectronOutputDir" -ForegroundColor Green
