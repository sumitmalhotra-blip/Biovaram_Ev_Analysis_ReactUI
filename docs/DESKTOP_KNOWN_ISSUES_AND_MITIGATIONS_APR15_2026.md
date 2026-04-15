# Desktop Known Issues and Mitigations (Apr 15, 2026)

## Scope
Production rollout known issues for desktop updater and startup lifecycle.

## Issue 1: Release may be created as draft/untagged by initial publish
Impact:
- Clients do not receive updates from latest channel until release is published.
Mitigation:
1. Run release finalization immediately after publish.
2. Verify release is non-draft and has required assets.
3. Required assets:
   - BioVaram-Setup-<version>.exe
   - BioVaram-Setup-<version>.exe.blockmap
   - latest.yml

## Issue 2: Frontend assets can become stale if backend bundle is not rebuilt
Impact:
- UI may show old behavior/version labels despite newer installer version.
Mitigation:
1. Use publish pipeline with backend rebuild for production cutovers.
2. Ensure backend packaging includes latest frontend export.
3. Validate runtime UI version marker after install.

## Issue 3: Backend startup failure due local environment conflicts (port/dependency)
Impact:
- App startup fails before backend health is achieved.
Mitigation:
1. Startup failure dialog now surfaces backend stderr/exit context.
2. Retry after freeing conflicting local services.
3. If persistent, reinstall latest stable installer.

## Issue 4: Update download interruptions/unreachable provider
Impact:
- Update does not complete in-session.
Mitigation:
1. App should remain usable on current version.
2. Relaunch app and retry update flow.
3. Validate release host availability and artifact presence.

## Pre-Release Verification Checklist
1. Installer launches and backend health is green.
2. Update check detects next version.
3. Download + install + restart path completes.
4. Header/version marker reflects released version.
5. Release is published (not draft) with all required assets.

## Operational Recommendation
1. Keep one prior stable installer available for fallback.
2. Perform one controlled rollout test machine before broad distribution.
3. Rotate exposed PAT tokens immediately if shared in chat/logs.
