# Desktop Modularization Plan — BioVaram EV Analysis Platform

## From Monolith to Modular Desktop Executables

**Date:** February 27, 2026  
**Author:** Architecture Team  
**Status:** Planning  
**Target Delivery:** Module-by-module, starting March 2026

---

## 1. Why Modularize?

**Current state:** One monolithic application — a Python FastAPI backend + Next.js React frontend running together. To use *any* feature, the user must run the entire stack.

**What Surya needs:** Individual EXE files he can run in the lab on a Windows PC — click an icon, the module opens, he uses it, closes it. No terminal, no `npm run dev`, no port configuration.

**What we need:** The ability to develop, test, and ship each module independently, while keeping them connectable when deployed as a full platform.

---

## 2. Module Breakdown

Based on the current codebase and feature areas, the platform splits into **5 functional modules + 1 shared core**:

```
┌──────────────────────────────────────────────────────────┐
│                    SHARED CORE LAYER                      │
│  Database │ Config │ Auth │ Physics Engine │ Parsers      │
└─────────┬──────────┬──────────┬──────────┬───────────────┘
          │          │          │          │
    ┌─────┴──┐  ┌────┴───┐  ┌──┴───┐  ┌──┴──────┐  ┌─────┐
    │ Module │  │ Module │  │Module│  │ Module  │  │Mod  │
    │   1    │  │   2    │  │  3   │  │   4     │  │ 5   │
    │ NanoFACS│  │  NTA   │  │Cross │  │Dashboard│  │ AI  │
    │  (FCS) │  │Analysis│  │Comp. │  │& Admin  │  │Chat │
    └────────┘  └────────┘  └──────┘  └─────────┘  └─────┘
```

### Module 1: NanoFACS / Flow Cytometry

**What it does:** Upload FCS files → bead calibration → Mie sizing → scatter plots → size distribution → anomaly detection → population shift → export

**Backend pieces:**
- `routers/upload.py` (FCS upload only)
- `routers/samples.py` (FCS-related endpoints: scatter-data, size-bins, distribution-analysis, reanalyze, fcs/values, fcs/metadata, available-channels)
- `routers/calibration.py` (all bead calibration endpoints)
- `parsers/fcs_parser.py`, `parsers/bead_datasheet_parser.py`
- `physics/mie_scatter.py`, `physics/bead_calibration.py`, `physics/size_distribution.py`, `physics/size_config.py`, `physics/statistics_utils.py`
- `analysis/population_shift.py`, `analysis/temporal_analysis.py`
- `visualization/auto_axis_selector.py`
- `utils/channel_config.py`

**Frontend pieces:**
- `components/flow-cytometry/` (all 24+ files)
- `components/flow-cytometry/charts/` (all 10 charts)
- `components/sidebar.tsx` (FCS settings portion)

**Database tables used:** `samples`, `fcs_results`, `processing_jobs`, `experimental_conditions`, `qc_reports`

---

### Module 2: NTA Analysis

**What it does:** Upload NTA text/PDF → parse → size distribution → concentration profile → temperature correction → metadata → export

**Backend pieces:**
- `routers/upload.py` (NTA upload only)
- `routers/samples.py` (NTA-related endpoints: nta/metadata, nta/values)
- `parsers/nta_parser.py`, `parsers/nta_pdf_parser.py`
- `physics/nta_corrections.py`

**Frontend pieces:**
- `components/nta/` (all 9 files)
- `components/nta/charts/` (all 4 charts)

**Database tables used:** `samples`, `nta_results`

---

### Module 3: Cross-Compare / Validation

**What it does:** Compare FCS vs NTA results → overlay histograms → statistical tests → validation verdict → export PDF

**Depends on:** Module 1 + Module 2 data (needs both FCS and NTA results in the database)

**Backend pieces:**
- `routers/samples.py` (cross-validate endpoint)
- `routers/analysis.py` (statistical-tests, distribution-comparison)
- Uses physics engine from Module 1 for Mie re-computation

**Frontend pieces:**
- `components/cross-compare/` (all 6 files)
- `components/cross-compare/charts/` (all 4 charts)

**Database tables used:** `samples`, `fcs_results`, `nta_results`

---

### Module 4: Dashboard & Administration

**What it does:** Overview stats → recent activity → alerts → job queue → sample management → user management

**Backend pieces:**
- `routers/samples.py` (list, get, delete)
- `routers/jobs.py` (all job endpoints)
- `routers/alerts.py` (all alert endpoints)
- `routers/auth.py` (user management)

**Frontend pieces:**
- `components/dashboard/` (all 10 files)
- `components/previous-analyses.tsx`
- `components/sample-details-modal.tsx`
- `components/delete-confirmation-dialog.tsx`

**Database tables used:** All tables

---

### Module 5: AI Research Chat

**What it does:** Scientific Q&A → context-aware queries about loaded samples → literature guidance

**Backend pieces:**
- `app/api/research/chat/route.ts` (Next.js API route)
- Vercel AI SDK integration

