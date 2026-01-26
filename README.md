# BioVaram EV Analysis Platform

[![Node.js 18+](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-teal.svg)](https://fastapi.tiangolo.com/)

A comprehensive platform for analyzing **Extracellular Vesicles (EVs/Exosomes)** using Flow Cytometry (FCS) and Nanoparticle Tracking Analysis (NTA) data.

**Client:** BioVaram via CRMIT  
**Application:** iPSC-derived exosome characterization for therapeutics

---

## 📖 Table of Contents

1. [Quick Start](#-quick-start)
2. [Architecture Overview](#-architecture-overview)
3. [Project Structure](#-project-structure)
4. [For New Developers](#-for-new-developers)
5. [Key Features](#-key-features)
6. [Documentation Index](#-documentation-index)

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **Node.js** | 18+ | Frontend (React/Next.js) |
| **Python** | 3.10+ | Backend (FastAPI) |
| **PostgreSQL** | 15+ | Database (optional for dev) |

### Step 1: Clone & Install

```powershell
# Clone repository
git clone https://github.com/sumitmalhotra-blip/Biovaram_Ev_Analysis_ReactUI.git
cd Biovaram_Ev_Analysis_ReactUI

# Install frontend dependencies
npm install

# Setup Python backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
```

### Step 2: Start the Platform

**Option A: One-Command Start (Windows)**
```powershell
.\start.ps1
```

**Option B: Manual Start (Two Terminals)**

```powershell
# Terminal 1: Backend API
cd backend
.\venv\Scripts\Activate.ps1
python run_api.py

# Terminal 2: Frontend
npm run dev
```

### Step 3: Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| **Web UI** | http://localhost:3000 | Main application |
| **API Docs** | http://localhost:8000/docs | Swagger documentation |
| **API Health** | http://localhost:8000/health | Health check |

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT BROWSER                                  │
│                    (React/Next.js Frontend)                            │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ HTTP/REST
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      BACKEND API (FastAPI)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   /upload    │  │   /samples   │  │   /results   │                  │
│  │  FCS & NTA   │  │  CRUD ops    │  │  Analysis    │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    PARSERS      │  │    PHYSICS      │  │  VISUALIZATION  │
│  FCS Parser     │  │  Mie Scattering │  │  Plot Generators│
│  NTA Parser     │  │  Calibration    │  │  Size Histograms│
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   + Parquet     │
                    └─────────────────┘
```

### Data Flow

1. **User uploads FCS/NTA file** → Frontend
2. **Frontend sends to API** → `/api/v1/upload/fcs` or `/api/v1/upload/nta`
3. **Parser extracts data** → Converts to DataFrame
4. **Physics module calculates sizes** → Mie theory or calibration
5. **Results stored** → PostgreSQL (metadata) + Parquet (raw data)
6. **Visualization generated** → Size distributions, scatter plots
7. **Results returned** → JSON to frontend for display

---

## 📁 Project Structure

```
ev-analysis-platform/
│
├── 📱 FRONTEND (Next.js/React)
│   ├── app/                    # Next.js pages (App Router)
│   │   ├── page.tsx           # Main dashboard
│   │   ├── (auth)/            # Login/signup pages
│   │   └── api/               # API routes (proxies)
│   │
│   ├── components/             # React components
│   │   ├── flow-cytometry/    # FCS analysis components
│   │   ├── nta/               # NTA analysis components
│   │   ├── cross-compare/     # Comparison tools
│   │   ├── charts/            # Recharts visualizations
│   │   └── ui/                # Shadcn/UI components
│   │
│   ├── lib/                    # Utilities
│   │   ├── api-client.ts      # Backend API client
│   │   ├── auth.ts            # Authentication
│   │   └── export-utils.ts    # PDF/Excel export
│   │
│   └── hooks/                  # Custom React hooks
│
├── 🐍 BACKEND (FastAPI/Python)
│   └── backend/
│       ├── src/                # Core source code
│       │   ├── api/           # FastAPI endpoints
│       │   ├── parsers/       # FCS & NTA file parsers
│       │   ├── physics/       # Mie scattering, calibration
│       │   ├── visualization/ # Plot generation
│       │   └── database/      # SQLAlchemy models
│       │
│       ├── scripts/            # Standalone analysis scripts
│       ├── data/               # Uploads & processed data
│       ├── figures/            # Generated plots
│       └── docs/               # Technical documentation
│
└── 📚 DOCUMENTATION
    ├── README.md               # This file
    └── backend/docs/           # Detailed technical docs
```

---

## 👨‍💻 For New Developers

### Start Here

1. **Read this README** completely
2. **Read** [`backend/docs/DEVELOPER_GUIDE.md`](backend/docs/DEVELOPER_GUIDE.md) - Developer onboarding
3. **Understand the science** - EVs, FCS, NTA basics (see Literature folder)

### Key Concepts to Understand

| Concept | What It Is | Where in Code |
|---------|------------|---------------|
| **FCS Files** | Flow cytometry data (914K+ events per file) | `backend/src/parsers/fcs_parser.py` |
| **NTA Files** | Nanoparticle tracking data (size distributions) | `backend/src/parsers/nta_parser.py` |
| **Mie Theory** | Physics for calculating particle size from light scatter | `backend/src/physics/mie_scatter.py` |
| **SSC/FSC** | Side/Forward Scatter - raw signals from flow cytometer | Used throughout |
| **D50** | Median particle diameter (50th percentile) | Key output metric |

### Development Workflow

```
1. Pick a task from TASK_TRACKER.md
2. Create feature branch: git checkout -b feature/your-feature
3. Make changes
4. Test locally (backend + frontend)
5. Commit with clear message
6. Push and create PR
```

---

## ✨ Key Features

### Flow Cytometry (FCS) Analysis
- ✅ Upload and parse FCS 2.0/3.0/3.1 files
- ✅ Automatic channel detection (FSC, SSC, fluorescence)
- ✅ Mie theory particle sizing (30-500nm range)
- ✅ Multi-solution disambiguation using wavelength ratios
- ✅ Scatter plots, histograms, density plots
- ✅ Export to Excel/PDF

### Nanoparticle Tracking Analysis (NTA)
- ✅ Parse ZetaView text files
- ✅ Size distribution histograms
- ✅ D10/D50/D90 percentile calculations
- ✅ Concentration measurements
- ✅ 11-position uniformity analysis

### Cross-Comparison
- ✅ Compare FCS vs NTA results
- ✅ Statistical correlation analysis
- ✅ Side-by-side visualization

### Enterprise Features
- ✅ User authentication (JWT)
- ✅ User-specific sample ownership
- ✅ Previous analysis browser
- ✅ PDF/Excel report generation

---

## 📚 Documentation Index

### For Developers

| Document | Description | Location |
|----------|-------------|----------|
| **Developer Guide** | Onboarding for new developers | [`backend/docs/DEVELOPER_GUIDE.md`](backend/docs/DEVELOPER_GUIDE.md) |
| **Backend Architecture** | Python code structure | [`backend/docs/BACKEND_ARCHITECTURE.md`](backend/docs/BACKEND_ARCHITECTURE.md) |
| **Frontend Architecture** | React/Next.js structure | [`docs/FRONTEND_ARCHITECTURE.md`](docs/FRONTEND_ARCHITECTURE.md) |
| **API Reference** | All endpoints with examples | [`backend/docs/API_REFERENCE.md`](backend/docs/API_REFERENCE.md) |

### For Scientists

| Document | Description | Location |
|----------|-------------|----------|
| **Mie Theory Guide** | Physics of particle sizing | [`backend/docs/user_guides/MIE_QUICK_REFERENCE.md`](backend/docs/user_guides/MIE_QUICK_REFERENCE.md) |
| **FCS Calibration** | Calibration analysis | [`backend/docs/technical/FCS_CALIBRATION_ANALYSIS_REPORT.md`](backend/docs/technical/FCS_CALIBRATION_ANALYSIS_REPORT.md) |
| **Scientific Rationale** | Why we plot what we plot | [`backend/docs/user_guides/SCIENTIFIC_RATIONALE_FCS_PLOTS.md`](backend/docs/user_guides/SCIENTIFIC_RATIONALE_FCS_PLOTS.md) |

### Reference Literature

Located in `backend/Literature/`:
- `Mie functions_scattering_Abs-V1.pdf` - Mie theory equations
- `Mie functions_scattering_Abs-V2.pdf` - Extended Mie theory
- `FCMPASS_Software-Aids-EVs-Light-Scatter-Stand.pdf` - FCM-PASS standardization

---

## 🔧 Configuration

### Environment Variables

**Frontend** (`.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_SECRET=your-secret-key
NEXTAUTH_URL=http://localhost:3000
```

**Backend** (`backend/.env`):
```env
CRMIT_DB_URL=postgresql+asyncpg://user:pass@localhost:5432/crmit_db
CRMIT_ENVIRONMENT=development
```

---

## 🧪 Testing

```powershell
# Backend tests
cd backend
pytest tests/

# Frontend tests (if configured)
npm test
```

---

## 📞 Support

- **Technical Lead:** Sumit Malhotra
- **Project:** BioVaram via CRMIT
- **Repository:** https://github.com/sumitmalhotra-blip/Biovaram_Ev_Analysis_ReactUI

---

*Last Updated: January 2026*

