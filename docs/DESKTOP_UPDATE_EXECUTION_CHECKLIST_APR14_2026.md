# Desktop Update Rollout - Execution Checklist (Apr 14, 2026)

## Status
- Electron scaffold: completed
- Backend launch from Electron: completed
- Updater module wiring: completed
- Release notes popup support: completed
- Release helper scripts: completed

## Remaining Steps to Complete

Use this checklist together with:
- docs/DESKTOP_ROLLOUT_EXECUTION_RUNBOOK_APR14_2026.md

### 1. Build artifacts
1. Build backend desktop executable:
   powershell -ExecutionPolicy Bypass -File packaging/build.ps1 -SkipFrontend -Version 1.0.0
2. Build static frontend export:
   npm.cmd run build
3. Build Electron installer and update artifacts:
   npm.cmd run desktop:dist
4. Validate release artifacts:
   powershell -ExecutionPolicy Bypass -File scripts/validate-release-artifacts.ps1 -Version 1.0.0

### 2. First release publish (v1.0.0)
1. Ensure GITHUB_TOKEN is set in terminal environment.
2. Prepare release notes using scripts/release-notes-template.md.
3. Run:
   powershell -ExecutionPolicy Bypass -File scripts/publish-release.ps1 -Version 1.0.0
4. Confirm release contains installer and update metadata files.

### 3. Update simulation release (v1.0.1)
1. Make a visible small UI change for verification.
2. Update release notes.
3. Run:
   powershell -ExecutionPolicy Bypass -File scripts/publish-release.ps1 -Version 1.0.1

### 4. End-to-end update test
1. Install v1.0.0 on clean machine/profile.
2. Launch app and confirm normal behavior.
3. Launch again after v1.0.1 publish.
4. Confirm update popup displays release notes.
5. Click Download Update.
6. After download, click Install and Restart.
7. Verify app opens with v1.0.1 behavior.

### 5. Handover package
1. Installer for stable version.
2. Published release notes.
3. One-page user guide: how update popup works.
4. Internal runbook for future release process.
5. Known issues list (if any).

## Go/No-Go Gate
Release is handover-ready only if all are true:
1. Backend starts from Electron without manual command.
2. Update popup appears for newer version.
3. Release notes are shown in popup.
4. Install-and-restart applies update successfully.
5. No blocking error during startup or update flow.

## Exact Next Steps (Execution Order)
1. Complete Phase 1 in docs/DESKTOP_ROLLOUT_EXECUTION_RUNBOOK_APR14_2026.md.
2. Publish v1.0.0 and verify assets on GitHub Releases.
3. Execute v1.0.0 -> v1.0.1 update simulation.
4. Record pass/fail evidence for every gate above.
5. Proceed to client rollout only after all gates are green.