**Frontend pieces:**
- `components/research-chat/research-chat-tab.tsx`
- `lib/ai-chat-client.ts`

**Note:** This module requires internet connectivity (LLM API calls). It can be deferred for the initial lab deployment.

---

### Shared Core Layer

Everything that multiple modules depend on:

| Component | Files | Used By |
|-----------|-------|---------|
| **Database engine** | `database/connection.py`, `database/models.py`, `database/crud.py` | All modules |
| **Configuration** | `api/config.py`, `config/channel_config.json` | All modules |
| **Authentication** | `api/auth_middleware.py`, `routers/auth.py` | All modules |
| **Base parser** | `parsers/base_parser.py` | Module 1, 2 |
| **Parquet writer** | `parsers/parquet_writer.py` | Module 1, 2 |
| **Cache** | `api/cache.py` (TTLCache) | Module 1, 2, 3 |
| **UI primitives** | `components/ui/*` (57 files) | All modules |
| **Store** | `lib/store.ts` | All modules |
| **API client** | `lib/api-client.ts` | All modules |
| **Hooks** | `hooks/*` | All modules |
| **Layout** | `app/layout.tsx`, `header.tsx`, `tab-navigation.tsx` | All modules |
| **Theme** | `theme-provider.tsx`, `globals.css` | All modules |
| **Error handling** | `error-boundary.tsx`, `lib/error-utils.ts` | All modules |
| **Export utils** | `lib/export-utils.ts` | Module 1, 2, 3 |

---

## 3. Packaging Strategy

### Option A: Embedded Web App (Recommended)

**How it works:**
```
EXE (PyInstaller / Electron)
 ├── Python backend (FastAPI + uvicorn)        ← bundled
 ├── Next.js static export (HTML/CSS/JS)       ← bundled
 ├── SQLite database                           ← created on first run
 ├── config/ (calibration, bead standards)     ← bundled
 └── data/ (uploads, parquet, temp)            ← created at runtime
```

The EXE starts a local server (e.g., `localhost:8000`), opens a browser window (or embedded Chromium via Electron/WebView2), and the user interacts with the same web UI they already know.

**Why this is best:**
- Zero rework on the UI — it's already built and working
- Zero rework on the API — FastAPI serves as-is
- The user sees a normal application window
- All data stays local (no cloud dependency)
- Can still connect modules to a shared database

**Tech stack:**
```
Option A1: PyInstaller + system browser
  - Simplest: PyInstaller bundles Python + deps
  - On launch: starts uvicorn, opens default browser to localhost
  - Lightest EXE (~200-300 MB after compression)

Option A2: Electron wrapper
  - Electron hosts embedded Chromium
  - Spawns Python backend as child process
  - Desktop-native window (titlebar, tray icon, etc.)
  - Heavier EXE (~400-500 MB) but more polished

Option A3: PyWebView (Python-native)
  - Python-only: uses system WebView2 (Windows) / WebKit (Mac)
  - No Electron overhead, native-feeling window
  - ~200-300 MB, desktop-native feel
```

**Recommendation:** Start with **A1 (PyInstaller + system browser)** for the first delivery to Surya. It's the fastest to implement and Surya already uses PyInstaller. Upgrade to A3 (PyWebView) later for a polished UX.

---

### Option B: Pure Python GUI (NOT Recommended)

Rewriting the entire UI in Tkinter/PyQt/PySide. This would be:
- 3-6 months of work to recreate what we already have
- Lose all the React charts, responsive design, export capabilities
- No benefit over the embedded web approach

**Verdict:** Don't do this.

---

## 4. Detailed Implementation Plan

### Phase 0: Preparation (Week 1 — Feb 27 – Mar 5)

#### 0.1 Next.js Static Export

The frontend is currently a server-rendered Next.js app. For desktop packaging, we need a **static export** (pure HTML/CSS/JS files that can be served by FastAPI).

**Changes needed:**

```javascript
// next.config.mjs — add:
output: 'export'
```

**Implications:**
- All API calls already go to `localhost:8000` — no change needed
- The AI chat route (`app/api/research/chat/route.ts`) uses server-side streaming — this needs to move to the Python backend OR become a serverless function the desktop app calls
- NextAuth.js needs to either:
  - Move auth fully to FastAPI (we already have `routers/auth.py` with JWT)
  - Or use a simpler token-based auth for desktop (single user, no need for full OAuth)

**Task list:**
- [ ] Add `output: 'export'` to next.config.mjs
- [ ] Move AI chat endpoint from Next.js API route to FastAPI backend
- [ ] Replace NextAuth with direct FastAPI JWT auth (or auto-login for desktop)
- [ ] Build static export: `pnpm build` → produces `out/` directory
- [ ] Configure FastAPI to serve `out/` as static files at root `/`
- [ ] Test: `uvicorn` alone serves both API and UI

#### 0.2 Single-Process Architecture

Make FastAPI serve everything:

