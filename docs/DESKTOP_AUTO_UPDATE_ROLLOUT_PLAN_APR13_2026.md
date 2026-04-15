# Desktop Auto-Update Rollout Plan (Electron) - April 13, 2026

## Status Snapshot (Updated: Apr 15, 2026)

Status legend:
- [x] Completed
- [ ] Pending
- [~] In progress / partially validated

### Delivery Progress
- [x] Electron shell + updater architecture implemented.
- [x] Backend launch from Electron implemented.
- [x] Mandatory updater flow implemented (download progress + install and restart).
- [x] Release publishing scripts implemented and hardened.
- [x] Releases v0.1.0 through v0.1.4 published with updater assets.
- [x] Runtime version-badge fix rolled out in v0.1.4 with backend/frontend asset sync.

### Open Rollout Gaps
- [~] Clean-profile E2E validation recorded for latest candidate release (detection/download evidence captured; final interactive install-restart proof pending).
- [ ] Rollback drill execution evidence captured and documented.
- [ ] Code-signing setup for client-wide rollout.
- [~] Final handover bundle completion (final review and sign-off pending).
- [x] Plan text cleanup aligned to mandatory-update behavior and current version line.

## 1) Goal
Deliver a handover-ready desktop application with automatic update detection and install flow, so client users do not need manual EXE sharing for every release.

## 2) Success Criteria for Handover
1. User installs desktop app once.
2. App checks for new versions on startup.
3. If update exists, app shows popup with:
   - version number
   - release notes/changelog
   - action: Download Update (mandatory flow, no defer option)
4. App downloads update and installs on restart.
5. Team can publish new version remotely and clients receive it automatically.

## 3) Scope
### In Scope (Must Have)
- Electron shell around existing app.
- Existing backend process launched from Electron main process.
- Existing frontend rendered inside Electron window.
- Auto-update pipeline with release notes.
- One complete end-to-end test: v1.0.0 -> v1.0.1.
- Handover runbook for publishing future updates.

### Out of Scope (For Later)
- AI recommendations/chat improvements.
- Deep refactor of scientific processing.
- Full staged rollout automation (can be manual first).
- Delta patch optimization.

## 4) High-Level Architecture

### 4.1 Components
1. Electron Main Process
   - Starts desktop lifecycle.
   - Spawns Python backend process.
   - Manages update checks and install flow.
2. Python Backend (existing FastAPI desktop executable)
   - Handles API and data processing.
   - Serves analysis logic and local data access.
3. Frontend Renderer
   - UI loaded in Electron window.
   - Talks to local backend endpoint.
4. Update Provider (GitHub Releases, S3, or HTTPS server)
   - Hosts installer artifacts and update metadata.
   - Hosts release notes text.

### 4.2 Runtime Flow
1. User opens app.
2. Electron launches backend process and waits for health response.
3. Electron opens renderer window.
4. Updater checks remote release metadata.
5. If newer version found, show update dialog with changelog.
6. If user accepts, download update package.
7. When ready, prompt install/restart.
8. App restarts on new version.

## 5) Technology Decisions
1. Desktop shell: Electron.
2. Build/packaging: electron-builder.
3. Update library: electron-updater.
4. Release host (initial fast path): GitHub Releases (private/public based on client access model).
5. Signing:
   - Initial internal pilot: unsigned acceptable for testing.
   - Client handover target: code signing certificate strongly recommended.

## 6) Repo Implementation Plan

### 6.1 New Folder Structure
Create:
- electron/
  - main.js
  - preload.js
  - updater.js
  - constants.js
- electron-builder.yml
- scripts/
  - release-notes-template.md
  - publish-release.ps1

### 6.2 Main Process Responsibilities
main.js should:
1. Resolve app directories.
2. Start backend executable as child process.
3. Poll backend health endpoint (timeout + retries).
4. Create BrowserWindow.
5. Load frontend URL (local backend route or static file route).
6. Hook updater events and dispatch dialogs.
7. Handle graceful shutdown (kill backend child process).

### 6.3 Updater Module Responsibilities
updater.js should:
1. Configure update feed provider.
2. On app ready, call checkForUpdates.
3. Listen to events:
   - update-available
   - update-not-available
   - download-progress
   - update-downloaded
   - error
4. Fetch release notes and show in popup.
5. Provide actions:
   - Download Update
   - Install and restart

### 6.4 Backend Integration
Use existing desktop backend EXE path first (do not rewrite backend):
1. Build backend EXE from existing PyInstaller pipeline.
2. Package backend EXE inside Electron resources or as external binary included by builder.
3. Use fixed localhost port with fallback strategy.
4. Health check endpoint required before loading UI.

