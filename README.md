# BioVaram EV Analysis Platform

A comprehensive platform for analyzing Extracellular Vesicles (EVs) / Exosomes using Flow Cytometry (FCS) and Nanoparticle Tracking Analysis (NTA) data.

[![Node.js 18+](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-teal.svg)](https://fastapi.tiangolo.com/)

---

## 🏗️ Architecture

```
ev-analysis-platform/
├── app/                    # Next.js frontend pages
├── components/             # React UI components
├── lib/                    # Frontend utilities & API client
├── hooks/                  # Custom React hooks
├── backend/                # FastAPI Python backend
│   ├── src/
│   │   ├── api/           # REST API endpoints
│   │   ├── parsers/       # FCS & NTA file parsers
│   │   ├── physics/       # Mie scattering calculations
│   │   └── database/      # Database models & connection
│   ├── data/              # Uploads & processed files
│   └── run_api.py         # Backend startup script
├── public/                 # Static assets
└── start.ps1              # Full platform startup (Windows)
```

---

## 🚀 Quick Start (One-Time Setup)

### Prerequisites

| Requirement | Version | Download |
|-------------|---------|----------|
| **Node.js** | 18+ | https://nodejs.org/ |
| **Python** | 3.10+ | https://www.python.org/downloads/ |
| **Git** | Latest | https://git-scm.com/ |

### Step 1: Clone the Repository

```bash
git clone https://github.com/sumitmalhotra-blip/Biovaram_Ev_Analysis_ReactUI.git
cd Biovaram_Ev_Analysis_ReactUI
```

### Step 2: Install Frontend Dependencies

```powershell
# Windows PowerShell
npm install

# OR if you prefer pnpm:
# pnpm install
```

### Step 3: Setup Python Backend

```powershell
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install all Python dependencies
pip install -r requirements.txt

# Return to project root
cd ..
```

**Linux/macOS Alternative:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
```

### Step 4: Create Environment Files (Optional)

```powershell
# Frontend environment (create .env.local in root)
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Backend environment (create .env in backend folder)
echo "CRMIT_ENVIRONMENT=development" > backend/.env
```

---

## 🏃 Running the Application

### Option 1: Using Startup Script (Windows)

```powershell
.\start.ps1
```

### Option 2: Manual Start (Two Terminals)

**Terminal 1 - Start Backend:**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python run_api.py
```

**Terminal 2 - Start Frontend:**
```powershell
npm run dev
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Main application UI |
| **Backend API** | http://localhost:8000 | REST API |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **ReDoc** | http://localhost:8000/redoc | Alternative API docs |

---

## 📊 Features

### Flow Cytometry Analysis (FCS)
- Upload .fcs files from flow cytometers (nanoFACS, etc.)
- Automatic channel detection (FSC, SSC, fluorescence markers)
- Particle size estimation using **Mie scattering theory**
- Statistical analysis (D10, D50, D90, mean, median, std)
- Size distribution visualization
- Configurable experimental parameters

### Nanoparticle Tracking Analysis (NTA)
- Upload NTA data files (.txt, .csv) from ZetaView
- Size distribution analysis with temperature correction
- Concentration profiling
- Multi-position analysis
- Stokes-Einstein equation calculations

### Cross-Compare
- Overlay FCS and NTA size distributions
- Statistical comparison (KS test, Mann-Whitney U)
- Correlation scatter charts with regression
- Discrepancy analysis

### Dashboard
- Quick file upload with drag-and-drop
- Recent activity feed
- Sample overview with statistics
- Pinnable charts
- AI-powered research assistant

### Additional Features
- Export to CSV, Excel, Parquet, JSON
- Markdown report generation
- Saved images gallery
- Chat history export

---

## 🔧 Configuration

### Frontend Configuration (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend Configuration (backend/.env)
```env
# Environment: development | production
CRMIT_ENVIRONMENT=development

# Database (SQLite default - no setup required)
CRMIT_DATABASE_URL=sqlite+aiosqlite:///./data/crmit.db

# CORS Origins (comma-separated for multiple)
CRMIT_CORS_ORIGINS=http://localhost:3000

# Optional: PostgreSQL (uncomment and configure)
# CRMIT_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/biovaram
```

---

## 📁 Supported File Formats

| Type | Extensions | Description |
|------|------------|-------------|
| FCS | `.fcs` | Flow Cytometry Standard (2.0, 3.0, 3.1) |
| NTA | `.txt`, `.csv` | ZetaView, NanoSight export files |

---

## 🛠️ API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/upload/fcs` | Upload FCS file |
| `POST` | `/api/v1/upload/nta` | Upload NTA file |
| `GET` | `/api/v1/samples` | List all samples |
| `GET` | `/api/v1/samples/{id}` | Get sample details |
| `GET` | `/api/v1/samples/{id}/scatter-data` | Get FCS scatter data |
| `GET` | `/api/v1/samples/{id}/size-bins` | Get size distribution |
| `POST` | `/api/v1/samples/{id}/reanalyze` | Re-analyze with new parameters |
| `DELETE` | `/api/v1/samples/{id}` | Delete sample |

---

## 📚 Tech Stack

**Frontend:**
- Next.js 16 (React 19)
- Tailwind CSS 4
- shadcn/ui components
- Recharts (visualization)
- Zustand (state management)
- TypeScript

**Backend:**
- FastAPI (async Python web framework)
- SQLAlchemy 2.0 (async ORM)
- Pydantic 2.0 (data validation)
- FlowIO (FCS file parsing)
- NumPy, SciPy, Pandas (data processing)
- MiePython (Mie scattering calculations)

---

## 🔄 Updating the Application

```powershell
# Pull latest changes
git pull origin main

# Update frontend dependencies
npm install

# Update backend dependencies
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt --upgrade
cd ..
```

---

## 🐛 Troubleshooting

### Backend won't start
```powershell
# Make sure virtual environment is activated
cd backend
.\venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

### Frontend build errors
```powershell
# Clear node modules and reinstall
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
npm install
```

### Database issues
```powershell
# Delete database and restart (data will be lost)
Remove-Item backend\data\crmit.db -Force
# Restart backend - database will be recreated
```

### Port already in use
```powershell
# Kill process on port 8000 (backend)
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force

# Kill process on port 3000 (frontend)
Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess | Stop-Process -Force
```

---

## 📝 License

Proprietary - BioVaram / CRMIT

---

## 👥 Contributors

- Development Team @ CRMIT
- BioVaram Research Team