```python
# backend/run_desktop.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.api.main import app

# Mount the static frontend at root
app.mount("/", StaticFiles(directory="../out", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading
    
    # Open browser after short delay
    def open_browser():
        import time
        time.sleep(2)
        webbrowser.open("http://localhost:8000")
    
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

**Task list:**
- [ ] Create `run_desktop.py` entry point
- [ ] Add static file mounting to FastAPI app
- [ ] Add auto-browser-open on startup
- [ ] Handle port conflicts (try 8000, fallback to 8001, etc.)
- [ ] Add graceful shutdown (Ctrl+C or window close → stop server)
- [ ] Test end-to-end: single command launches everything

#### 0.3 Database Migration (SQLite → Portable)

Currently the database is at `./data/crmit.db`. For desktop:
- Database file should live in a user-writable location
- First-run should auto-create tables (Alembic or `create_all`)
- Backup/export capability

**Task list:**
- [ ] Make DB path configurable via environment variable with sensible default (`%APPDATA%/BioVaram/crmit.db` on Windows)
- [ ] Add auto-table-creation on first run (bypass Alembic for desktop)
- [ ] Add DB backup/restore endpoints

---

### Phase 1: Full Platform EXE (Week 2–3 — Mar 6 – Mar 19)

Build a single EXE that contains the entire platform. This is the fastest path to giving Surya something to test.

#### 1.1 PyInstaller Spec File

```python
# biovaram.spec
a = Analysis(
    ['backend/run_desktop.py'],
    pathex=['backend'],
    binaries=[],
    datas=[
        ('out/', 'frontend/'),                          # Static UI
        ('backend/config/', 'config/'),                 # Config files
        ('backend/calibration_data/', 'calibration_data/'),
    ],
    hiddenimports=[
        'uvicorn.logging', 'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on', 'aiosqlite',
        'sqlalchemy.dialects.sqlite', 'miepython',
        'scipy.special.cython_special', 'sklearn',
        'engineio.async_drivers.aiohttp',
    ],
    ...
)
```

**Task list:**
- [ ] Create PyInstaller spec file
- [ ] Resolve all hidden imports (FastAPI + uvicorn + SQLAlchemy async need many)
- [ ] Test on clean Windows machine (no Python installed)
- [ ] Handle miepython C extension compilation
- [ ] Handle scipy/numpy binary dependencies
- [ ] Add splash screen / loading indicator
- [ ] Add application icon (.ico)
- [ ] Test final EXE size (target: < 400 MB)

#### 1.2 First-Run Experience

When the user launches for the first time:
1. Create `%APPDATA%/BioVaram/` directory structure
2. Initialize empty SQLite database
3. Copy default config files (channel_config, bead_standards)
4. Open browser to `localhost:8000`
5. Show welcome page / quick start

**Task list:**
- [ ] Add first-run detection (check if DB exists)
- [ ] Create data directory structure
- [ ] Auto-register a default user (for desktop, no signup needed)
- [ ] Auto-login (desktop mode = single user)

#### 1.3 Deliverable

**Full Platform EXE** — everything in one executable. Surya can:
- Upload FCS files → see scatter plots, size distributions
- Upload bead files → run calibration
- Upload NTA files → see NTA analysis
- Cross-compare FCS vs NTA
- Use AI chat (if internet available)
- Export PDF/CSV/Excel reports

---

### Phase 2: Module Splitting (Week 4–6 — Mar 20 – Apr 9)

Once the full EXE works, split into individual module EXEs.

#### 2.1 Architecture for Separate Modules

Each module is a separate EXE but they **share the same database and data directory:**

```
%APPDATA%/BioVaram/
├── crmit.db                    ← shared SQLite database
├── config/
│   ├── channel_config.json
│   ├── bead_standards/
│   └── calibration/
├── data/
│   ├── uploads/                ← shared upload directory
│   └── parquet/                ← shared parquet directory
└── logs/
```

When Module 1 (NanoFACS) uploads and processes an FCS file, the results are in the shared DB. When Module 3 (Cross-Compare) launches, it can see those results immediately.

**How this works technically:**
- Each module EXE bundles its own Python runtime + FastAPI subset
- Each module uses the **same database file path** (configured via shared settings file or registry)
- File locking: SQLite supports multiple readers. Only one writer at a time, but each module runs sequentially anyway (lab use case = one module at a time)
- Each module runs on a **different port** to avoid conflicts if someone runs two simultaneously

| Module | Default Port | Fallback Ports |
|--------|-------------|----------------|
| NanoFACS | 8001 | 8011, 8021 |
| NTA | 8002 | 8012, 8022 |
| Cross-Compare | 8003 | 8013, 8023 |
| Dashboard | 8004 | 8014, 8024 |
| Full Platform | 8000 | 8010, 8020 |

#### 2.2 Module-Specific FastAPI Apps

Instead of one big `main.py` with all routers, each module has its own slim app:

```python
# module_nanofacs/app.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.api.routers import upload, samples, calibration
from src.database.connection import init_db

