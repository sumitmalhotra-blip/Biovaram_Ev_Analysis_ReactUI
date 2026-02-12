# BioVaram EV Analysis Platform — Desktop Packaging & Licensing Plan

**Created:** February 12, 2026  
**Target Delivery:** March 1st week, 2026 (~2.5 weeks)  
**Objective:** Package the web-based platform as a standalone Windows EXE with per-module licensing

---

## Executive Summary

Convert the current Next.js + FastAPI web platform into a **single downloadable Windows installer** (.exe) that:
1. Runs entirely offline (no cloud dependency)
2. Enforces per-module licensing (client pays for NTA only → sees only NTA)
3. Bundles everything: Python backend, Next.js frontend, SQLite database, all dependencies
4. One-click install, one-click launch — no Node.js/Python required on client machine

---

## Architecture Decision: Electron + Embedded Python

### Why Electron (not Tauri/PyWebView/CEF)?

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Electron** | Proven at scale, excellent Next.js integration, mature packaging (electron-builder), auto-updates | ~150MB Chromium bundle | **CHOSEN** — fastest path to March deadline |
| Tauri | Smaller binary (~10MB), Rust-based | Needs Rust toolchain, SSR challenges with Next.js, less mature ecosystem | Too risky for 2.5-week timeline |
| PyWebView | Native webview, smallest bundle | Limited API, no DevTools, poor state management | Insufficient for our UI complexity |
| CEF (Chromium Embedded) | Flexible | C++ integration, no built-in packaging pipeline | Over-engineered for this use case |

### Final Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 BioVaram EV Analyzer.exe                 │
│  (Electron main process)                                │
│                                                         │
│  ┌─────────────────────┐  ┌──────────────────────────┐  │
│  │   Next.js Frontend  │  │   Python Backend (.exe)  │  │
│  │   (Static Export)   │  │   (PyInstaller bundle)   │  │
│  │                     │  │                          │  │
│  │  Loaded in Electron │  │  Spawned as child        │  │
│  │  BrowserWindow via  │  │  process on app start    │  │
│  │  file:// or local   │  │  Port: 18234 (random)    │  │
│  │  http server        │  │                          │  │
│  │                     │  │  ┌────────────────────┐  │  │
│  │  ┌───────────────┐  │  │  │ SQLite DB          │  │  │
│  │  │ License Gate  │  │  │  │ (in %APPDATA%)     │  │  │
│  │  │ Module Filter │  │  │  │                    │  │  │
│  │  └───────────────┘  │  │  └────────────────────┘  │  │
│  └─────────────────────┘  └──────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  License Manager (Electron main process)         │    │
│  │  - Reads license key from %APPDATA%/license.key  │    │
│  │  - Validates signature (RSA/Ed25519)             │    │
│  │  - Exposes enabled modules to renderer           │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## Part 1: Licensable Module Definition

### Module Catalog

Based on the codebase analysis, we define **5 licensable modules**:

| Module ID | Display Name | What's Included | Can Be Standalone? |
|-----------|-------------|------------------|--------------------|
| `fcs` | Flow Cytometry Analysis | FCS upload, scatter plots, Mie sizing, anomaly detection, gated analysis, bead calibration | **Yes** |
| `nta` | Nanoparticle Tracking (NTA) | NTA/PDF upload, size distribution, position analysis, temperature settings | **Yes** |
| `cross_compare` | Cross-Compare | FCS vs NTA comparison, statistical tests, validation verdicts | No — requires `fcs` + `nta` |
| `research_chat` | AI Research Assistant | AI chat with context awareness, sample data queries | No — requires at least one data module |
| `dashboard` | Advanced Dashboard | Pinned charts, saved images, AI insights widget | **Free** — always included |

### License Tiers (Business Model)

| Tier | Modules Included | Use Case |
|------|-----------------|----------|
| **NTA Basic** | `dashboard` + `nta` | Client only does NTA measurements |
| **FCS Basic** | `dashboard` + `fcs` | Client only does flow cytometry |
| **Analysis Suite** | `dashboard` + `fcs` + `nta` + `cross_compare` | Full analytical workflow |
| **Enterprise** | All modules | Everything including AI assistant |

### Module Dependencies (Enforced)

```
cross_compare  →  requires: [fcs, nta]
research_chat  →  requires: [fcs OR nta]  (at least one data module)
dashboard      →  requires: []  (always available)
fcs            →  requires: []
nta            →  requires: []
```

