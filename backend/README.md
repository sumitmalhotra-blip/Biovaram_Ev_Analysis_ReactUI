# 🧬 BioVaram EV Analysis Platform

**Enterprise-Grade Extracellular Vesicle (EV/Exosome) Analysis System**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-Proprietary-orange.svg)]()

---

## 📖 Overview

A comprehensive data analysis platform for characterizing Extracellular Vesicles (EVs/Exosomes) from iPSC-derived sources. The system integrates multiple analytical instruments:

- **nanoFACS** - Nano Flow Cytometry (FCS files)
- **NTA** - Nanoparticle Tracking Analysis (ZetaView text files)
- **Mie Scattering Theory** - Physics-based particle sizing (30-200nm)

**Client:** BioVaram via CRMIT  
**Application:** iPSC-derived exosome characterization for therapeutics

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 16+ (optional, for database features)
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/sumitmalhotra-blip/Biovaram_Ev_Analysis.git
cd Biovaram_Ev_Analysis

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.\.venv\Scripts\activate.bat
# Linux/macOS:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. (Optional) Set up environment variables
copy .env.example .env
# Edit .env with your database credentials
```

### Running the Application

```bash
# Start the Backend API (Terminal 1)
.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload --port 8000

# Start the Streamlit UI (Terminal 2)
.venv\Scripts\python.exe -m streamlit run apps/biovaram_streamlit/app.py --server.port 8501
```

**Access:**
- 🌐 **Web UI:** http://localhost:8501
- 📚 **API Docs:** http://localhost:8000/docs
- 🔄 **API ReDoc:** http://localhost:8000/redoc

---

## 📁 Project Structure

```
Biovaram_Ev_Analysis/
│
├── 📄 README.md                     # This file
├── 📄 requirements.txt              # Python dependencies
├── 📄 .env.example                  # Environment template
├── 📄 alembic.ini                   # Database migrations config
│
├── 🖥️ apps/                         # Frontend Applications
│   └── biovaram_streamlit/          # Streamlit Web UI (2000+ lines)
│       └── app.py                   # Main Streamlit application
│
├── 🔧 src/                          # Backend Source Code
│   ├── api/                         # FastAPI REST API
│   │   ├── main.py                  # API entry point
│   │   ├── config.py                # Settings & configuration
│   │   └── routers/                 # API endpoints
│   │       ├── upload.py            # File upload endpoints
│   │       ├── samples.py           # Sample query endpoints
│   │       └── jobs.py              # Processing job endpoints
│   │
│   ├── database/                    # Database Layer
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   ├── crud.py                  # CRUD operations
│   │   └── connection.py            # Async connection management
│   │
│   ├── parsers/                     # Data Parsers
│   │   ├── fcs_parser.py            # FCS file parser (439 lines)
│   │   └── nta_parser.py            # NTA text file parser
│   │
│   ├── physics/                     # Scientific Calculations
│   │   └── mie_scatter.py           # Mie scattering theory (782 lines)
│   │
│   ├── preprocessing/               # Data Processing
│   │   ├── normalization.py         # Data normalization
│   │   ├── size_binning.py          # Size distribution binning
│   │   └── metadata_standardizer.py # Metadata extraction
│   │
│   ├── visualization/               # Plotting & Charts
│   │   ├── fcs_plots.py             # FCS visualization (950+ lines)
│   │   └── auto_axis_selector.py    # Smart axis selection
│   │
│   └── fusion/                      # Multi-Modal Integration
│       ├── sample_matcher.py        # Cross-instrument sample linking
│       └── feature_extractor.py     # Combined feature extraction
│
├── 📜 scripts/                      # Utility Scripts (35+ scripts)
│   ├── quick_fcs_plots.py           # Generate FCS scatter plots
│   ├── batch_process_fcs.py         # Batch FCS processing
│   ├── batch_process_nta.py         # Batch NTA processing
│   ├── integrate_data.py            # FCS + NTA integration
│   ├── s3_utils.py                  # AWS S3 utilities
│   └── ...                          # 30+ more utility scripts
│
├── 🧪 tests/                        # Test Suite
│   ├── test_e2e_system.py           # End-to-end tests
│   ├── test_mie_scatter.py          # Physics tests
│   ├── test_integration.py          # Integration tests
│   └── test_parser.py               # Parser tests
│
├── ⚙️ config/                       # Configuration Files
│   ├── parser_rules.json            # FCS/NTA parsing rules
│   ├── qc_thresholds.json           # Quality control thresholds
│   └── s3_config.json               # AWS S3 configuration
│
├── 🗄️ alembic/                      # Database Migrations
│   └── versions/                    # Migration scripts
│
├── 📊 data/                         # Data Directory
│   ├── raw/                         # Raw instrument files
│   │   ├── fcs/                     # FCS files
│   │   └── nta/                     # NTA files
│   └── processed/                   # Processed Parquet files
│
├── 🔬 nanoFACS/                     # Raw FCS Data (70 files)
│   ├── 10000 exo and cd81/          # CD81 antibody titration
│   ├── CD9 and exosome lots/        # CD9 batch testing
│   └── EXP 6-10-2025/               # Serial dilution experiments
│
├── 📈 NTA/                          # Raw NTA Data (86 files)
│   ├── EV_IPSC_P1_19_2_25_NTA/      # Passage 1
│   ├── EV_IPSC_P2_27_2_25_NTA/      # Passage 2
│   └── EV_IPSC_P2.1_28_2_25_NTA/    # Passage 2.1
│
├── 📚 docs/                         # Documentation
│   ├── user_guides/                 # How-to guides
│   ├── technical/                   # Architecture docs
│   ├── planning/                    # Roadmaps & task tracking
│   └── meeting_notes/               # Client meeting notes
│
├── 📊 figures/                      # Generated Visualizations
│   ├── fcs_presentation/            # CD81 plots (20 graphs)
│   ├── fcs_presentation_cd9/        # CD9 plots (23 graphs)
│   └── fcs_presentation_exp/        # EXP plots (23 graphs)
│
└── 📚 Literature/                   # Scientific References
    └── *.pdf                        # Mie scattering papers
