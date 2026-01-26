# BioVaram EV Analysis - Backend

**Python/FastAPI Backend for EV Analysis Platform**

*Last Updated: January 2026*

---

## 🚀 Quick Start

```powershell
# Setup (one-time)
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run API server
python run_api.py

# Access
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

---

## 📁 Structure

```
backend/
├── src/                 # Core source code
│   ├── api/            # FastAPI endpoints
│   ├── parsers/        # FCS & NTA file parsers
│   ├── physics/        # Mie scattering, calibration
│   ├── visualization/  # Plot generation
│   └── database/       # SQLAlchemy models
│
├── scripts/            # Standalone analysis scripts
├── data/               # Uploads & processed data
├── figures/            # Generated plots
├── docs/               # Documentation
├── nanoFACS/           # Sample FCS data
├── NTA/                # Sample NTA data
└── Literature/         # Reference papers
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Onboarding for new developers |
| [BACKEND_ARCHITECTURE.md](docs/BACKEND_ARCHITECTURE.md) | Code structure & modules |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | API endpoints |

---

## 🔧 Key Modules

### Parsers (`src/parsers/`)
- `fcs_parser.py` - Parse FCS 2.0/3.0/3.1 files
- `nta_parser.py` - Parse ZetaView NTA text files

### Physics (`src/physics/`)
- `mie_scatter.py` - Mie theory calculations
- `size_distribution.py` - Per-event sizing
- `fcs_calibration.py` - SSC-to-size calibration

### API (`src/api/`)
- `main.py` - FastAPI application
- `routers/upload.py` - File upload endpoints
- `routers/samples.py` - Sample CRUD

---

## 🧪 Testing

```powershell
pytest tests/ -v
```

---

## 📊 Sample Data

- `nanoFACS/Exp_20251217_PC3/` - PC3 exosome samples
- `NTA/` - ZetaView measurements

---

*See main README in project root for full documentation.*
