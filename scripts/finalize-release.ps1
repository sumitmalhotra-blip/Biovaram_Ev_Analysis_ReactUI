param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$Owner = "sumitmalhotra-blip",
    [string]$Repo = "Biovaram_Ev_Analysis_ReactUI",
    [string]$ArtifactsDir = "",
    [switch]$ReplaceExisting
)

$ErrorActionPreference = "Stop"

if (-not $ArtifactsDir) {
    $ArtifactsDir = "dist-electron-$Version"
}

if (-not $env:GITHUB_TOKEN) {
    throw "GITHUB_TOKEN is not set. Export a real PAT with repo scope first."
}

if ($env:GITHUB_TOKEN -eq "YOUR_PAT_WITH_REPO_SCOPE") {
    throw "GITHUB_TOKEN is still the placeholder value. Replace it with a real PAT."
}

$tag = if ($Version.StartsWith("v")) { $Version } else { "v$Version" }
$normalizedVersion = if ($Version.StartsWith("v")) { $Version.Substring(1) } else { $Version }

$headers = @{
    Authorization        = "Bearer $($env:GITHUB_TOKEN)"
    Accept               = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

function Invoke-GitHubJson {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("GET", "POST", "PATCH", "DELETE")]
        [string]$Method,
        [Parameter(Mandatory = $true)]
        [string]$Uri,
        [object]$Body
    )

    if ($null -ne $Body) {
        $payload = $Body | ConvertTo-Json -Depth 10
        return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers -Body $payload -ContentType "application/json"
    }

    return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers
}

function Get-ReleaseByTag {
    param([Parameter(Mandatory = $true)][string]$Tag)

    try {
        return Invoke-GitHubJson -Method GET -Uri "https://api.github.com/repos/$Owner/$Repo/releases/tags/$Tag"
    }
    catch {
        if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 404) {
            $allReleases = Invoke-GitHubJson -Method GET -Uri "https://api.github.com/repos/$Owner/$Repo/releases?per_page=100"
            return $allReleases | Where-Object { $_.tag_name -eq $Tag } | Select-Object -First 1
        }
        throw
    }
}

if (-not (Test-Path $ArtifactsDir)) {
    throw "Artifacts directory not found: $ArtifactsDir"
}

$requiredFiles = @(
    "BioVaram-Setup-$normalizedVersion.exe",
    "BioVaram-Setup-$normalizedVersion.exe.blockmap",
    "latest.yml"
)

foreach ($file in $requiredFiles) {
    $filePath = Join-Path $ArtifactsDir $file
    if (-not (Test-Path $filePath)) {
        throw "Required artifact missing: $filePath"
    }
}

Write-Host "Resolving release for $tag..." -ForegroundColor Yellow
$release = Get-ReleaseByTag -Tag $tag

if (-not $release) {
    Write-Host "Release not found, creating published release for $tag..." -ForegroundColor Yellow
    $release = Invoke-GitHubJson -Method POST -Uri "https://api.github.com/repos/$Owner/$Repo/releases" -Body @{
        tag_name   = $tag
        name       = $tag
        draft      = $false
        prerelease = $false
    }
}

if ($release.draft) {
    Write-Host "Release is draft. Publishing it..." -ForegroundColor Yellow
    $release = Invoke-GitHubJson -Method PATCH -Uri "https://api.github.com/repos/$Owner/$Repo/releases/$($release.id)" -Body @{
        draft      = $false
        prerelease = $false
        name       = $tag
    }
}

$uploadBase = ($release.upload_url -replace '\{\?name,label\}$', '')
if (-not $uploadBase) {
    throw "Could not resolve upload URL from release object."
}

$assets = @($release.assets)

foreach ($name in $requiredFiles) {
    $path = Join-Path $ArtifactsDir $name
    $existing = $assets | Where-Object { $_.name -eq $name } | Select-Object -First 1

    if ($existing -and -not $ReplaceExisting) {
        Write-Host "Asset already exists, skipping: $name" -ForegroundColor DarkGray
        continue
    }

    if ($existing -and $ReplaceExisting) {
        Write-Host "Deleting existing asset before upload: $name" -ForegroundColor DarkYellow
        Invoke-GitHubJson -Method DELETE -Uri "https://api.github.com/repos/$Owner/$Repo/releases/assets/$($existing.id)"
    }

    Write-Host "Uploading asset: $name" -ForegroundColor Yellow
    Invoke-RestMethod -Method POST -Uri "$uploadBase?name=$name" -Headers @{
        Authorization = "Bearer $($env:GITHUB_TOKEN)"
        Accept        = "application/vnd.github+json"
        "Content-Type" = "application/octet-stream"
    } -InFile $path | Out-Null
}

$finalRelease = Invoke-GitHubJson -Method GET -Uri "https://api.github.com/repos/$Owner/$Repo/releases/$($release.id)"
$finalAssetNames = @($finalRelease.assets | ForEach-Object { $_.name })

$missing = @()
foreach ($expected in $requiredFiles) {
    if ($finalAssetNames -notcontains $expected) {
        $missing += $expected
    }
}

if ($finalRelease.draft) {
    throw "Release is still draft after update: $($finalRelease.html_url)"
}

if ($missing.Count -gt 0) {
    throw "Release is missing required assets: $($missing -join ', ')"
}

Write-Host "Release finalized successfully:" -ForegroundColor Green
Write-Host $finalRelease.html_url -ForegroundColor Green
Write-Host "Assets:" -ForegroundColor Green
foreach ($asset in $finalRelease.assets) {
    Write-Host " - $($asset.name)" -ForegroundColor Green
}