```

---

## 📦 Installation Guide

### Step 1: Clone Repository

```bash
git clone https://github.com/sumitmalhotra-blip/Biovaram_Ev_Analysis.git
cd Biovaram_Ev_Analysis
```

### Step 2: Create Virtual Environment

```bash
# Create venv
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Windows CMD)
.\.venv\Scripts\activate.bat

# Activate (Linux/macOS)
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt
```

### Step 4: Quick Install (Alternative)

If `requirements.txt` has issues, install core packages directly:

```bash
pip install pandas numpy scipy fcsparser pyarrow
pip install fastapi uvicorn python-multipart pydantic pydantic-settings
pip install sqlalchemy asyncpg alembic psycopg2-binary
pip install streamlit plotly matplotlib seaborn
pip install miepython boto3 tqdm python-dotenv loguru requests
pip install pytest pytest-cov pytest-asyncio
```

---

## 📋 Requirements

### requirements.txt

```
# ============================================
# CORE DATA PROCESSING
# ============================================
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0

# ============================================
# FCS FILE PARSING
# ============================================
fcsparser>=0.2.0

# ============================================
# PARQUET & DATA STORAGE
# ============================================
pyarrow>=14.0.0

# ============================================
# WEB FRAMEWORK (Backend)
# ============================================
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6
pydantic>=2.0.0
pydantic-settings>=2.0.0

# ============================================
# DATABASE
# ============================================
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0
psycopg2-binary>=2.9.9

# ============================================
# WEB UI (Frontend)
# ============================================
streamlit>=1.30.0
plotly>=5.18.0

# ============================================
# VISUALIZATION
# ============================================
matplotlib>=3.7.0
seaborn>=0.12.0

# ============================================
# PHYSICS / SCIENTIFIC
# ============================================
miepython>=2.3.0

# ============================================
# AWS S3 (Optional)
# ============================================
boto3>=1.26.0
botocore>=1.29.0

# ============================================
# UTILITIES
# ============================================
tqdm>=4.65.0
python-dotenv>=1.0.0
loguru>=0.7.2
requests>=2.31.0
colorama>=0.4.6

# ============================================
# TESTING
# ============================================
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-asyncio>=0.21.0

# ============================================
# CODE QUALITY
# ============================================
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
```

---

## ⚙️ Environment Configuration

### Create `.env` file

```bash
# Copy template
copy .env.example .env
```

### .env Contents

```env
# ============================================
# APPLICATION SETTINGS
# ============================================
ENVIRONMENT=development
DEBUG=true
APP_NAME=BioVaram EV Analysis
APP_VERSION=1.0.0

# ============================================
# DATABASE (PostgreSQL)
# ============================================
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/biovaram_ev_db
DB_ECHO=false

# ============================================
# API SETTINGS
# ============================================
API_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:8501,http://localhost:3000

# ============================================
# FILE STORAGE
# ============================================
UPLOAD_DIR=./uploads
PARQUET_DIR=./data/processed
MAX_UPLOAD_SIZE_MB=100

# ============================================
# AWS S3 (Optional)
# ============================================
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET=biovaram-ev-data
```

### PostgreSQL Setup (Optional)

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE biovaram_ev_db;

# Exit
\q

# Run migrations
alembic upgrade head
```

---

## 🖥️ Usage Guide