---

## Part 2: License Key System Design

### License Key Format

```
BIOVARAM-XXXX-XXXX-XXXX-XXXX
```

**Internally, this is a signed JSON payload (base64-encoded):**

```json
{
  "license_id": "LIC-2026-00001",
  "customer": "University of Melbourne",
  "email": "lab@unimelb.edu.au",
  "modules": ["fcs", "nta", "cross_compare"],
  "tier": "analysis_suite",
  "issued_at": "2026-03-01T00:00:00Z",
  "expires_at": "2027-03-01T00:00:00Z",
  "max_users": 5,
  "machine_id": null,
  "signature": "... Ed25519 signature ..."
}
```

### Validation Flow

```
App Start → Read license.key from %APPDATA%/BioVaram/
          → Decode base64 → Parse JSON payload
          → Verify Ed25519 signature with embedded PUBLIC key
          → Check expiry date
          → Check machine_id (if hardware-locked)
          → Extract enabled modules list
          → Pass to frontend via Electron IPC / backend config
```

### Key Properties

- **Offline-capable** — no license server needed (signature verification only)
- **Tamper-proof** — Ed25519 signature; public key embedded in app, private key stays at BioVaram HQ
- **Time-limited** — `expires_at` field enforces annual renewal
- **Optional hardware lock** — `machine_id` field can tie license to specific machine
- **No internet required** after initial activation

---

## Part 3: Implementation Plan — File-by-File Changes

### Phase A: License System (Days 1-3)

#### A1. Backend License Module

**New file: `backend/src/licensing/__init__.py`**
```python
# License constants and module definitions
```

**New file: `backend/src/licensing/license_manager.py`**
```python
"""
Offline license validation using Ed25519 signatures.

- Reads license key file
- Verifies cryptographic signature
- Returns enabled modules list
- Caches validation result in memory
"""
class LicenseManager:
    MODULES = {
        'dashboard': {'name': 'Dashboard', 'always_free': True, 'dependencies': []},
        'fcs': {'name': 'Flow Cytometry', 'always_free': False, 'dependencies': []},
        'nta': {'name': 'NTA Analysis', 'always_free': False, 'dependencies': []},
        'cross_compare': {'name': 'Cross-Compare', 'always_free': False, 'dependencies': ['fcs', 'nta']},
        'research_chat': {'name': 'AI Research Chat', 'always_free': False, 'dependencies': []},
    }

    def validate_license(self, license_path: str) -> LicenseInfo
    def get_enabled_modules(self) -> list[str]
    def is_module_enabled(self, module_id: str) -> bool
```

**New file: `backend/src/licensing/keygen.py`** (internal tool, not shipped)
```python
"""
License key generator — used by BioVaram sales team only.
Signs license payloads with Ed25519 PRIVATE key.
Generates BIOVARAM-XXXX-XXXX-XXXX-XXXX formatted keys.
"""
def generate_license(customer, modules, expires_at, private_key) -> str
```

#### A2. Backend API Enforcement

**Modified: `backend/src/api/main.py`**
- Load license on startup → store in app state
- New endpoint: `GET /api/v1/license/status` → returns enabled modules
- New middleware: `require_module(module_id)` dependency

**Modified: `backend/src/api/routers/samples.py`**
- FCS endpoints: wrap with `Depends(require_module("fcs"))`
- NTA endpoints: wrap with `Depends(require_module("nta"))`

**Modified: `backend/src/api/routers/upload.py`**
- `POST /upload/fcs`: guard with `require_module("fcs")`
- `POST /upload/nta`: guard with `require_module("nta")`

**Modified: `backend/src/api/routers/analysis.py`**
- Statistical tests: guard with `require_module("cross_compare")`

#### A3. Frontend License Gate

**New file: `lib/license.ts`**
```typescript
// License context provider
// Fetches enabled modules from backend on app init
// Provides useLicense() hook

interface LicenseInfo {
  customer: string;
  tier: string;
  modules: string[];       // ['fcs', 'nta', 'cross_compare']
  expiresAt: string;
  isValid: boolean;
}

export function useLicense(): LicenseInfo
export function useModuleEnabled(moduleId: string): boolean
```

**New file: `components/license-gate.tsx`**
```tsx
// Wrapper component that conditionally renders children
// <LicenseGate module="nta"> ... NTA content ... </LicenseGate>
// Shows "Module not licensed" placeholder if disabled
```