app = FastAPI(title="BioVaram NanoFACS")

# Only include relevant routers
app.include_router(upload.fcs_router, prefix="/api/v1/upload")      # FCS upload only
app.include_router(samples.fcs_router, prefix="/api/v1/samples")    # FCS endpoints only
app.include_router(calibration.router, prefix="/api/v1/calibration")

# Serve module-specific static frontend
app.mount("/", StaticFiles(directory="frontend_nanofacs/", html=True))
```

**This means we need to split the routers:**

| Current Router | Split Into |
|---------------|------------|
| `upload.py` | `upload_fcs.py` + `upload_nta.py` |
| `samples.py` (4282 LOC!) | `samples_common.py` + `samples_fcs.py` + `samples_nta.py` + `samples_cross.py` |

Or more practically: keep the routers as-is but **include only the endpoints each module needs** using FastAPI's router filtering.

#### 2.3 Module-Specific Frontend Builds

Each module needs its own static export with only the relevant tabs. Approach:

```
// Environment variable controls which tabs are available
NEXT_PUBLIC_MODULE = "nanofacs"  // or "nta", "cross-compare", "dashboard", "full"
```

In `app/page.tsx`, conditionally render only the relevant tab:
```typescript
const enabledModules = process.env.NEXT_PUBLIC_MODULE || 'full';

// Only show NanoFACS tab if module is 'nanofacs' or 'full'
{(enabledModules === 'nanofacs' || enabledModules === 'full') && <FlowCytometryTab />}
```

Build each variant:
```bash
NEXT_PUBLIC_MODULE=nanofacs pnpm build    → out_nanofacs/
NEXT_PUBLIC_MODULE=nta pnpm build         → out_nta/
NEXT_PUBLIC_MODULE=cross pnpm build       → out_cross/
NEXT_PUBLIC_MODULE=full pnpm build        → out_full/
```

**Task list:**
- [ ] Add `NEXT_PUBLIC_MODULE` environment variable to control tab visibility
- [ ] Update `app/page.tsx` to conditionally render tabs
- [ ] Update `sidebar.tsx` to show only relevant settings
- [ ] Update `header.tsx` to show module name
- [ ] Create build scripts for each module variant
- [ ] Create PyInstaller specs for each module

---

### Phase 3: Polish & Production (Week 7–8 — Apr 10 – Apr 23)

#### 3.1 Installer

Instead of a raw EXE, create a proper Windows installer:

**Option: Inno Setup (free, battle-tested)**
- Creates a `.setup.exe` with install wizard
- Start menu shortcuts for each module
- Uninstaller
- Auto-creates data directories
- Optionally: desktop shortcuts

```
Program Files/
└── BioVaram/
    ├── BioVaram Full Platform.exe
    ├── BioVaram NanoFACS.exe
    ├── BioVaram NTA.exe
    ├── BioVaram CrossCompare.exe
    └── _internal/                    ← PyInstaller runtime (shared)
```

#### 3.2 Auto-Update (Future)

For post-deployment updates:
- Add a version check on startup (HTTP call to a version API)
- Download new EXE from a releases server
- Prompt user to update

#### 3.3 Data Migration

When upgrading from one version to another:
- SQLite database schema may change
- Include Alembic migrations in the EXE bundle
- Run migrations automatically on startup if DB version < app version

---

## 5. Shared Database Strategy

### The Core Question: How Do Modules Stay Connected?

**Answer: One SQLite file, shared file path.**

```
All modules read/write: %APPDATA%/BioVaram/crmit.db
```

This works because:
1. Lab use case = one person, one computer, one module at a time
2. SQLite handles concurrent reads fine
3. Write contention is minimal (user won't upload via NanoFACS and NTA simultaneously)

### Schema Compatibility

All module EXEs are built from the same codebase at the same time, so they share the same schema version. The database includes a version table:

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

On startup, each module checks: `my_schema_version == db_schema_version`. If not, run migrations.

### What Goes in the Database vs. Config Files

| Data | Storage | Reason |
|------|---------|--------|
| Uploaded file metadata (Sample records) | SQLite DB | Queryable, relational |
| FCS/NTA analysis results | SQLite DB | Queryable, relational |
| Processing jobs | SQLite DB | Stateful, needs tracking |
| User accounts | SQLite DB | Auth, multi-user future |
| Alerts | SQLite DB | Queryable, dismissable |
| Calibration parameters (k-factor, bead data) | JSON files in `config/calibration/` | Versionable, portable, human-readable |
| Bead standard definitions | JSON files in `config/bead_standards/` | Static reference data |
| Channel configuration | JSON file | Instrument-specific, rarely changes |
| Raw uploaded files | `data/uploads/` directory | Binary files, too large for DB |
| Parquet event data | `data/parquet/` directory | Columnar analytics format |

---

## 6. AI Chat in Desktop Mode

The AI Research Chat currently uses:
- Next.js API route (`app/api/research/chat/route.ts`)
- Vercel AI SDK with `streamText()`
- Requires an API key for the LLM provider

### Desktop Approach

**Move the chat endpoint to FastAPI:**

```python
# backend/src/api/routers/chat.py
@router.post("/chat")
async def research_chat(request: ChatRequest):
    # Call OpenAI/Anthropic API directly from Python
    # Stream response back via SSE
    ...
