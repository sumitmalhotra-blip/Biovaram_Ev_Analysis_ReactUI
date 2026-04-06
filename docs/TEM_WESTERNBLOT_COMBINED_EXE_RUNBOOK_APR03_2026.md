# TEM + WesternBlot Combined EXE Runbook
## Date: April 3, 2026
## Audience: Junior developers
## Goal: Build one Windows EXE that includes both TEM and WesternBlot modules

---

## 1. Outcome You Are Building
You will ship one desktop EXE that:
1. Starts backend services locally.
2. Opens the frontend in a desktop window.
3. Shows only TEM + WesternBlot module UI (plus shared dashboard if required).
4. Runs offline for normal analysis workflows.

This runbook is written for the current architecture in this repo:
1. Frontend: Next.js/React.
2. Backend: FastAPI/Python.
3. Packaging direction: Desktop wrapper + bundled backend.

---

## 2. Important Context in This Codebase
Current module switching already exists in frontend:
1. `lib/module-config.ts` currently supports `full`, `nanofacs`, `nta`.
2. `app/page.tsx` renders tabs based on `isTabEnabled(...)`.
3. `start.ps1` runs frontend and backend separately for dev.

What is missing for TEM + WesternBlot combined EXE:
1. A new module profile for TEM+WesternBlot in frontend module config.
2. Matching backend module profile/router gating.
3. A single desktop packaging pipeline that builds both FE+BE into one EXE artifact.

---

## 3. Pre-Implementation Checklist
Before writing packaging code, confirm these are true:
1. TEM frontend components exist and run independently.
2. WesternBlot frontend components exist and run independently.
3. TEM backend routers/services exist and run independently.
4. WesternBlot backend routers/services exist and run independently.
5. Both modules can use the same shared DB/config/runtime without port conflicts.

If any item is missing, complete that module first. Do not start EXE work until both modules are independently stable.

---

## 4. Step-by-Step Implementation Plan

## Phase A: Add a Combined Module Profile (Frontend)

### A1. Extend module config
Update `lib/module-config.ts`:
1. Add a new module type, for example: `tem_wb`.
2. Add module display name: `TEM + WesternBlot Suite`.
3. Add a module port mapping (for dev fallback), for example `8003`.
4. Add tab mapping for `tem_wb` to include TEM and WesternBlot tabs only (plus dashboard if needed).
5. Add default tab for `tem_wb`.

Suggested shape:
1. `ModuleType`: include `tem_wb`.
2. `MODULE_TABS.tem_wb`: `["dashboard", "tem", "westernblot"]` (adapt to your actual tab IDs).
3. `MODULE_DEFAULT_TAB.tem_wb`: `"tem"` (or your preferred entry module).

### A2. Ensure tab routing supports TEM and WesternBlot
Update tab rendering in `app/page.tsx` and navigation components:
1. Add lazy-loaded tab components for TEM and WesternBlot if not present.
2. Ensure `TabNavigation` can display new tab IDs.
3. Ensure `isTabEnabled` hides everything except allowed tabs in `tem_wb` mode.

### A3. Environment-based build selection
Set module at build time:
1. `NEXT_PUBLIC_MODULE=tem_wb` for frontend build.
2. Keep this value in CI/release scripts for repeatable output.

---

## Phase B: Add Backend Module Profile Gating

### B1. Create backend module profile env
In backend settings (for example `backend/src/api/config.py`):
1. Add env var like `MODULE_PROFILE` with default `full`.
2. Allowed values should include `tem_wb`.

### B2. Gate router registration
In `backend/src/api/main.py`:
1. Keep shared routers always on (health/auth/system status if needed).
2. Register TEM routers when profile is `tem_wb` or `full`.
3. Register WesternBlot routers when profile is `tem_wb` or `full`.
4. Skip unrelated routers (FCS/NTA/CrossCompare) when profile is `tem_wb`.

This prevents exposing unrelated endpoints in module-specific EXE.

### B3. Validate API contract from frontend
Run a full local test using:
1. Frontend in `tem_wb` mode.
2. Backend in `MODULE_PROFILE=tem_wb` mode.
3. Verify no 404/500 for TEM and WesternBlot flows.

---

## Phase C: Prepare Desktop Runtime Entry Points

### C1. Frontend production artifact
For desktop packaging, produce frontend static/runtime artifact from `tem_wb` mode:
1. Build command should inject `NEXT_PUBLIC_MODULE=tem_wb`.
2. Output must be deterministic (same files for same commit).

### C2. Backend desktop entrypoint
Create or reuse a desktop launcher (example pattern):
1. Start FastAPI server bound to localhost.
2. Use profile `MODULE_PROFILE=tem_wb`.
3. Resolve a free port if needed.
4. Expose readiness/health checks.