### 6.5 Frontend Integration
1. Keep existing frontend behavior.
2. Ensure API base URL points to local backend port during desktop runtime.
3. Validate login, upload, processing screens in Electron renderer.

## 7) Release and Update Pipeline

### 7.1 Versioning Rules
Use semantic versioning:
- MAJOR.MINOR.PATCH
Examples:
- 1.0.0 initial handover
- 1.0.1 bug fix
- 1.1.0 new feature release

### 7.2 Release Artifact Set
Every release publishes:
1. Installer EXE
2. Update metadata file (generated by electron-builder)
3. Release notes markdown/text

### 7.3 Publish Workflow (Manual First)
1. Bump version in desktop package config.
2. Build release artifacts.
3. Upload artifacts to release host.
4. Publish release notes.
5. Smoke test update path from previous version.

## 8) Tonight Execution Plan (Detailed)

### Phase A - Baseline (60-90 min) [x]
1. Create Electron scaffold files.
2. Configure electron-builder for Windows target.
3. Add npm scripts:
   - desktop:dev
   - desktop:build
   - desktop:dist
4. Confirm app window opens.

### Phase B - Backend Wiring (60-120 min) [x]
1. Start backend child process from Electron.
2. Implement health poll/retry.
3. Add robust logs for startup failures.
4. Validate app works with backend in Electron.

### Phase C - Updater Wiring (90-150 min) [x]
1. Integrate electron-updater.
2. Add update dialogs and release notes rendering.
3. Configure provider feed URL.
4. Build and publish test release v1.0.0.

### Phase D - E2E Update Test (60-90 min) [~]
1. Install v1.0.0 on clean machine/profile.
2. Publish v1.0.1 with visible small UI change.
3. Launch app and confirm update popup.
4. Download, install, restart.
5. Verify changed behavior is present.

### Phase E - Handover Docs (45-60 min) [~]
1. Publish runbook for release process.
2. Add troubleshooting notes.
3. Add rollback steps.
4. Share known limitations list.

## 9) QA Test Checklist

### 9.1 Functional
1. [x] App starts backend reliably.
2. [x] UI loads without blank screen.
3. [~] Upload and processing still work (smoke-tested only in desktop mode; full regression pending).
4. [x] Update check triggers at startup.
5. [x] Update popup shows correct version and notes.
6. [x] Update downloads successfully.
7. [x] Install-and-restart moves to new version.

### 9.2 Resilience
1. [~] No internet during check -> app continues normally (proxy-based simulation run; deterministic offline assertion still pending).
2. [ ] Corrupt download -> user gets safe retry message.
3. [x] Backend start failure -> user sees actionable message.
4. [~] Update server unreachable -> no crash (initial simulation inconclusive; controlled firewall test pending).

## 10) Rollback Plan
If new release is bad:
1. Unpublish or mark release as draft/pre-release.
2. Publish hotfix release with higher patch version.
3. Communicate rollback advisory in release notes.
4. Keep previous stable installer available.

## 11) Security and Compliance Notes
1. [ ] Sign release binaries before client-wide rollout.
2. [ ] Verify update artifacts with built-in signature checks.
3. [x] Keep update channel HTTPS-only.
4. [~] Do not embed sensitive secrets in desktop package (design intent enforced; periodic secret scan still recommended).

## 12) Handover Package Content
1. [x] Desktop installer (current stable).
2. [x] Release notes for current version.
3. [x] One-page user update behavior guide.
4. [x] Internal release runbook for your team.
5. [x] Known issues and mitigations.

## 13) Risks and Mitigations
1. Risk: Electron migration takes longer than expected.
   - Mitigation: Keep strict MVP scope; no AI features now.
2. Risk: Auto-update blocked by signing/trust warnings.
   - Mitigation: Pilot unsigned internally, then sign before broad client rollout.
3. Risk: Backend process race on startup.
   - Mitigation: health polling + timeout + retry + clear error dialog.
4. Risk: Last-minute packaging incompatibility.
   - Mitigation: do first full release test early tonight.

## 14) Immediate Next Actions (Start Now)
1. [x] Create Electron scaffolding in repo.
2. [x] Wire backend child-process startup.
3. [x] Add updater module with provider config.
4. [x] Build first installer and run on clean environment.
5. [~] Publish test update and validate end-to-end update flow (core path complete; final clean-profile evidence pass pending for latest candidate).

---

Owner note:
This plan intentionally prioritizes an update-ready handover build over feature expansion. Complete this first, then resume AI feature work in a separate phase.