```

**Configuration:**
- User provides their own API key (stored in local config, encrypted)
- Or we provide a pre-configured key for licensed users
- If no key: chat tab shows "AI Chat requires an API key. Configure in Settings."
- The chat module is **optional** — the platform works fully without it

---

## 7. Implementation Timeline

```
Week 1 (Feb 27 – Mar 5):   PHASE 0 — Static export, single-process architecture
Week 2 (Mar 6 – Mar 12):   PHASE 1a — PyInstaller bundling, dependency resolution
Week 3 (Mar 13 – Mar 19):  PHASE 1b — First-run experience, testing on clean machine
                            >>> DELIVERABLE: Full Platform EXE to Surya <<<
Week 4 (Mar 20 – Mar 26):  PHASE 2a — Router splitting, module-specific apps
Week 5 (Mar 27 – Apr 2):   PHASE 2b — Module-specific frontend builds
Week 6 (Apr 3 – Apr 9):    PHASE 2c — Individual module EXEs, testing
                            >>> DELIVERABLE: Individual Module EXEs <<<
Week 7 (Apr 10 – Apr 16):  PHASE 3a — Inno Setup installer, shortcuts
Week 8 (Apr 17 – Apr 23):  PHASE 3b — Polish, data migration, documentation
                            >>> DELIVERABLE: Production Installer <<<
```

---

## 8. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **PyInstaller hidden import issues** | High | Blocks build | Maintain a growing list of hiddenimports; test frequently |
| **EXE size too large (>500 MB)** | Medium | User experience | Use `--exclude-module` for unused scipy/sklearn submodules; UPX compression |
| **Next.js static export breaks dynamic routes** | Medium | Blocks Phase 0 | We only have 4 pages, all can be static; API calls are already client-side |
| **SQLite locking if two modules run simultaneously** | Low | Data corruption | WAL mode (`journal_mode=WAL`), retry logic on write conflicts |
| **miepython C extension won't bundle** | Medium | Breaks NanoFACS | Pre-compile wheel; include `.pyd` file directly |
| **antivirus blocks EXE** | Medium | User can't run | Code-sign the EXE (requires a certificate); add to allowlist instructions |
| **AI chat needs internet** | Expected | Chat doesn't work offline | Clearly label as "requires internet"; graceful fallback message |

---

## 9. File Structure After Modularization

```
ev-analysis-platform/
├── shared/                          ← NEW: shared core
│   ├── database/
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── crud.py
│   ├── config/
│   │   ├── settings.py
│   │   └── defaults/
│   ├── parsers/
│   │   ├── base_parser.py
│   │   └── parquet_writer.py
│   ├── physics/
│   │   ├── mie_scatter.py
│   │   ├── bead_calibration.py
│   │   ├── size_distribution.py
│   │   ├── nta_corrections.py
│   │   ├── statistics_utils.py
│   │   └── size_config.py
│   └── utils/
│       ├── cache.py
│       ├── channel_config.py
│       └── auth.py
│
├── modules/                         ← NEW: module-specific code
│   ├── nanofacs/
│   │   ├── app.py                   ← Module-specific FastAPI app
│   │   ├── routers/
│   │   │   ├── upload_fcs.py
│   │   │   ├── samples_fcs.py
│   │   │   └── calibration.py
│   │   └── run.py                   ← Entry point for this module
│   │
│   ├── nta/
│   │   ├── app.py
│   │   ├── routers/
│   │   │   ├── upload_nta.py
│   │   │   └── samples_nta.py
│   │   └── run.py
│   │
│   ├── cross_compare/
│   │   ├── app.py
│   │   ├── routers/
│   │   │   └── cross_validate.py
│   │   └── run.py
│   │
│   └── full_platform/
│       ├── app.py                   ← Includes ALL routers
│       └── run.py
│
├── frontend/                        ← Replaces current app/ + components/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── build_modules.ps1           ← Script to build each module variant
│
├── packaging/                       ← NEW: build scripts
│   ├── biovaram_full.spec          ← PyInstaller spec (full platform)
│   ├── biovaram_nanofacs.spec
│   ├── biovaram_nta.spec
│   ├── biovaram_cross.spec
│   ├── installer.iss               ← Inno Setup script
│   ├── icon.ico
│   └── splash.png
│
├── dist/                            ← Build output
│   ├── BioVaram_Full_Platform.exe
│   ├── BioVaram_NanoFACS.exe
│   ├── BioVaram_NTA.exe
│   └── BioVaram_CrossCompare.exe
│
└── data/                            ← Runtime data (not bundled)
    ├── crmit.db
    ├── uploads/
    ├── parquet/
    └── temp/
