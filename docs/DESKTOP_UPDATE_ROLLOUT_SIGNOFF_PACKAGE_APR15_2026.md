# Desktop Update Rollout Sign-off Package

Date: 2026-04-15
Prepared by: BioVaram / CRM IT
Release line: v0.1.7

## 1) Scope of This Sign-off Package

This package records closure evidence for the final rollout tasks requested:

1. Unreachable-provider deterministic test
2. Corrupt-download controlled test
3. Rollback drill
4. Full regression pass
5. Code-signing validation
6. Final sign-off package

## 2) Evidence Files

- `temp/step4_unreachable_provider_deterministic_apr15.txt`
- `temp/step4_corrupt_download_controlled_apr15.txt`
- `temp/step4_rollback_drill_apr15.txt`
- `temp/step5_full_regression_pass_apr15.txt`
- `temp/step6_code_signing_validation_apr15.txt`
- `temp/regression_perf_gates_apr15.log`
- `temp/regression_uat_evidence_apr15.log`
- `temp/step7_signing_provisioning_and_release_attempt_apr15.txt`

## 3) Closure Results

### 3.1 Unreachable-provider deterministic test
- Result: PASS
- Method: controlled deterministic fault injection (`CRMIT_TEST_UNREACHABLE_PROVIDER=1`)
- Outcome: backend remained healthy, updater error path triggered safely, app stayed usable.

### 3.2 Corrupt-download controlled test
- Result: PASS
- Method: controlled deterministic fault injection (`CRMIT_TEST_CORRUPT_DOWNLOAD=1`)
- Outcome: download failure surfaced safely with no app crash.

### 3.3 Rollback drill
- Result: PASS
- Method: seeded `install-started` updater state with mismatched target version; startup recovery path executed.
- Outcome: stale update state cleared and app continued on last good version.

### 3.4 Full regression pass
- Result: PASS
- Suites executed:
  - `npm run perf:gates`
  - `npx playwright test tests/perf/fcs-compare-uat-evidence.spec.ts`
- Outcome: both suites passed after Playwright Chromium runtime installation.

### 3.5 Code-signing validation
- Result: FAIL (BLOCKER)
- Evidence: installer signature status = `NotSigned`
- Impact: broad production rollout should remain blocked until valid signing certificate is configured and signed artifacts are re-validated.

### 3.6 Production signing + signed release execution attempt
- Result: BLOCKED (external prerequisites missing)
- Attempted actions:
  - Enforced signing gate in release pipeline (`publish-release.ps1 -RequireSigning`)
  - Added no-publish signed-candidate workflow (`build-signed-candidate.ps1`)
  - Attempted signed candidate build and release execution
- Observed blockers in environment:
  - `GITHUB_TOKEN` missing
  - signing variables missing (`WIN_CSC_LINK`/`WIN_CSC_KEY_PASSWORD`, `CSC_LINK`/`CSC_KEY_PASSWORD`, `CSC_NAME`)
- Impact:
  - signed candidate could not be produced
  - signed update smoke cycle could not be executed
  - signed production release could not be published

## 4) Go / No-Go Decision

Current decision: GO FOR INTERNAL CLIENT TEST ROLLOUT

Public/global rollout decision: CONDITIONAL NO-GO

Reason:
- All resilience and regression closure tests passed.
- Internal rollout is controlled and intended for testing use.
- Code-signing gate is not satisfied (`NotSigned`), so broad/public rollout remains blocked.

## 5) Required Actions Before Public Go-Live

1. Provision production code-signing certificate (recommended EV cert for SmartScreen reputation).
2. Configure signing in build pipeline for installer/update artifacts.
3. Build signed release candidate.
4. Re-run signature validation and one update smoke cycle.
5. Publish signed release and update this package with final GO decision.

## 7) What Is Already Ready in Pipeline

The repository now includes production-safe signing gates:
- `scripts/validate-code-signing.ps1`
- `scripts/build-signed-candidate.ps1`
- `scripts/publish-release.ps1 -RequireSigning`

These changes prevent accidental unsigned production release when `-RequireSigning` is used.

## 6) Notes on Deterministic Resilience Testing

To support deterministic non-interactive validation in this repo, test-only updater fault-injection flags were used:
- `CRMIT_TEST_UNREACHABLE_PROVIDER=1`
- `CRMIT_TEST_CORRUPT_DOWNLOAD=1`
- `CRMIT_TEST_AUTO_ACK_DIALOGS=1`

These are disabled by default and do not alter normal runtime behavior unless explicitly set.
