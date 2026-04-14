# Desktop Rollout Execution Runbook (Apr 14, 2026)

## Objective
Move from "desktop build works locally" to "repeatable release + updater rollout" with measurable go/no-go criteria.

## Phase 1 - Release Baseline (Today)
1. Build backend desktop binary:
   - `powershell -ExecutionPolicy Bypass -File packaging/build.ps1 -SkipFrontend -Version 0.1.0`
2. Build frontend static export:
   - `npm.cmd run build`
3. Build desktop installer + updater artifacts:
   - `npm.cmd run desktop:dist`
4. Validate artifacts:
   - `powershell -ExecutionPolicy Bypass -File scripts/validate-release-artifacts.ps1 -Version 0.1.0`

### Exit Criteria
1. `dist/BioVaram/BioVaram.exe` exists.
2. `out/index.html` exists.
3. `dist-electron/BioVaram-Setup-0.1.0.exe` exists.
4. `dist-electron/latest.yml` exists.
5. `dist-electron/BioVaram-Setup-0.1.0.exe.blockmap` exists.

## Phase 2 - Publish Stable Baseline (v0.1.0)
1. Export token for release publish:
   - `$env:GITHUB_TOKEN = "<token>"`
2. Publish release with notes:
   - `powershell -ExecutionPolicy Bypass -File scripts/publish-release.ps1 -Version 0.1.0`
3. Confirm release assets are visible in GitHub release page:
   - installer exe
   - blockmap
   - latest.yml

### Exit Criteria
1. GitHub release `v0.1.0` exists.
2. All updater artifacts are downloadable over HTTPS.

## Phase 3 - Real Update Test (v0.1.0 -> v0.1.1)
1. Install v0.1.0 on clean machine/profile.
2. Make visible UI marker change for v0.1.1.
3. Build and validate v0.1.1 artifacts.
4. Publish v0.1.1 via `publish-release.ps1`.
5. Launch v0.1.0 and verify:
   - update popup shown
   - release notes shown
   - download succeeds
   - install and restart succeeds

### Exit Criteria
1. App self-updates from v0.1.0 to v0.1.1 without manual reinstall.
2. Updated UI marker is visible after restart.

## Phase 4 - Rollout Hardening
1. Signing:
   - move from unsigned internal build to signed installer/app for client delivery.
2. Observability:
   - collect updater and backend startup logs from at least 3 test runs.
3. Rollback drill:
   - simulate bad release and confirm rollback procedure works.

### Exit Criteria
1. Signed artifacts available.
2. Rollback instructions tested once.
3. No P0 startup/update blockers.

## Go/No-Go Gate (Client Rollout)
All must be true:
1. Backend starts from packaged app reliably.
2. Updater detects new version on startup.
3. Update download/install/restart succeeds.
4. Release artifacts are reproducible with the documented commands.
5. Rollback path is tested and documented.

## Ownership
1. Packaging + release publish: Desktop owner
2. Updater hosting/permissions: DevOps owner
3. Sign certificate + renewal: Platform owner
4. Final go/no-go decision: Release manager
