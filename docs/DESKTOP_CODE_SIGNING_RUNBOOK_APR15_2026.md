# Desktop Code Signing Runbook (Production)

Date: 2026-04-15
Owner: BioVaram / CRM IT

## 1) Goal

Produce signed Windows installer artifacts so Authenticode status is `Valid` and rollout can move to production-grade trust posture.

## 2) Recommended Certificate

- Recommended: EV code signing certificate (best SmartScreen reputation behavior).
- Minimum acceptable: standard OV code signing certificate (with timestamping).

## 3) Supported Signing Inputs (Current Pipeline)

The release pipeline now supports standard electron-builder signing inputs:

- `WIN_CSC_LINK` + `WIN_CSC_KEY_PASSWORD`
- or `CSC_LINK` + `CSC_KEY_PASSWORD`
- or `CSC_NAME` (certificate in Windows cert store)

## 4) One-Time Provisioning Checklist

1. Acquire production certificate from CA.
2. Export PFX securely (if using file-based cert flow).
3. Store secret values in secure CI secret store or secure local env.
4. Ensure timestamp server access is allowed.
5. Restrict key access to release owners only.

## 5) Local/Runner Configuration Example (PFX)

PowerShell session setup example:

```powershell
$env:WIN_CSC_LINK = "file:///C:/secure/certs/biovaram-signing.pfx"
$env:WIN_CSC_KEY_PASSWORD = "<pfx-password>"
```

Alternative base64/content URL for CI is also supported by electron-builder.

## 6) Signed Release Build Command

```powershell
./scripts/publish-release.ps1 -Version <x.y.z> -BuildBackend -RequireSigning
```

Behavior:
- Fails early if signing config is missing.
- Builds installer and updater artifacts.
- Validates artifacts.
- Validates Authenticode signature (`Status=Valid`) before commit/tag/push.

## 7) Signature Validation Command

```powershell
./scripts/validate-code-signing.ps1 -Version <x.y.z> -ArtifactsDir dist-electron-<x.y.z> -RequireValid
```

## 8) Signed Update Smoke Cycle

1. Install previous signed baseline build.
2. Publish new signed release.
3. Launch app and accept update.
4. Restart to apply update.
5. Validate:
   - app launches normally
   - backend health is OK
   - version updates correctly
   - update notes render correctly

## 9) Release Gate (Must Pass)

All must be true:
- `validate-release-artifacts.ps1` passes
- `validate-code-signing.ps1 -RequireValid` passes
- one update smoke cycle passes

## 10) If Signing Fails

1. Do not publish production rollout.
2. Rotate/reload cert material if expired or inaccessible.
3. Re-run signed build and validation.
4. Keep sign-off package in NO-GO state until signature is valid.
