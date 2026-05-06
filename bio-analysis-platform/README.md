# BioLab Analysis Platform

A desktop application for automated analysis of **Transmission Electron Microscopy (TEM)** images and **Western Blot** gels, built with Electron, React, and a Python FastAPI backend.

---

## Overview

BioLab Analysis Platform provides researchers with a unified desktop tool to:

- **TEM Module** - Upload TEM microscopy images (PNG, JPG, TIFF), automatically detect and classify extracellular vesicles (EVs) as intact, non-intact, or needs-review using CNN or rule-based engines, measure particle diameters in nanometres, and export results.
- **Western Blot Module** - Upload Western blot gel images, mark the molecular-weight ladder (lane 0), detect protein bands, interpolate kDa values from the ladder, quantify band concentrations, and export a CSV report.

---

## Purpose

Analysing TEM and Western Blot images manually is time-consuming and subjective. This platform automates the detection and classification pipeline, giving researchers consistent, reproducible measurements with interactive tools to review and correct the results.

---

## Use Cases

| Module | Who Uses It | How |
|---|---|---|
| TEM | Cell biology researchers | Upload TEM images, auto-detect vesicles, review/edit circles, export particle data |
| Western Blot | Protein researchers | Upload gel image, mark ladder lane, enter kDa values, detect bands, export CSV |

---

## Prerequisites

| Tool | Minimum Version | Notes |
|---|---|---|
| **Node.js** | 20.x LTS | Required for frontend build and Electron |
| **npm** | 10.x | Comes with Node.js |
| **Python** | 3.10 - 3.11 | Python 3.12+ is not supported by TensorFlow 2.15 |
| **Git** | Any recent | For cloning the repository |

---

## Cloning the Repository

`ash
git clone https://github.com/dineshchandran/bio-analysis-platform.git
cd bio-analysis-platform
`

---

## Project Structure

`
bio-analysis-platform/
|-- electron/                         # Electron shell (main.js, builder config)
|-- frontend/
|   |-- western-blot-frontend/        # React + TypeScript UI (Vite)
|       |-- src/
|           |-- components/
|           |   |-- tem/              # TEM canvas, particle tools
|           |   |-- western/          # Western Blot analysis UI
|           |-- services/api.ts       # API base URL configuration
|-- backend/
|   |-- main.py                       # FastAPI app with router registration
|   |-- backend_service.py            # Entry point: port discovery + uvicorn
|   |-- requirements.txt              # Python dependencies
|   |-- routers/
|   |   |-- tem_routes.py             # TEM API endpoints
|   |   |-- western_routes.py         # Western Blot API endpoints
|   |-- services/
|       |-- tem/                      # TEM analysis engines (CNN, rule-based)
|       |-- western/                  # Western Blot band detection service
|-- package.json                      # Root Electron scripts and builder config
|-- README.md
`

---

## Installation

### 1. Install Python dependencies

`ash
cd backend
pip install -r requirements.txt
`

> **Note:** tensorflow==2.15.0 and keras==2.15.0 are pinned. Use Python 3.10 or 3.11.
> A CUDA-compatible GPU is optional - the app falls back to CPU automatically.

### 2. Install frontend dependencies

`ash
cd frontend/western-blot-frontend
npm install
`

### 3. Install Electron / root dependencies

`ash
cd ../..
npm install
`

---

## Running the Application

### Development mode

Open **two terminals**:

**Terminal 1 - Start the backend**
`ash
cd backend
python backend_service.py
`
The backend auto-selects a free port starting at 8000 and prints:
`
BACKEND_PORT:8000
INFO:     Uvicorn running on http://127.0.0.1:8000
`

**Terminal 2 - Start the frontend dev server**
`ash
cd frontend/western-blot-frontend
npm run dev
`
Vite serves the UI at http://localhost:5173.

Then launch the Electron window (optional):
`ash
npm run electron:dev
`

### Production mode (Electron app)

`ash
# 1. Build the frontend
npm run build:frontend

# 2. Launch the packaged desktop app
npx electron .
`

---

## Building the Installer (EXE)

`ash
# Full release build from the repository root
npm run release

# Or just the Windows installer
npm run build:installer
`

The output installer is placed in dist/.

### Build steps

1. npm run build:frontend - compiles React/TypeScript to frontend/western-blot-frontend/dist/
2. electron-builder --win --x64 - bundles Electron, compiled frontend, and BioLabBackend.exe

> **Before building locally**, package the Python backend with PyInstaller:
> `ash
> cd backend
> pyinstaller backend_service.py --onefile --name BioLabBackend
> `
> Copy dist/BioLabBackend.exe to the path referenced in electron/package.json.

---

## Configuration

### API base URLs

Edit frontend/western-blot-frontend/src/services/api.ts to change the backend host/port for development.

### Backend port

The backend auto-discovers a free port starting at **8000**. In development, create a .env file inside frontend/western-blot-frontend/:
`
VITE_BACKEND_URL=http://127.0.0.1:8000
`

### TEM analysis method

Default method is **cnn** (deep learning). Switch to **rulebased** or **voronoi** via the dropdown in the TEM right sidebar.

### Database

TEM results are stored in **SQLite** (backend/biolab.db). Created automatically on first run. No setup required.

---

## Key Features

### TEM Module
- Upload multiple images (PNG, JPG, TIFF - up to 5 files, 5 MB each)
- Auto-detect extracellular vesicles using CNN or rule-based engines
- Interactive canvas: add, move, resize, and delete particle circles
- Circle resize clamped so particles cannot fall below the Hide particles below threshold
- Minimum Hide particles below value enforced at **30 nm**
- Set image scale (nm/pixel) by drawing a line on the scale bar
- Filter particles below a size threshold
- Intensity line tool for radial intensity profiling
- Shape classification with AI-assisted feedback
- Particle table view with intact / non-intact / needs-review categories
- Zoom (Ctrl + scroll) and pan (Space + drag)

### Western Blot Module
- Upload gel images (PNG, JPG, TIFF)
- Mark molecular-weight ladder lane by drawing top/bottom boundaries
- Automatic ruler band detection via peak analysis
- Enter kDa and concentration values per ladder band
- Full band analysis with annotated image and concentration plot
- Logarithmic kDa interpolation between ladder bands
- Manual band placement with automatic kDa interpolation
- CSV report export for selected bands

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| TIFF images not displaying | Browser cannot render TIFF natively | Fixed via UTIF decode in this version |
| Backend fails to start | Missing Python packages | pip install -r backend/requirements.txt |
| tensorflow install error | Python version > 3.11 | Use Python 3.10 or 3.11 |
| Port 8000 in use | Another process | Backend auto-selects next free port |
| EXE not launching backend | PyInstaller build missing | Build BioLabBackend.exe before npm run build:installer |
| Canvas blank after upload | TIFF still decoding | Wait 1-2 s, TIFF decode is async |

---

## License

Internal use - CRMIT Solutions. All rights reserved.