**Modified: `components/tab-navigation.tsx`**
- Filter visible tabs based on licensed modules
- NTA tab hidden if `nta` not in license
- FCS tab hidden if `fcs` not in license
- Cross-Compare hidden if `cross_compare` not in license

**Modified: `components/sidebar.tsx`**
- Hide module-specific sidebar panels for unlicensed modules

**Modified: `app/page.tsx`**
- Wrap each tab's content in `<LicenseGate module="...">`
- Show license activation prompt if no valid license

**New file: `components/license-activation.tsx`**
```tsx
// License key input dialog
// Paste BIOVARAM-XXXX-XXXX-XXXX-XXXX key
// Sends to backend for validation
// Stores in %APPDATA% via Electron IPC or local file
```

---

### Phase B: Desktop Packaging with Electron (Days 4-8)

#### B1. Next.js Static Export Conversion

The current app uses Next.js SSR features (API routes, server components). For Electron packaging, we need to convert to **static export** mode since the Python backend handles all API calls.

**Modified: `next.config.mjs`**
```javascript
const nextConfig = {
  output: 'export',           // Static HTML/JS/CSS export
  distDir: 'out',             // Output to ./out
  trailingSlash: true,        // Required for static export
  images: { unoptimized: true }, // No Next.js image optimization server
  // ... existing config
}
```

**Key conversion tasks:**
- `app/api/research/chat/route.ts` → Must be moved to backend (FastAPI endpoint) since Next.js API routes don't work in static export
- `app/layout.tsx` → Remove any server-only imports
- `lib/auth.ts` (NextAuth) → Replace with direct JWT auth against backend (NextAuth requires a server)

**Modified: `lib/auth.ts`** → **New: `lib/auth-desktop.ts`**
```typescript
// Replace NextAuth with direct JWT token management
// Login → POST /api/v1/auth/login → receive JWT → store in localStorage
// All API calls include Authorization: Bearer <jwt>
// Session management via Zustand store
```

**Modified: `app/api/research/chat/route.ts`** → Move AI chat to backend
```python
# New backend endpoint: POST /api/v1/research/chat
# Handles AI provider calls server-side (OpenAI/Anthropic)
# Streams response back to client via SSE
```

#### B2. Electron Shell

**New directory structure:**
```
electron/
  main.js              # Electron main process
  preload.js           # Secure bridge between main/renderer
  package.json         # Electron app metadata
  icon.ico             # App icon (BioVaram logo)
  build/
    installer.nsh      # NSIS installer customization
```

**New file: `electron/main.js`**
```javascript
const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');

let backendProcess = null;
let mainWindow = null;
const BACKEND_PORT = 18234;

// Find free port, start Python backend, wait for health check, load UI
app.whenReady().then(async () => {
  // 1. Start Python backend
  const backendPath = path.join(process.resourcesPath, 'backend', 'biovaram-backend.exe');
  backendProcess = spawn(backendPath, ['--port', BACKEND_PORT, '--no-browser']);

  // 2. Wait for backend health check
  await waitForBackend(`http://localhost:${BACKEND_PORT}/health`);

  // 3. Create window and load frontend
  mainWindow = new BrowserWindow({
    width: 1400, height: 900,
    title: 'BioVaram EV Analyzer',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    }
  });

  // Load static export
  mainWindow.loadFile(path.join(process.resourcesPath, 'frontend', 'index.html'));

  // 4. Handle license IPC
  ipcMain.handle('get-license', () => readLicenseFile());
  ipcMain.handle('activate-license', (event, key) => saveLicenseKey(key));
});

// Clean shutdown
app.on('before-quit', () => {
  if (backendProcess) backendProcess.kill();
});
```

**New file: `electron/preload.js`**
```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('biovaram', {
  getLicense: () => ipcRenderer.invoke('get-license'),
  activateLicense: (key) => ipcRenderer.invoke('activate-license', key),
  getBackendUrl: () => `http://localhost:18234`,
  platform: 'desktop',
  version: '1.0.0',
});
```

#### B3. Python Backend PyInstaller Bundling

**New file: `backend/biovaram.spec`** (PyInstaller spec)
```python
# PyInstaller configuration
# Bundles: Python 3.13 + all pip packages + src/ code + config/ + miepython
# Output: single-directory distribution (faster startup than single-file)