```

---

## 10. What NOT to Change

These things should remain exactly as they are:

1. **The React UI** — don't rewrite in Python GUI. The web UI is already polished.
2. **The FastAPI backend** — it works. We're just packaging it differently.
3. **The Mie physics engine** — proven accurate (<1% on beads). Don't touch.
4. **The database schema** — stable, migrated, working.
5. **The calibration pipeline** — validated end-to-end.
6. **Recharts visualizations** — all charts are client-side, work in static export.

The entire modularization is about **packaging and deployment**, not rewriting functionality.

---

## 11. Testing Strategy

### Per-Module Testing

Each module EXE must pass:

| Test | What It Checks |
|------|----------------|
| **Cold start** | Launches on clean Windows PC (no Python/Node installed) |
| **First run** | Creates database, config dirs, default user |
| **Core workflow** | Upload → Parse → Analyze → Export |
| **Data persistence** | Close app → reopen → previous data is there |
| **Cross-module data** | Module 1 uploads file → Module 3 sees it |
| **Port conflict** | Handles port-in-use gracefully |
| **Antivirus** | EXE not flagged by Windows Defender |
| **Large files** | 100 MB FCS file doesn't crash (memory management) |

### Integration Testing

| Test | What It Checks |
|------|----------------|
| **Shared DB** | NanoFACS saves → close → open CrossCompare → data visible |
| **Config sharing** | Calibration done in NanoFACS → available in CrossCompare |
| **Concurrent read** | Open Dashboard (read-only) while NanoFACS is processing |
| **Upgrade** | Install v1.1 over v1.0 → data migrates, nothing lost |

---

## 12. Quick-Start: What to Do This Week

**Immediate actions (this week, Feb 27 – Mar 5):**

1. **Test static export:**
   ```bash
   # In frontend root
   pnpm build     # Does it build with output: 'export'?
   ```
   Identify what breaks and fix it.

2. **Create `run_desktop.py`:**
   FastAPI serves static files + API. One process, one command.

3. **Test PyInstaller on current backend:**
   ```bash
   pip install pyinstaller
   pyinstaller --onefile backend/run_desktop.py
   ```
   See what breaks. Start building the hiddenimports list.

4. **Move AI chat to FastAPI** (if time permits):
   Create `routers/chat.py` that calls the LLM API directly from Python.

By end of this week, you should have: **a single `python run_desktop.py` command that serves both UI and API on localhost:8000.**

---

## 13. Remote Update Strategy — Push Updates Without Resending the EXE

### The Problem

Every time the client gives feedback and we make a change, we don't want to:
- Rebuild the entire 300–400 MB EXE
- Email/upload it to them
- Have them uninstall the old version and reinstall

We want: **the app checks for updates, downloads only what changed, and applies it automatically.**

### How the EXE is Structured (Important for Understanding Updates)

When PyInstaller builds in `--onedir` mode (recommended over `--onefile`), the output looks like:

```
BioVaram/
├── BioVaram.exe              ← ~5 MB launcher (rarely changes)
├── _internal/                ← ~250 MB Python runtime + packages (rarely changes)
│   ├── python313.dll
│   ├── numpy/
│   ├── scipy/
│   ├── miepython/
│   └── ...
├── frontend/                 ← ~15 MB static HTML/CSS/JS (changes frequently)
│   ├── index.html
│   ├── _next/
│   └── ...
├── backend_code/             ← ~5 MB Python source (changes frequently)
│   ├── src/
│   ├── config/
│   └── ...
└── version.json              ← version metadata
```

**Key insight:** Only ~20 MB of the 300 MB package changes between updates (frontend + backend code). The Python runtime and heavy packages (numpy, scipy, etc.) almost never change.

### Update Architecture

```
┌──────────────────┐         ┌──────────────────────────┐
│  Desktop EXE     │         │  Update Server           │
│  (Surya's PC)    │         │  (GitHub Releases /      │
│                  │◄────────│   our server / S3)       │
│  On startup:     │  HTTPS  │                          │
│  1. Check version│────────►│  /api/version            │
│  2. Download diff│◄────────│  /api/update/{version}   │
│  3. Apply patch  │         │  /releases/latest.zip    │
│  4. Restart      │         │                          │
└──────────────────┘         └──────────────────────────┘
```

### Three Update Tiers

We support three types of updates depending on what changed:

#### Tier 1: Frontend-Only Updates (~15 MB download) ⚡ Most Common

**When:** UI bug fixes, new chart, layout tweaks, label changes — anything in `components/`, `app/`, `lib/`

**How it works:**
1. We rebuild the frontend: `pnpm build` → produces `out/` directory
2. We zip the `out/` folder → `frontend_v1.2.0.zip` (~5 MB compressed)
3. Upload to update server (GitHub Release, S3, or our own server)
4. On next launch, the EXE:
   - Calls `GET /api/updates/check?current=1.1.0`
   - Server responds: `{ "latest": "1.2.0", "type": "frontend", "url": "https://...", "size_mb": 5 }`
   - Downloads zip
   - Extracts to `frontend/` folder (replacing old files)
   - Restarts the local server — done!

**User experience:** "Update available (5 MB). Apply now?" → clicks Yes → 10 seconds → back to work.

#### Tier 2: Backend Logic Updates (~5–10 MB download)

**When:** Bug fix in Mie calculation, new API endpoint, parser improvement, database migration

**How it works:**
1. We zip the updated `src/` directory → `backend_v1.3.0.zip`
2. Upload to update server
3. On next launch, the EXE:
   - Downloads zip
   - Extracts to `backend_code/` folder
   - Runs any database migrations (Alembic)
   - Restarts — done!

**Important:** This works because we **keep our Python source code as importable packages outside `_internal/`**, not frozen into the EXE. PyInstaller supports this via `--add-data` with a source code bundle that gets imported at runtime.

#### Tier 3: Full Update (~300 MB download) — Rare

**When:** Python version upgrade, new heavy dependency (new ML model, new physics library), PyInstaller runtime changes

**How it works:**
- Full EXE rebuild + download
- This is the "send a new EXE" scenario, but automated:
  - Download new installer in background
  - Prompt: "A major update is available. Install now?"
  - Run new installer, which replaces everything

**This should be very rare** — maybe once every 2–3 months.

### Implementation: Built-In Update Manager

```python
# backend/src/updater/update_manager.py