### 1. Start the Application

**Terminal 1 - Backend API:**
```bash
cd "path/to/Biovaram_Ev_Analysis"
.\.venv\Scripts\Activate.ps1
.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload --port 8000
```

**Terminal 2 - Frontend UI:**
```bash
cd "path/to/Biovaram_Ev_Analysis"
.\.venv\Scripts\Activate.ps1
.venv\Scripts\python.exe -m streamlit run apps/biovaram_streamlit/app.py --server.port 8501
```

### 2. Access the Application

| Service | URL |
|---------|-----|
| Web UI | http://localhost:8501 |
| API Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |

### 3. Command Line Scripts

```bash
# Generate FCS scatter plots
python scripts/quick_fcs_plots.py

# Batch process all FCS folders
python scripts/process_all_fcs_folders.py

# Parse NTA files
python scripts/batch_process_nta.py

# Integrate FCS + NTA data
python scripts/integrate_data.py

# Validate integration
python scripts/validate_integration.py
```

### 4. Python API Usage

```python
from src.parsers.fcs_parser import FCSParser
from src.physics.mie_scatter import MieScatterCalculator

# Parse FCS file
parser = FCSParser("path/to/file.fcs")
data = parser.parse()
print(f"Events: {len(data)}")
print(f"Channels: {list(data.columns)}")

# Calculate particle size from FSC
calculator = MieScatterCalculator()
diameter_nm = calculator.fsc_to_diameter(fsc_value=15000)
print(f"Particle size: {diameter_nm:.1f} nm")
```

---

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/status` | GET | System status with DB check |
| `/api/v1/upload/fcs` | POST | Upload FCS file |
| `/api/v1/upload/nta` | POST | Upload NTA file |
| `/api/v1/upload/batch` | POST | Batch upload files |
| `/api/v1/samples` | GET | List all samples |
| `/api/v1/samples/{id}` | GET | Get sample details |
| `/api/v1/samples/{id}/fcs` | GET | Get FCS results |
| `/api/v1/samples/{id}/nta` | GET | Get NTA results |
| `/api/v1/samples/{id}` | DELETE | Delete sample |
| `/api/v1/jobs` | GET | List processing jobs |
| `/api/v1/jobs/{id}` | GET | Get job status |
| `/api/v1/jobs/{id}` | DELETE | Cancel job |
| `/api/v1/jobs/{id}/retry` | POST | Retry failed job |

---

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_mie_scatter.py -v

# Run end-to-end tests
pytest tests/test_e2e_system.py -v
```

---

## 🔬 Scientific Features

### Mie Scattering Theory
- Accurate particle sizing from 30-200nm
- Uses refractive index of polystyrene beads for calibration
- Validated against FCMPASS methodology
- Implementation in `src/physics/mie_scatter.py`

### Data Analysis Capabilities
1. **CD81/CD9 Antibody Optimization** - Titration analysis
2. **Batch Consistency Testing** - Compare production lots
3. **Serial Dilution Validation** - Instrument linearity
4. **Purification Comparison** - SEC vs Centrifugation
5. **Size Calibration** - Reference bead calibration
6. **User-Defined Size Ranges** - Custom binning (e.g., 50-100nm, 100-150nm)

---

## 📈 Project Status

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Data Processing | ✅ Complete | 100% |
| Phase 2: Visualization | ✅ Complete | 100% |
| Phase 3: ML Analytics | ⏳ Pending | 0% |
| Phase 4: Deployment | 🔄 In Progress | 60% |

**Overall Progress:** ~65% Complete

### Recent Updates (Dec 2025)
- ✅ Database CRUD operations connected to API
- ✅ FCS/NTA uploads now save to PostgreSQL
- ✅ User-defined size ranges implemented
- ✅ Comprehensive task tracking document

---

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and test
3. Commit: `git commit -m "Add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open Pull Request

---

## 📚 Documentation

| Document | Location | Description |
|----------|----------|-------------|
| Quick Start | `docs/user_guides/QUICK_START_GUIDE.md` | Get started in 5 minutes |
| Technical Docs | `docs/technical/MASTER_BACKEND_DOCUMENTATION.md` | API & architecture |
| Task Tracker | `docs/planning/TASK_TRACKER.md` | Current task status |
| Pending Tasks | `docs/planning/PENDING_TASKS_ANALYSIS.md` | Comprehensive task audit |

---

## 📞 Support

- **Repository:** https://github.com/sumitmalhotra-blip/Biovaram_Ev_Analysis
- **Documentation:** See `docs/` folder
- **Issues:** Open a GitHub issue

---

## 📄 License

Proprietary - BioVaram/CRMIT

---

**Last Updated:** December 1, 2025  
**Version:** 1.0.0