a = Analysis(
    ['run_api.py'],
    pathex=['.'],
    datas=[
        ('config/', 'config/'),
        ('src/', 'src/'),
        ('alembic/', 'alembic/'),
        ('alembic.ini', '.'),
    ],
    hiddenimports=[
        'uvicorn.logging', 'uvicorn.protocols.http',
        'aiosqlite', 'miepython', 'flowio', 'fcsparser',
        'sklearn', 'scipy.optimize', 'scipy.stats',
        'pdfplumber', 'jose', 'passlib',
    ],
)
```

**Modified: `backend/run_api.py`**
- Accept `--port` CLI argument
- Accept `--license-path` CLI argument
- Resolve paths relative to `sys._MEIPASS` when running as PyInstaller bundle
- Create `%APPDATA%/BioVaram/data/` for database and uploads

**Modified: `backend/src/api/config.py`**
```python
# Add desktop-aware path resolution
import sys

def get_data_dir() -> Path:
    """Returns writable data directory: %APPDATA%/BioVaram/ in desktop mode"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        return Path(os.environ['APPDATA']) / 'BioVaram'
    return Path('.')  # Dev mode: current directory
```

#### B4. Electron-Builder Configuration

**New file: `electron/package.json`**
```json
{
  "name": "biovaram-ev-analyzer",
  "version": "1.0.0",
  "description": "BioVaram Extracellular Vesicle Analysis Platform",
  "main": "main.js",
  "author": "BioVaram",
  "build": {
    "appId": "com.biovaram.ev-analyzer",
    "productName": "BioVaram EV Analyzer",
    "win": {
      "target": ["nsis"],
      "icon": "icon.ico"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true,
      "installerIcon": "icon.ico"
    },
    "extraResources": [
      {
        "from": "../backend/dist/biovaram-backend/",
        "to": "backend/",
        "filter": ["**/*"]
      },
      {
        "from": "../out/",
        "to": "frontend/",
        "filter": ["**/*"]
      }
    ],
    "files": ["main.js", "preload.js"]
  },
  "dependencies": {
    "electron": "^34.0.0"
  },
  "devDependencies": {
    "electron-builder": "^25.0.0"
  }
}
```

---

### Phase C: Auth Adaptation for Desktop (Days 9-10)

In desktop mode, authentication works differently:

| Web Mode (Current) | Desktop Mode (New) |
|--------------------|--------------------|
| NextAuth v5 with server sessions | Direct JWT against FastAPI backend |
| `app/api/auth/[...nextauth]/` API route | Not used (static export) |
| Session stored in HTTP cookie | JWT stored in localStorage |
| Server-side session validation | Client-side token check + backend validation |

**Key changes:**

**New: `lib/api-client-desktop.ts`**
```typescript
// Override ApiClient.baseUrl to use localhost backend port
// Override auth header to use stored JWT token
// Auto-detect desktop mode via window.biovaram?.platform === 'desktop'
```

**Modified: `lib/api-client.ts`**
```typescript
// Add desktop detection:
const getBaseUrl = () => {
  if (typeof window !== 'undefined' && (window as any).biovaram?.getBackendUrl) {
    return (window as any).biovaram.getBackendUrl();
  }
  return 'http://localhost:8000';  // Dev fallback
};
```

**Modified: `components/session-provider.tsx`**
- In desktop mode, skip NextAuth SessionProvider
- Use Zustand-based auth state instead

---

### Phase D: Build Pipeline & Testing (Days 11-14)

#### D1. Build Scripts

**New file: `scripts/build-desktop.ps1`** (master build script)
```powershell
# 1. Build Next.js static export
Write-Host "Building frontend..."
pnpm build                    # output: ./out/

# 2. Bundle Python backend with PyInstaller
Write-Host "Bundling backend..."
cd backend
.\venv\Scripts\pyinstaller.exe biovaram.spec --noconfirm
cd ..                           # output: backend/dist/biovaram-backend/

# 3. Package with electron-builder
Write-Host "Packaging installer..."
cd electron
npm run build                   # output: electron/dist/BioVaram EV Analyzer Setup.exe
cd ..

Write-Host "Done! Installer at: electron/dist/"
```

#### D2. File Size Estimates

| Component | Estimated Size |
|-----------|---------------|
| Electron + Chromium | ~150 MB |
| Next.js static export | ~15 MB |
| Python backend (PyInstaller) | ~200 MB (numpy, scipy, sklearn, pandas, miepython) |
| **Total installer** | **~350-400 MB** |

*Note: Can be reduced to ~250MB with UPX compression on PyInstaller output.*

#### D3. Testing Matrix

| Test | What to verify |
|------|---------------|
| Fresh install | Installer runs, creates desktop shortcut, first launch works |
| License activation | Paste key → modules appear → restart preserves license |
| NTA-only license | Only NTA tab visible, FCS upload rejected with clear message |
| FCS-only license | Only FCS tab visible, NTA upload rejected |
| Full license | All tabs visible and functional |
| Expired license | Shows "License expired" dialog with renewal instructions |
| No license | Shows activation prompt, only dashboard accessible |
| Data persistence | Upload FCS → close app → reopen → data still there |
| Backend crash recovery | Kill backend process → app detects → auto-restarts backend |
| Offline operation | Disconnect internet → everything works (except AI chat if cloud-based) |
| Windows 10/11 | Test on both OS versions |

---

## Part 4: Detailed Sprint Plan (Feb 12 → Mar 7)

### Week 1 (Feb 12-18): Foundation

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| Thu-Fri (12-13) | License system backend: `LicenseManager`, Ed25519 signing, `keygen.py` | Backend | License validation working in tests |
| Sat-Sun (14-15) | Backend API guards: `require_module()` middleware on all routers | Backend | Unlicensed module calls return 403 |
| Mon (16) | Frontend license gate: `useLicense()` hook, `<LicenseGate>` component | Frontend | Tabs filtered by license |
| Tue (17) | License activation UI: input dialog, settings page | Frontend | User can paste license key |
| Wed (18) | Next.js static export conversion: remove server features, move AI chat to backend | Fullstack | `pnpm build` produces `out/` |

### Week 2 (Feb 19-25): Packaging

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| Thu (19) | Auth refactor: replace NextAuth with direct JWT for desktop mode | Fullstack | Login/signup works without NextAuth server |
| Fri (20) | Electron shell: `main.js`, `preload.js`, backend process management | Desktop | Electron loads static frontend + starts backend |
| Sat-Sun (21-22) | PyInstaller bundling: spec file, hidden imports, path resolution for frozen mode | Backend | `biovaram-backend.exe` runs standalone |
| Mon (23) | Electron-builder: NSIS installer, resource bundling, icon | Desktop | `Setup.exe` installs on clean Windows machine |
| Tue (24) | Desktop data paths: `%APPDATA%/BioVaram/` for DB, uploads, license | Fullstack | Data persists across app restarts |
| Wed (25) | Integration testing: full license + packaging flow | QA | End-to-end test on clean VM |

### Week 3 (Feb 26 - Mar 4): Polish & Delivery

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| Thu (26) | Bug fixes from integration testing | Fullstack | All critical bugs resolved |
| Fri (27) | Auto-update mechanism (optional: electron-updater) | Desktop | App checks for updates on launch |
| Sat-Sun (28-1) | Splash screen, about dialog, error handling polish | Frontend | Professional first-impression |
| Mon (2) | Generate first batch of client license keys | Business | License keys for pilot clients |
| Tue (3) | Final testing on clean Windows 10/11 machines | QA | Installer verified on 2+ machines |
| Wed (4) | Documentation: install guide, license activation guide | Docs | Client-facing documentation |

---

## Part 5: Files to Create/Modify Summary

### New Files (18 files)

| File | Purpose |
|------|---------|
| `backend/src/licensing/__init__.py` | Licensing module init |
| `backend/src/licensing/license_manager.py` | License validation (Ed25519) |
| `backend/src/licensing/keygen.py` | License key generator (internal) |
| `backend/src/licensing/models.py` | License data models |
| `backend/biovaram.spec` | PyInstaller spec file |
| `electron/main.js` | Electron main process |
| `electron/preload.js` | Electron preload script |
| `electron/package.json` | Electron app config + builder config |
| `electron/icon.ico` | App icon |
| `electron/build/installer.nsh` | NSIS installer customization |
| `lib/license.ts` | Frontend license hook + context |
| `lib/auth-desktop.ts` | JWT-only auth for desktop mode |
| `components/license-gate.tsx` | Module visibility wrapper |
| `components/license-activation.tsx` | License key input UI |
| `components/license-status.tsx` | License info display (settings) |
| `scripts/build-desktop.ps1` | Master build script |
| `scripts/build-backend.ps1` | PyInstaller build script |
| `scripts/generate-license.py` | License generation CLI tool |

### Modified Files (14 files)

| File | Changes |
|------|---------|
| `next.config.mjs` | Add `output: 'export'`, disable image optimization |
| `package.json` | Add electron dev scripts, electron dependency |
| `app/page.tsx` | Wrap tabs in `<LicenseGate>`, add license activation |
| `app/layout.tsx` | Conditional SessionProvider (web vs desktop) |
| `components/tab-navigation.tsx` | Filter tabs by licensed modules |
| `components/sidebar.tsx` | Hide unlicensed module panels |
| `components/session-provider.tsx` | Desktop-mode auth bypass |
| `lib/api-client.ts` | Dynamic `baseUrl` for desktop mode |
| `lib/store.ts` | Add license state slice |
| `backend/run_api.py` | CLI args for port, license-path, frozen-mode paths |
| `backend/src/api/main.py` | Load license on startup, add `/license/status` endpoint |
| `backend/src/api/config.py` | Desktop-aware data directory resolution |
| `backend/src/api/routers/upload.py` | Add `require_module()` guards |
| `backend/src/api/routers/samples.py` | Add `require_module()` guards on FCS/NTA endpoints |

---

## Part 6: Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| PyInstaller misses hidden imports | Backend crashes on client machine | Exhaustive testing on clean VM; maintain `hiddenimports` list |
| Next.js static export breaks features | Pages don't render correctly | Early conversion (Week 1); test every tab in export mode |
| NextAuth removal breaks login | Users can't authenticate | Keep web-mode NextAuth; separate desktop auth path |
| Large installer size (~400MB) | Client download time | UPX compression; split installer into modules (advanced) |
| AI Research Chat needs cloud API key | Won't work offline | Make it optional/licensable; clearly document cloud requirement |
| Windows Defender false positive | Installer blocked | Code-sign with EV certificate ($300-500/year) |
| Antivirus blocks child process spawn | Backend won't start | Document exclusion; use signed binaries |

---

## Part 7: Key Technical Decisions Needed

### Decision 1: AI Chat in Desktop Mode
- **Option A:** Require internet + API key from client → AI chat works with cloud provider
- **Option B:** Bundle a small local LLM (e.g., Phi-3-mini via llama.cpp) → ~2GB extra, fully offline
- **Option C:** Disable AI chat in desktop mode entirely → simplest
- **Recommended:** Option A for March launch, Option B as future roadmap

### Decision 2: Auto-Updates
- **Option A:** electron-updater with GitHub Releases → automatic background updates
- **Option B:** Manual download of new installer from website
- **Recommended:** Option B for March launch (simpler), Option A for v1.1

### Decision 3: Multi-User on Same Machine
- **Option A:** Each Windows user gets separate data + license → `%APPDATA%` per-user
- **Option B:** Shared installation, shared data → `%PROGRAMDATA%`
- **Recommended:** Option A (per-user `%APPDATA%` — more secure, license per user)

### Decision 4: Code Signing
- **Option A:** Sign with EV code signing certificate → no SmartScreen warning
- **Option B:** Don't sign → Windows SmartScreen "unknown publisher" warning
- **Recommended:** Option A before shipping to clients (costs ~$300-500/year)

---

## Part 8: Post-March Roadmap

| Feature | Timeline | Description |
|---------|----------|-------------|
| Auto-update system | March 2026 | electron-updater with version checks |
| macOS build | April 2026 | Electron supports macOS natively; PyInstaller macOS bundle |
| Linux build | April 2026 | AppImage or .deb packaging |
| Online license activation | April 2026 | Phone-home activation server for easier key distribution |
| Floating licenses | Q3 2026 | License server for concurrent user count licensing |
| Plugin system | Q3 2026 | Allow third-party analysis modules |
| Local LLM for AI chat | Q4 2026 | Offline AI assistant using quantized models |

---

## Quick Start: How to Begin Development

```powershell
# Step 1: Install Electron dev dependencies
cd electron
npm init -y
npm install electron --save
npm install electron-builder --save-dev

# Step 2: Install PyInstaller in backend venv
cd ..\backend
.\venv\Scripts\pip.exe install pyinstaller

# Step 3: Install Ed25519 signing library
.\venv\Scripts\pip.exe install PyNaCl  # for Ed25519 signatures

# Step 4: Test static export
cd ..
npx next build  # with output: 'export' in next.config.mjs

# Step 5: Test PyInstaller bundle
cd backend
.\venv\Scripts\pyinstaller.exe --onedir run_api.py --name biovaram-backend
```
