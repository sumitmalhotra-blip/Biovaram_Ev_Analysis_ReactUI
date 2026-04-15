# Desktop Diagnostics and Remote Logging Execution Plan (Safe Rollout)

Date: 2026-04-15
Owner: BioVaram / CRM IT
Status: Ready for staged execution

## 1) Goal

Provide reliable, privacy-safe diagnostics for desktop failures (Electron + backend), and optionally deliver failure logs to the support team automatically with user consent.

This plan is designed to be executed later with low operational risk.

## 2) Current Baseline (From Code Audit)

- Backend frozen mode currently redirects stdout/stderr to `%APPDATA%/BioVaram/biovaram.log`.
- Backend log file is opened in overwrite mode on startup, so previous history can be lost.
- Electron main/updater/backend-manager logs are printed to console but not persisted to rotating files.
- No global Electron uncaught exception/unhandled rejection capture is wired.
- No remote telemetry transport is currently configured.

## 3) Safety Principles (Mandatory)

- Do not upload any user data files by default (FCS/NTA/parquet/raw uploads).
- Collect only diagnostics metadata and application logs.
- Require explicit user opt-in for remote submission.
- Redact likely PII before upload (username, local paths, hostnames where possible).
- Keep all new telemetry behind feature flags for staged rollout.
- Maintain full offline behavior if telemetry endpoint is unavailable.

## 4) Architecture Target

### Local diagnostics (always on)

- Electron logs:
  - main process
  - updater lifecycle
  - backend process bridge output
- Backend logs:
  - rotating file logs
  - startup and fatal exception traces
- Crash artifacts:
  - include process crash dumps if available
- Session correlation:
  - generate one `run_id` per app launch and include in all log records

### User support tooling

- Help menu action: `Open Logs Folder`
- Help menu action: `Export Diagnostics Bundle`
- Bundle format: zip with manifest + selected log files + version/build metadata

### Remote diagnostics (opt-in)

- Upload channel options:
  - Option A: Sentry for error telemetry
  - Option B: Custom HTTPS endpoint for zipped diagnostic bundles
- Queue and retry when offline
- Backoff policy and max retry window

## 5) Execution Plan (Phased)

## Phase 1: Local Logging Hardening (Low risk, execute first)

Scope:
- Persist Electron logs to `%APPDATA%/BioVaram/logs/` with rotation.
- Add global exception handlers in Electron main process.
- Change backend frozen log from overwrite to append + rotation strategy.
- Add run metadata header at startup (app version, OS, run_id, timestamp).

Deliverables:
- `main.log`, `updater.log`, `backend-bridge.log`, `backend.log`
- 14-day retention or 50 MB cap (whichever reached first)

Acceptance criteria:
- Simulated backend startup failure appears in local logs with stack/error context.
- Simulated updater failure appears in local logs.
- Logs survive app restart.

Rollback:
- Keep file logger behind `CRMIT_FILE_LOGGING=1` env flag.
- If issues are observed, disable flag and revert to console-only logging.

## Phase 2: Support Diagnostics UX (Low-medium risk)

Scope:
- Add Help menu actions:
  - `Open Logs Folder`
  - `Export Diagnostics Bundle`
- Include manifest JSON in bundle:
  - app version
  - build date
  - OS
  - run_id
  - active feature flags
- Exclude large or sensitive files by allowlist strategy.

Acceptance criteria:
- Export produces zip in user-chosen folder.
- Bundle excludes raw scientific data files.
- Support can reproduce issue timeline using only bundle files.

Rollback:
- Hide export menu entries behind `CRMIT_DIAG_EXPORT=1`.

## Phase 3: Remote Delivery (Medium risk, controlled rollout)

Scope:
- Add `Send diagnostics automatically` setting (default OFF for initial rollout).
- Build async upload queue with durable local spool.
- Retry policy: exponential backoff, bounded attempts.
- Redaction pass before queue write and before network upload.

Acceptance criteria:
- Upload failures never block app startup or analysis workflows.
- Offline devices queue logs and flush later.
- Uploaded payloads pass redaction validation.

Rollback:
- Hard kill-switch: `CRMIT_REMOTE_DIAGNOSTICS=0`.
- Client disables network upload while local logging stays active.

## 6) Security and Privacy Checklist (Go/No-Go)

All items must be YES before enabling remote upload beyond pilot:

- User consent dialog reviewed and approved.
- Data classification completed for each uploaded field.
- Redaction rules tested against sample logs.
- Transport security enforced (HTTPS/TLS only).
- Server-side access control and audit logs enabled.
- Retention policy documented (recommended 30-90 days).
- Delete-by-request workflow documented.

## 7) Operational Controls

Feature flags:
- `CRMIT_FILE_LOGGING=1`
- `CRMIT_DIAG_EXPORT=1`
- `CRMIT_REMOTE_DIAGNOSTICS=0|1`

Environment stages:
- Stage A: internal dev machines
- Stage B: QA and pilot lab users
- Stage C: broad release

Monitoring KPIs:
- crash-free sessions %
- failed startup count per version
- upload success rate
- median time to triage (from report received to issue identified)

## 8) Test Matrix (Must pass before each stage)

Functional tests:
- Backend crash at startup
- Uvicorn bind failure
- Updater network timeout
- Renderer crash / main process unhandled rejection

Resilience tests:
- Disk full / log write failure
- No internet (upload queue behavior)
- Endpoint 500 and 429 retries

Privacy tests:
- Verify path/user redaction
- Verify no raw upload data in bundle

Compatibility tests:
- Windows 10/11 support matrix
- Upgrade from prior installer versions

## 9) Suggested Timeline

- Week 1: Phase 1 implementation + validation
- Week 2: Phase 2 implementation + support runbook
- Week 3: Phase 3 pilot (5-10 internal users)
- Week 4: analyze pilot, then expand rollout

## 10) Minimum Change Set (Implementation Targets)

Primary code areas:
- `electron/main.js`
- `electron/backend-manager.js`
- `electron/updater.js`
- `backend/run_desktop.py`

Optional UX enhancement:
- add diagnostics entry point in renderer if needed

## 11) Failure Handling Strategy

If diagnostics subsystem fails:
- Never block app startup.
- Fall back to console logging and local minimal log file.
- Record one concise self-diagnostic entry indicating diagnostics degradation.
- Continue core analysis features.

## 12) Execution Decision Template

Proceed to next phase only when:
- Acceptance criteria for current phase are fully met.
- No high-severity regression in updater or backend startup.
- Security/privacy checklist items relevant to the phase are complete.

---

Execution readiness: APPROVED FOR LATER STAGED EXECUTION

This plan is intentionally structured for safe incremental rollout with rollback controls at every phase.
