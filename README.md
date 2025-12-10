# BioVaram EV Analysis Platform

A comprehensive platform for analyzing Extracellular Vesicles (EVs) / Exosomes using Flow Cytometry (FCS) and Nanoparticle Tracking Analysis (NTA) data.

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
└── start.ps1              # Full platform startup
```

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ (for frontend)
- **Python** 3.10+ (for backend)
- **npm** or **pnpm** (package manager)

### Installation

1. **Clone or download this project**

2. **Install Frontend Dependencies**
   ```powershell
   npm install
   ```

3. **Setup Backend**
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\pip install fastapi uvicorn python-multipart pydantic pydantic-settings loguru pandas numpy scipy pyarrow flowio aiosqlite sqlalchemy alembic
   cd ..
   ```

4. **Start Both Services**
   ```powershell
   # Option 1: Use the startup script
   .\start.ps1

   # Option 2: Start manually in separate terminals
   # Terminal 1 - Backend:
   cd backend
   .\venv\Scripts\python.exe run_api.py

   # Terminal 2 - Frontend:
   npm run dev
   ```

5. **Access the Application**
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8000
   - **API Docs**: http://localhost:8000/docs

## 📊 Features

### Flow Cytometry Analysis (FCS)
- Upload .fcs files from flow cytometers
- Automatic channel detection (FSC, SSC, fluorescence)
- Particle size estimation using Mie scattering theory
- Statistical analysis (D10, D50, D90, mean, std)

### Nanoparticle Tracking Analysis (NTA)
- Upload NTA data files (.txt, .csv)
- Size distribution analysis
- Concentration profiling
- Quality metrics

### Cross-Compare
- Overlay FCS and NTA size distributions
- Statistical comparison (KS test, Mann-Whitney U)
- Discrepancy analysis

### Dashboard
- Quick file upload
- Recent activity feed
- Sample overview
- Pinnable charts

## 🔧 Configuration

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (backend/.env)
```env
CRMIT_ENVIRONMENT=development
CRMIT_DATABASE_URL=sqlite+aiosqlite:///./data/crmit.db
CRMIT_CORS_ORIGINS=http://localhost:3000
```

## 📁 Supported File Formats

| Type | Extensions | Description |
|------|------------|-------------|
| FCS | .fcs | Flow Cytometry Standard files (2.0, 3.0, 3.1) |
| NTA | .txt, .csv | ZetaView, NanoSight export files |

## 🛠️ API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| POST | /api/v1/upload/fcs | Upload FCS file |
| POST | /api/v1/upload/nta | Upload NTA file |
| GET | /api/v1/samples | List all samples |
| GET | /api/v1/samples/{id}/fcs | Get FCS analysis results |
| GET | /api/v1/samples/{id}/nta | Get NTA analysis results |

## 📚 Tech Stack

**Frontend:**
- Next.js 16
- React 19
- Tailwind CSS 4
- shadcn/ui components
- Recharts (visualization)
- Zustand (state management)

**Backend:**
- FastAPI
- SQLAlchemy (async)
- Pydantic
- NumPy, SciPy, Pandas
- FlowIO (FCS parsing)

## 📝 License

MIT License - see LICENSE file for details.