### C3. Shared runtime directories
Use app data directories for:
1. Database.
2. Upload/temp files.
3. Logs.
4. License/config files if used.

Do not write runtime state into installation directory.

---

## Phase D: Build One Combined EXE

Use one of these two packaging methods. Pick one and standardize.

### Option D1 (Recommended for polished UX): Electron wrapper + bundled backend
Use this if you need a true desktop window and installer experience.

1. Build backend executable:
1. Use PyInstaller on backend launcher.
2. Bundle required Python dependencies and model/data files.

2. Build frontend module artifact:
1. Build with `NEXT_PUBLIC_MODULE=tem_wb`.
2. Bundle frontend output into Electron resources.

3. Electron main process:
1. On app launch, start backend child process.
2. Wait for `/health` ready signal.
3. Open BrowserWindow to local app URL.
4. On app close, gracefully terminate backend process.

4. Package installer:
1. Use `electron-builder` (NSIS target for Windows).
2. Include app icon, app version, publisher metadata.

### Option D2 (Faster initial delivery): PyInstaller launcher + system browser
Use this if you need fastest first delivery.

1. Build one Python executable that:
1. Starts backend.
2. Serves frontend assets.
3. Opens default browser to localhost.

2. Result is one EXE, less polished but simpler.

---

## 5. Suggested Build Script Structure
Create a release script folder, for example `scripts/release/`:
1. `build-frontend-tem-wb.ps1`
2. `build-backend-tem-wb.ps1`
3. `package-tem-wb-exe.ps1`
4. `verify-tem-wb-artifact.ps1`

Script responsibilities:
1. Clean previous artifacts.
2. Install deps (deterministic lockfile install).
3. Build frontend with `NEXT_PUBLIC_MODULE=tem_wb`.
4. Build backend with `MODULE_PROFILE=tem_wb`.
5. Package final EXE.
6. Emit checksums and manifest.

---

## 6. QA and Acceptance Criteria
The combined EXE is accepted only if all pass:
1. App launches on clean Windows machine with no Node/Python preinstalled.
2. Only TEM + WesternBlot tabs are visible.
3. TEM workflows complete end-to-end.
4. WesternBlot workflows complete end-to-end.
5. Logs are generated in app-data location.
6. EXE close terminates backend process cleanly.
7. Offline launch works for normal analysis paths.
8. Installer/EXE version shown correctly.

---

## 7. CI/CD Recommendation
Create one dedicated pipeline for this combined module artifact:
1. Trigger on tagged release or manual dispatch.
2. Build on Windows runner.
3. Produce artifacts:
1. Installer EXE.
2. Portable EXE (optional).
3. SHA256 checksum file.
4. Build metadata (commit, date, module profile).

---

## 8. Common Pitfalls and Fixes
1. Wrong tabs appear in EXE:
1. Check `NEXT_PUBLIC_MODULE=tem_wb` was set during frontend build.
2. Ensure stale frontend cache/build folder is cleaned before packaging.

2. Backend exposes wrong APIs:
1. Verify `MODULE_PROFILE=tem_wb` at runtime, not just build time.
2. Confirm router inclusion logic in `backend/src/api/main.py`.

3. EXE starts but blank window appears:
1. Check backend health-wait logic before loading BrowserWindow URL.
2. Confirm frontend build assets are included in packaged resources.

4. App closes but python process remains:
1. Add child process kill/cleanup handlers on Electron app exit.
2. Handle forced close and crash signals.

---

## 9. Handoff Checklist for Juniors
Before raising PR for release branch:
1. Include module profile code changes (FE + BE).
2. Include packaging scripts.
3. Include local run steps in README section.
4. Attach QA evidence (screenshots/videos/log snippets).
5. Attach artifact size and SHA256 checksum.
6. Confirm tested on a clean Windows VM.

---

## 10. Minimal Command Flow (Reference)
Use these as a template and adapt to your final scripts.

1. Frontend build for combined module:
```powershell
$env:NEXT_PUBLIC_MODULE="tem_wb"
npm ci
npm run build
```

2. Backend build for combined module:
```powershell
$env:MODULE_PROFILE="tem_wb"
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pyinstaller .\run_api.py --name BioVaram-TEM-WB-Backend --onefile
```

3. Package desktop app (Electron route):
```powershell
npm run desktop:build:tem-wb
```

If you do not have `desktop:build:tem-wb` yet, create it and keep it as the single source of truth for releases.

---

## 11. Recommended Next Action
Implement Phase A and Phase B first in one PR (module profile + gating), verify local `tem_wb` mode stability, then start Phase C/D packaging PR.

This two-PR approach reduces release risk and makes debugging much easier.
