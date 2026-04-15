# Desktop Rollout Step 3 + 4 Validation (Apr 15, 2026)

## Scope
This report captures execution evidence for:
- Step 3: Clean-profile E2E update validation for current candidate path (0.1.2 -> 0.1.3).
- Step 4: Resilience checks for updater/backend failure scenarios.

## Step 3 - Clean-Profile E2E (0.1.2 -> 0.1.3)

### Evidence Collected
- Installed baseline version probe:
  - File: temp/installed_version_probe.txt
  - Result: INSTALLED_DISPLAY_VERSION=0.1.2
- Updater state after launch with clean updater-state/pending reset:
  - File: temp/step3_e2e_result.txt
  - Key fields:
    - UPDATER_STAGE=download-started
    - UPDATER_TARGET=0.1.3
    - PENDING_FILES=current.blockmap,temp-BioVaram-Setup-0.1.3.exe

### Interpretation
- Update discovery from installed 0.1.2 to target 0.1.3 is working.
- Download path is active (pending installer temp file created).
- Full install-and-restart confirmation is not finalized in this non-interactive terminal run (requires completing the UI install prompt and relaunch verification in-app).

### Status
- Step 3 status: PARTIALLY COMPLETED (detection + download evidence captured; final install-restart assertion pending interactive confirmation).

## Step 4 - Resilience Tests

### Test A - Backend startup failure handling (port conflict)
- Method:
  - Occupied port 18000 with a temporary TCP listener.
  - Launched desktop app.
- Runtime output:
  - [desktop] Backend exited (code=1, signal=null)
  - [desktop] Boot failed: Backend process exited before becoming healthy
- Evidence file:
  - temp/step4_resilience_backend_failure.txt
  - APP_EXITED_WITH_PORT_CONFLICT=yes
  - LOG_HAS_BIND_ERROR=yes
- Result: PASS (failure detected and surfaced with actionable backend-start signal).

### Test B - Update provider unreachable simulation
- Method:
  - Set HTTP_PROXY/HTTPS_PROXY to invalid local endpoint before launch.
  - Captured updater state and process/health signals.
- Evidence file:
  - temp/step4_resilience_unreachable.txt
  - PROCESS_RUNNING_AFTER_25S=no
  - BACKEND_HEALTH=ok
  - UPDATER_STAGE=download-started
- Result: INCONCLUSIVE in this environment (proxy route did not force a deterministic updater-error state; app backend remained healthy).

### Test C - Corrupt download handling
- Not executed automatically to avoid mutating signed release artifacts and destabilizing test channel.
- Requires controlled manual fault injection run.

### Status
- Step 4 status: PARTIALLY COMPLETED (backend-failure resilience verified; unreachable/corrupt-download scenarios still need controlled completion).

## Remaining To Fully Close Step 3 + 4
1. Complete one interactive install-and-restart cycle from 0.1.2 to 0.1.3 and capture post-restart version proof.
2. Run a deterministic unreachable-provider test (e.g., temporary firewall block for github API/asset hosts during app launch) and confirm app remains usable.
3. Run a controlled corrupt-download test in isolated channel and verify safe user-facing retry/error message.
