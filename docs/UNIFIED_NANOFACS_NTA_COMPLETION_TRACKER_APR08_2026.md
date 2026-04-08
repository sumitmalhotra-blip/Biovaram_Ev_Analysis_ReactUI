# Unified NanoFACS + NTA Completion Tracker
## Date: April 8, 2026
## Purpose
This file is the single consolidated tracker for NanoFACS and NTA work status, reconciled from all active and legacy trackers plus recent evidence runs.

## Sources Reconciled
1. TASK_TRACKER.md
2. docs/NANOFCS_UNIFIED_MULTI_FILE_TASK_TRACKER_MAR31_2026.md
3. docs/NANOFCS_COMPARE_REMEDIATION_REFERENCE_APR07_2026.md
4. docs/NTA_MULTI_FILE_COMPARE_STRATEGY_MAR24_2026.md
5. docs/NTA_IMPLEMENTATION_PLAN_MAR24_2026.md
6. Latest focused NanoFACS evidence runs and live-backend acceptance outputs

## NanoFACS Status
### Completed
1. Compare reliability foundation and deterministic loading hardening (WS-A): completed.
2. Performance foundation (workers, caching, progressive paint, point/bin caps) (WS-B): completed.
3. Multi-file compare UX/session controls (WS-C): completed.
4. Graph tool parity and isolation (WS-D): completed.
5. Principles expansion items E1-E4: completed in tracker and reflected in current compare behavior.
6. Treatment + dye metadata parity and UAT evidence pack (WS-F1/F2): completed.
7. Compare UX/reliability closure items G1-G4: completed.
8. Focused reliability evidence:
   - rapid-toggle evidence spec: pass.
   - upload-retry evidence spec: pass.
9. Live-backend 5-file duplicate acceptance:
   - 5/5 uploads succeeded.
   - 5 compare items retained.
   - duplicate backend sample_id observed while preserving distinct compare entities.
10. Apr 8 compare closure update (implementation completed):
   - compare upload UX refactor completed (queue-state counters, retry-friendly queue behavior, explicit cap toasts, success cleanup).
   - compare chart/session state sync completed (view fallback guards, overlay-mode fallback, primary-result null-safe sync, visible-set reload trigger).
   - file-cap alignment completed across compare session state and UI copy:
     - FCS selected compare cap normalized to 10 in store hydration and runtime selection.
     - upload dropzone guidance aligned to "up to 10 compare files".

### Validation Evidence (Apr 8, 2026)
1. Targeted Playwright validation for compare controls and graph/session behavior:
   - command: npx playwright test tests/perf/fcs-compare-controls-verification.spec.ts --project=chromium
   - result: pass (1 passed).
   - note: test selector was hardened for duplicated "Per-file Axis" controls in multi-graph UI.
2. Alternative repository-wide compile validation path:
   - command: npx tsc --noEmit
   - result: fails due pre-existing cross-module TypeScript issues outside this focused NanoFACS compare change set (backup auth files, cross-compare typing, legacy chart/store typing issues).
   - outcome: focused compare files remain diagnostics-clean and targeted compare acceptance check is passing.

### Closure Execution Snapshot (Apr 8, 2026)
1. Final NanoFACS long-task gate execution:
   - evidence file: temp/perf-reports/fcs-compare-longtask-gate.json
   - threshold: 50 ms recurring long-task gate.
   - latest measured summary (final): totalLongTasks=0, overThresholdCount=0, maxDurationMs=0.
   - latest gate status (final): gatePassed=true.
   - decision: long-task closure item completed.
2. Final NanoFACS acceptance/checklist refresh run:
   - passing acceptance evidence runs:
     - tests/perf/fcs-compare-controls-verification.spec.ts
     - tests/perf/fcs-compare-gates.spec.ts
     - tests/perf/fcs-compare-upload-retry-evidence.spec.ts
   - refreshed artifacts:
     - temp/perf-reports/fcs-compare-controls-verification.json
     - temp/perf-reports/fcs-compare-gates-report.json
     - temp/perf-reports/fcs-compare-upload-retry-evidence.json
       - temp/perf-reports/fcs-compare-longtask-gate.json
       - temp/perf-reports/fcs-compare-rapid-toggle-evidence.json
       - temp/perf-reports/fcs-compare-uat-evidence.json
    - decision: acceptance/checklist refresh completed with full closure suite pass.
3. Final acceptance rerun status (post-stabilization):
    - command: npx playwright test tests/perf/fcs-compare-gates.spec.ts tests/perf/fcs-compare-controls-verification.spec.ts tests/perf/fcs-compare-upload-retry-evidence.spec.ts tests/perf/fcs-compare-rapid-toggle-evidence.spec.ts tests/perf/fcs-compare-uat-evidence.spec.ts --project=chromium
    - result: pass (5 passed).

### Pending
1. No open NanoFACS closure blockers in this module tracker snapshot.

## NTA Status
### Completed
1. Multi-file session foundation and selection UI: completed.
2. Multi-series chart migration: completed.
3. Core performance path (concurrency-limited fetch, caching, progressive paint, debounce, downsampling): completed.
4. Optional backend bulk endpoint implemented and frontend fallback retained:
   - POST /analysis/nta/multi-compare path implemented.

### Pending
1. Full QA matrix closure for 1/2/5/10/20 sample sessions, stress, and regression sign-off.
2. Remaining implementation-plan backlog items that depend on product/QA finalization:
   - tolerance/profile finalization for quality thresholds.
   - final report template and export expectations.
   - GA max compare-file decision and final acceptance criteria freeze.

## Cross-Tracker Reconciliation Notes
1. NanoFACS tracker items marked done in WS-A through WS-G are consistent with latest focused evidence and live-backend acceptance.
2. NTA strategy reflects implementation progress but still carries explicit QA closure pending.
3. TASK_TRACKER.md still contains broader platform backlog (validation/compliance/enterprise/TEM) outside this file's NanoFACS+NTA module scope.

## Single Active Action List (Module Scope)
1. Run and document final NanoFACS long-task performance trace gate.
2. Execute NTA full QA matrix (1/2/5/10/20) and record pass/fail with evidence.
3. Publish final module sign-off addendum (NanoFACS + NTA) in this file only.

## Cleanup Decision Log
1. Superseded NanoFACS/NTA tracker documents have been removed in favor of this consolidated file.
2. Temporary perf-report markdown/image/debug artifacts generated for intermediate iterations were removed as non-source transient artifacts.
