# Desktop Update Rollout Task Status (Dedicated Tracker)

Date: 2026-04-15
Owner: BioVaram / CRM IT
Purpose: Single source of truth for update-rollout tasks and completion status.

Status legend:
- [x] Completed
- [~] In progress / partially completed
- [ ] Pending

## 1) Build and Architecture

- [x] Electron shell scaffolding implemented.
- [x] Backend launch from Electron implemented.
- [x] Backend health polling and startup failure handling implemented.
- [x] Frontend loaded in Electron runtime.
- [x] Graceful app shutdown with backend process termination implemented.

## 2) Updater Flow

- [x] electron-updater integration implemented.
- [x] Startup update check implemented.
- [x] Mandatory update path implemented (no defer).
- [x] Download progress visibility implemented.
- [x] Install-and-restart flow implemented.
- [x] Updater error dialogs/actionable messaging implemented.
- [x] Previous update attempt/failure check on startup implemented.

## 3) Release Notes and UX Reliability

- [x] Runtime version badge source fixed to app runtime version.
- [x] Renderer cache freshness/version transition handling implemented.
- [x] Release notes fallback for empty notes implemented.
- [x] Release notes sanitizer hardened for malformed HTML artifacts.
- [x] Newline artifact normalization added (including <code>n</code> and escaped \\n).
- [x] Bug Report top menu entry added and linked to form.

## 4) Build and Publish Pipeline

- [x] Release publish script implemented.
- [x] Release finalization script implemented.
- [x] Artifact validation script implemented.
- [x] Required updater artifacts validated in pipeline (.exe, .blockmap, latest.yml).
- [x] Draft-release handling and final publish safeguards added.
- [x] Backend packaging dependency fallback (pnpm -> npm) added.
- [x] Backend/frontend sync path for packaged desktop release build hardened.

## 5) Release Execution Status

- [x] v0.1.0 published with updater assets.
- [x] v0.1.1 published with updater assets.
- [x] v0.1.2 published with updater assets.
- [x] v0.1.3 published with updater assets.
- [x] v0.1.4 published with updater assets.
- [x] v0.1.5 published with updater assets.
- [x] v0.1.6 published with updater assets.
- [x] v0.1.7 published (draft resolved) with required assets and cleaned bullet release notes.

## 6) Validation and QA

### Functional
- [x] App starts backend reliably.
- [x] UI loads in desktop shell.
- [x] Update check triggers at startup.
- [x] Update popup shows version and notes.
- [x] Update download path validated.
- [x] Install-and-restart path validated in rollout iterations.
- [x] Full regression automation pass completed (perf:gates + uat-evidence Playwright suites).

### Resilience
- [x] Backend startup failure behavior validated (port conflict style test).
- [x] No-internet / provider-unreachable deterministic validation completed (controlled fault-injection evidence captured).
- [x] Corrupt download controlled validation completed (safe error handling evidence captured).
- [x] Formal rollback drill evidence captured (state mismatch recovery path validated).

## 7) Security and Rollout Governance

- [x] HTTPS update channel usage in place.
- [~] Code-signing pipeline hardened with strict gates (RequireSigning + signature validation scripts).
- [ ] Production certificate provisioning and signed artifact generation pending external credential/certificate availability.
- [~] Secret hygiene intention in place; periodic automated scan/sign-off pending.

## 8) Handover Package

- [x] Desktop installer available.
- [x] Release notes process and templates available.
- [x] User update behavior guide created.
- [x] Internal release runbook/scripts available.
- [x] Known issues and mitigations documentation created.
- [x] Final sign-off package assembled for internal-client test rollout.

## Internal Rollout Decision (Apr 15, 2026)

- Internal client real-environment testing: GO (unsigned build accepted for controlled internal use).
- Public/global production rollout: NO-GO until code signing is completed.

## 9) Remaining Tasks to Close Update Rollout

1. [x] Run and document deterministic unreachable-provider test (firewall or host block), confirm app remains usable.
2. [x] Run and document controlled corrupt-download test, confirm safe retry/error UX.
3. [x] Execute and document rollback drill for a bad release scenario.
4. [x] Complete final full regression pass for desktop upload/processing workflows.
5. [ ] Complete code-signing setup and signed release validation for client-wide rollout.
6. [~] Final public-production closure memo pending code-signing gate.

Completed in this execution wave:
1. [x] Run and document deterministic unreachable-provider test (controlled deterministic fault injection evidence).
2. [x] Run and document controlled corrupt-download test (controlled deterministic fault injection evidence).
3. [x] Execute and document rollback drill for bad-release recovery state path.
4. [x] Complete final full regression pass for desktop automation suites.
5. [x] Add production signing runbook and enforceable pipeline checks (`validate-code-signing.ps1`, `build-signed-candidate.ps1`, `publish-release.ps1 -RequireSigning`).

Blocked in current environment (external prerequisites missing):
1. [ ] Provision production signing certificate (EV/OV) and signing secrets in runtime environment.
2. [ ] Build signed candidate with Authenticode Status=Valid.
3. [ ] Run signed update smoke cycle (install -> update -> restart).
4. [ ] Publish signed release and flip sign-off from conditional NO-GO to GO.

## 10) Recommended Execution Order for Pending Items

1. Provision signing certificate and secrets.
2. Build signed candidate and validate signature.
3. Run signed update smoke cycle.
4. Publish signed release.
5. Update sign-off from internal GO/public NO-GO to full public GO.

---

This tracker is derived from:
- docs/DESKTOP_AUTO_UPDATE_ROLLOUT_PLAN_APR13_2026.md
- docs/DESKTOP_STEP3_STEP4_VALIDATION_APR15_2026.md
- Latest release execution logs through v0.1.7