import httpx
import zipfile
import shutil
import json
from pathlib import Path

UPDATE_SERVER = "https://updates.biovaram.com"  # or GitHub API
# Alternative: "https://api.github.com/repos/sumitmalhotra-blip/Biovaram_Ev_Analysis_ReactUI/releases/latest"

class UpdateManager:
    def __init__(self, app_dir: Path, current_version: str):
        self.app_dir = app_dir
        self.current_version = current_version
        self.version_file = app_dir / "version.json"
    
    async def check_for_updates(self) -> dict | None:
        """Check if a newer version is available."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{UPDATE_SERVER}/api/updates/check",
                    params={"current": self.current_version, "module": "full"}
                )
                data = resp.json()
                if data.get("update_available"):
                    return {
                        "version": data["latest_version"],
                        "type": data["update_type"],  # "frontend", "backend", "full"
                        "download_url": data["download_url"],
                        "size_mb": data["size_mb"],
                        "changelog": data["changelog"],
                    }
        except Exception:
            pass  # Offline or server down — skip silently
        return None
    
    async def download_and_apply(self, update_info: dict) -> bool:
        """Download update zip and apply it."""
        update_type = update_info["type"]
        url = update_info["download_url"]
        
        # Download to temp
        temp_zip = self.app_dir / "data" / "temp" / "update.zip"
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url) as resp:
                with open(temp_zip, "wb") as f:
                    async for chunk in resp.aiter_bytes(8192):
                        f.write(chunk)
        
        # Apply based on type
        if update_type == "frontend":
            target = self.app_dir / "frontend"
            shutil.rmtree(target, ignore_errors=True)
            with zipfile.ZipFile(temp_zip) as z:
                z.extractall(target)
        
        elif update_type == "backend":
            target = self.app_dir / "backend_code"
            shutil.rmtree(target, ignore_errors=True)
            with zipfile.ZipFile(temp_zip) as z:
                z.extractall(target)
            # Run migrations
            await self._run_migrations()
        
        # Update version file
        with open(self.version_file, "w") as f:
            json.dump({"version": update_info["version"], 
                       "updated_at": str(datetime.now())}, f)
        
        temp_zip.unlink()
        return True  # Signal: restart needed
    
    async def _run_migrations(self):
        """Run any pending database migrations."""
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(str(self.app_dir / "backend_code" / "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
```

### API Endpoints (Added to Each Module)

```python
# backend/src/api/routers/updates.py

@router.get("/updates/check")
async def check_updates():
    """Check for available updates."""
    manager = UpdateManager(APP_DIR, CURRENT_VERSION)
    update = await manager.check_for_updates()
    return {"update_available": update is not None, "update": update}

@router.post("/updates/apply")
async def apply_update():
    """Download and apply the latest update. Returns restart signal."""
    manager = UpdateManager(APP_DIR, CURRENT_VERSION)
    update = await manager.check_for_updates()
    if not update:
        return {"status": "already_latest"}
    
    success = await manager.download_and_apply(update)
    return {"status": "restart_required" if success else "failed"}

@router.get("/updates/version")
async def get_version():
    """Return current version info."""
    return {
        "version": CURRENT_VERSION,
        "module": MODULE_NAME,
        "build_date": BUILD_DATE,
    }
```

### Frontend Update UI

A small notification banner in the header:

```
┌─────────────────────────────────────────────────────────────┐
│ 🔔 Update available: v1.2.0 (5 MB) — "Fixed NTA chart     │
│    labels and improved D50 calculation"                      │
│                              [Update Now]  [Later]          │
└─────────────────────────────────────────────────────────────┘
```

When "Update Now" is clicked:
1. Progress bar shows download
2. Files extracted → "Restarting..."
3. Browser refreshes → user sees new version

### Where to Host Updates

**Option 1: GitHub Releases (Free, Recommended to Start)**

We already have a GitHub repo. Use GitHub Releases as the update server:

```
https://github.com/sumitmalhotra-blip/Biovaram_Ev_Analysis_ReactUI/releases

Release: v1.2.0
  Assets:
    - frontend_v1.2.0.zip     (5 MB)
    - backend_v1.2.0.zip      (3 MB)
    - BioVaram_v1.2.0_full.exe (300 MB)   ← only for major updates
    - changelog.md
```

The update checker calls the GitHub Releases API:
```
GET https://api.github.com/repos/sumitmalhotra-blip/Biovaram_Ev_Analysis_ReactUI/releases/latest
```

Compares `tag_name` with current version → downloads the appropriate asset.

**Pros:** Free, reliable, already integrated with our workflow  
**Cons:** 2 GB asset limit per release (more than enough), rate-limited to 60 req/hr unauthenticated

**Option 2: Our Own Server (Later, More Control)**

A simple FastAPI server running on a VPS:
- `/api/updates/check` — version comparison
- `/api/updates/download/{asset}` — signed download URLs
- Admin panel to push updates selectively (e.g., only to Surya's lab)

**Option 3: AWS S3 + CloudFront (Production Scale)**

For when we have many clients:
- S3 bucket stores update zips
- CloudFront CDN for fast global downloads
- Lambda function handles version checking
- ~$5/month for our scale

### Versioning Convention

```
v[MAJOR].[MINOR].[PATCH]

MAJOR = full rebuild needed (new Python version, new heavy dependency)
MINOR = backend logic change (new feature, new endpoint, physics fix)
PATCH = frontend-only change (UI fix, label change, chart tweak)

Examples:
  v1.0.0 → v1.0.1  = frontend patch (Tier 1, ~5 MB)
  v1.0.1 → v1.1.0  = backend change (Tier 2, ~10 MB)
  v1.1.0 → v2.0.0  = full rebuild   (Tier 3, ~300 MB)
```

### Rollback

If an update breaks something:

```python
# The updater keeps one backup
BACKUP_DIR = app_dir / "backups"

# Before applying update:
shutil.copytree(app_dir / "frontend", BACKUP_DIR / "frontend_backup")

# If user clicks "Rollback" or error detected:
shutil.rmtree(app_dir / "frontend")
shutil.copytree(BACKUP_DIR / "frontend_backup", app_dir / "frontend")
```

Each module stores the previous version as a backup. One-click rollback from the Settings page.

### Update Workflow (Developer Side)

When we get feedback from the client and make changes:

```
1. Fix the code on our dev machine
2. Commit + push to GitHub
3. Run the build script:
   
   # For frontend-only change:
   pnpm build
   zip -r frontend_v1.0.2.zip out/
   gh release create v1.0.2 frontend_v1.0.2.zip --notes "Fixed chart labels"
   
   # For backend change:
   zip -r backend_v1.1.0.zip backend/src/
   gh release create v1.1.0 backend_v1.1.0.zip --notes "Improved Mie calculation"
   
4. Done! Next time Surya launches the app, he sees "Update available"
```

Total time from fix to client: **< 5 minutes** (vs. rebuilding and re-sending a 300 MB EXE).

### Offline Machines

If Surya's lab PC has no internet:
- Update check silently fails → app works normally
- We can provide a USB stick with the update zip
- The app has a "Manual Update" option: browse to a zip file → apply

```python
@router.post("/updates/manual")
async def manual_update(file: UploadFile):
    """Apply an update from a local zip file."""
    # Save uploaded zip, validate, extract, apply
    ...
```

### Summary: Update Delivery Matrix

| Change Type | Download Size | User Action | Downtime |
|-------------|--------------|-------------|----------|
| UI fix (colors, labels, layout) | ~5 MB | Click "Update" | ~10 sec |
| New chart / new tab | ~5 MB | Click "Update" | ~10 sec |
| Physics fix (Mie, calibration) | ~8 MB | Click "Update" | ~15 sec |
| New API endpoint | ~8 MB | Click "Update" | ~15 sec |
| Database schema change | ~8 MB | Click "Update" (auto-migrates) | ~20 sec |
| New Python dependency | ~300 MB | Download new EXE | ~5 min |
| Python version upgrade | ~300 MB | Download new EXE | ~5 min |

**Bottom line:** 90%+ of updates will be Tier 1 or Tier 2 — under 10 MB, applied in seconds, no new EXE needed.

---

*This plan will be updated as we progress through each phase. Each deliverable will be tested with Surya in the lab before moving to the next phase.*
