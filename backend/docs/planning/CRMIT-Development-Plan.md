# CRMIT Development Plan: Backend Implementation
## Timeline: November 14, 2025 → January 15, 2026 (9 Weeks)
## Extended: Phase 7 UI Enhancements (January 2025)

**Developer**: Senior Python Full-Stack Developer  
**Project**: CRMIT - Multi-Modal Laboratory Data Integration Platform  
**Client**: Bio Varam (Biotechnology Research)  
**Primary Deadline**: Mid-January 2026 (FCS + NTA parsing + Basic UI)  
**Extended Deadline**: Late January 2026 (UI Enhancements + Gap Closure)

---

## 🔍 GAP ANALYSIS UPDATE - January 2025

**Status**: Gap analysis completed against Technical Requirements Document  
**Reference**: `docs/planning/GAP_ANALYSIS.md`  
**New Phase Added**: Phase 7 - UI Enhancements & Gap Closure

### Summary of Identified Gaps

| Gap | Priority | Effort | Status |
|-----|----------|--------|--------|
| FCS Best Practices Guide | HIGH | LOW | ❌ TODO |
| Interactive Plotly Graphs | HIGH | MEDIUM | ❌ TODO |
| Cross-Instrument Comparison | HIGH | MEDIUM | ❌ TODO |
| Anomaly Detection UI | MEDIUM | LOW | ❌ TODO |
| NTA Parameter Corrections | MEDIUM | MEDIUM | ❌ TODO |
| Graph Annotation Tools | MEDIUM | HIGH | ⏳ DEFERRED |
| Persistent Chat History | LOW | LOW | ❌ TODO |

**Excludes**: TEM, Western Blot, AI Model (known pending)

---

## 🎉 MEETING UPDATE - November 27, 2025

### **Weekly Customer Connect - Key Outcomes**

**Demo Success:**
- ✅ Backend + UI integration demonstrated successfully
- ✅ Analysis running smoothly and fast
- ✅ NTA tab added to UI for file uploads
- ✅ Client satisfied with current progress

**NEW REQUIREMENT: User-Defined Size Ranges**

Per Jaganmohan Reddy's guidance:
- **DO NOT hardcode** size categories (30-100nm, 100-150nm, etc.)
- **Let users choose** their own range dynamically via UI controls
- **Reason**: Different scientific applications need different segmentation
- **Example ranges**:
  - Small vesicles: 30-100 nm
  - Alternative: 30-150 nm
  - Custom: User-defined start/end

**Implementation Required:**
```python
# Add to UI: Range selector component
# User selects: min_size, max_size
# Display: "Particles in {min}-{max}nm: {count}"
```

**Waiting On:**
- ⏳ AI/Data Cloud credentials (after MD meeting with Vinod)
- ⏳ Parameter graphs list from Jaganmohan (which combinations to analyze)
- ⏳ New protocol data from BioVaram (~2 weeks)

**Meeting Schedule Changed:**
- **NEW**: Wednesdays 4:00-5:00 PM (recurring)

---

## 🚨 CRITICAL UPDATE - November 18, 2025

### **Mie Scattering Theory Implementation Required**

**Discovery**: Current particle size calculations use simplified sqrt approximation with NO physical basis. This was identified after analyzing client-provided Literature PDFs (3 files on Mie scattering theory and FCMPASS software).

**Impact**:
- ❌ Current particle sizes are arbitrary (not scientifically valid)
- ❌ Cannot explain biological observations (e.g., "CD9 at 80nm scatters blue light")
- ❌ Results are not publishable without proper Mie theory
- ⚠️ All 66 converted Parquet files need reprocessing after Mie implementation

**Status**:
- ✅ Literature analysis complete (LITERATURE_ANALYSIS_MIE_FCMPASS.md)
- ✅ Stub implementation created (src/physics/mie_scatter.py - 250+ lines)
- 🎯 **Implementation required THIS WEEK** (Nov 18-22)

**Action Items** (see Phase 0.5 below):
1. Install miepython library
2. Implement MieScatterCalculator with actual Mie equations
3. Implement FCMPASSCalibrator for reference bead calibration
4. Reprocess all 66 Parquet files with accurate sizes
5. Validate against NTA measurements

---

## 📁 Project Folder Structure Reference

```
C:\CRM IT Project\EV (Exosome) Project\
│
├── 📂 src/                          # SOURCE CODE (Production)
│   ├── parsers/                     # Data parsers
│   │   ├── __init__.py
│   │   ├── base_parser.py          # Abstract base class for parsers
│   │   ├── fcs_parser.py           # ✅ FCS parser (Task 1.1 COMPLETE)
│   │   └── nta_parser.py           # ✅ NTA parser (Task 1.2 COMPLETE)
│   │
│   ├── preprocessors/               # Data preprocessing
│   │   ├── __init__.py
│   │   ├── fcs_preprocessor.py     # FCS quality control & filtering
│   │   └── nta_preprocessor.py     # NTA validation & cleanup
│   │
│   ├── integrators/                 # Data integration
│   │   ├── __init__.py
│   │   └── multi_modal_fusion.py   # Combine FCS + NTA by sample ID
│   │
│   ├── ml/                          # Machine learning
│   │   ├── __init__.py
│   │   ├── feature_engineering.py  # Extract ML features
│   │   └── anomaly_detection.py    # Basic anomaly detection
│   │
│   └── config/                      # Configuration
│       ├── __init__.py
│       └── settings.py             # ✅ Settings (paths, constants)
│
├── 📂 scripts/                      # UTILITY SCRIPTS
│   ├── __init__.py
│   ├── batch_process_fcs.py        # ✅ Batch FCS processor (COMPLETE)
│   ├── batch_process_nta.py        # ✅ Batch NTA processor (Task 1.2 COMPLETE)
│   ├── integrate_data.py           # Data integration script
│   ├── parse_fcs.py                # Single FCS file parser
│   ├── parse_nta.py                # Single NTA file parser
│   └── s3_utils.py                 # AWS S3 utilities (future)
│
├── 📂 tests/                        # UNIT TESTS
│   ├── __init__.py
│   ├── test_fcs_parser.py          # ✅ FCS parser tests (21 passing)
│   ├── test_nta_parser.py          # ✅ NTA parser tests (7 tests, 6 passing)
│   └── test_integration.py         # Integration tests
│
├── 📂 data/                         # DATA STORAGE
│   ├── parquet/                    # ✅ Processed data (Parquet format)
│   │   ├── nanofacs/
│   │   │   ├── events/             # ✅ FCS event data (67 files, 727 MB)
│   │   │   └── statistics/         # ✅ FCS summary statistics
│   │   │       └── batch_summary.csv
│   │   │
│   │   ├── nta/                    # ✅ NTA data (Task 1.2 COMPLETE)
│   │   │   ├── measurements/       # ✅ NTA measurement data (112 files)
│   │   │   └── statistics/         # NTA summary statistics
│   │   │
│   │   └── integrated/             # 🔄 Combined FCS + NTA (Task 1.3)
│   │       ├── combined_features.parquet
│   │       └── baseline_comparison.parquet
│   │
│   └── ml_ready/                   # ML-ready datasets
│       └── (future ML datasets)
│
├── 📂 nanoFACS/                     # RAW FCS DATA (Input)
│   ├── 10000 exo and cd81/         # ✅ 20 FCS files processed
│   ├── CD9 and exosome lots/       # ✅ 27 FCS files processed
│   └── EXP 6-10-2025/              # ✅ 20 FCS files processed
│
├── 📂 NTA/                          # RAW NTA DATA (Input)
│   ├── EV_IPSC_P1_19_2_25_NTA/     # 🔄 86 NTA text files
│   ├── EV_IPSC_P2_27_2_25_NTA/
│   └── EV_IPSC_P2.1_28_2_25_NTA/
│
├── 📂 logs/                         # PROCESSING LOGS
│   ├── batch_fcs_processing_*.log  # ✅ FCS batch processing logs
│   ├── processing_log_*.csv        # ✅ Detailed processing records
│   └── error_log_*.csv             # Error tracking
│
├── 📂 docs/                         # DOCUMENTATION
│   ├── FILENAME_PARSING_RULES.md   # Filename parsing patterns
│   └── VSCODE_EXTENSIONS_GUIDE.md  # VS Code setup guide
│
├── 📂 config/                       # CONFIGURATION FILES
│   ├── parser_rules.json           # Parser configuration
│   ├── qc_thresholds.json          # Quality control thresholds
│   └── s3_config.json              # S3 configuration (future)
│
├── 📂 Literature/                   # RESEARCH PAPERS (Reference)
│   └── (scientific papers for ML models)
│
├── 📂 test_data/                    # TEST DATA (Sample files)
│   ├── nanofacs/                   # Sample FCS files for testing
│   └── nta/                        # Sample NTA files for testing
│
├── 📂 .venv/                        # VIRTUAL ENVIRONMENT
│   └── (Python 3.13.7 + dependencies)
│
├── 📂 .vscode/                      # VS CODE SETTINGS
│   └── settings.json               # Editor configuration
│
├── 📂 .git/                         # GIT REPOSITORY
│   └── (version control)
│
├── 📄 CRMIT-Development-Plan.md    # 📋 THIS FILE - Master plan
├── 📄 TASK_TRACKER.md              # ✅ Task tracking & progress
├── 📄 TASK_1.1_COMPLETE.md         # ✅ Task 1.1 completion report
├── 📄 TASK_1.1_TECHNICAL_GUIDE.md  # ✅ Task 1.1 technical guide
├── 📄 TASK_1.2_COMPLETE.md         # ✅ Task 1.2 completion report
├── 📄 TASK_1.2_TECHNICAL_GUIDE.md  # ✅ Task 1.2 technical guide
├── 📄 CRMIT_ARCHITECTURE_ANALYSIS.md # System architecture
├── 📄 DATA_FORMATS_FOR_ML_GUIDE.md # Data format specifications
├── 📄 CRMIT_Quick_Reference.txt    # Quick command reference
├── 📄 QUICK_REFERENCE.md           # Quick reference guide
├── 📄 README.md                    # Project overview
├── 📄 EXECUTIVE_SUMMARY.md         # Executive summary
├── 📄 SETUP_GUIDE.md               # Setup instructions
├── 📄 TEAM_SETUP_GUIDE.md          # Team onboarding guide
│
├── 📄 requirements.txt             # ✅ Python dependencies
├── 📄 setup.ps1                    # PowerShell setup script
├── 📄 .env.example                 # Environment variables template
├── 📄 .env                         # Environment variables (gitignored)
└── 📄 .gitignore                   # Git ignore rules
```

### 📊 Quick Reference: Where to Find What

| What You Need | Location | Status |
|---------------|----------|--------|
| **FCS Parser** | `src/parsers/fcs_parser.py` | ✅ Complete |
| **Batch FCS Processing** | `scripts/batch_process_fcs.py` | ✅ Complete |
| **FCS Unit Tests** | `tests/test_fcs_parser.py` | ✅ 21 passing |
| **Processed FCS Data** | `data/parquet/nanofacs/events/` | ✅ 67 files |
| **FCS Statistics** | `data/parquet/nanofacs/statistics/` | ✅ Available |
| **Raw FCS Files** | `nanoFACS/` (3 subdirectories) | ✅ 67 files |
| **Processing Logs** | `logs/` | ✅ Available |
| **Settings & Config** | `src/config/settings.py` | ✅ Complete |
| **NTA Parser** | `src/parsers/nta_parser.py` | ✅ Complete |
| **NTA Batch Processor** | `scripts/batch_process_nta.py` | ✅ Complete |
| **Processed NTA Data** | `data/parquet/nta/measurements/` | ✅ 112 files |
| **Raw NTA Files** | `NTA/` (3 subdirectories) | ✅ 126 files |
| **Data Integration** | `scripts/integrate_data.py` | 🔄 Task 1.3 |
| **Documentation** | Root directory `.md` files | ✅ Comprehensive |

### 🎯 Key Files by Task

#### Task 1.1 - FCS Parser (✅ COMPLETE)
- `src/parsers/fcs_parser.py` - Core parser (400 lines)
- `scripts/batch_process_fcs.py` - Batch processor (450 lines)
- `tests/test_fcs_parser.py` - Unit tests (350 lines, 21 tests)
- `data/parquet/nanofacs/events/` - Output (67 files, 727 MB)
- `TASK_1.1_COMPLETE.md` - Completion report

#### Task 1.2 - NTA Parser (✅ COMPLETE - Week 7)
- `src/parsers/nta_parser.py` - ✅ Created (700 lines, 3 file types)
- `scripts/batch_process_nta.py` - ✅ Created (200 lines, parallel processing)
- `tests/test_nta_parser.py` - ✅ Created (7 tests, 6 passing)
- `NTA/` - Input (126 text files across 3 batches)
- `data/parquet/nta/measurements/` - ✅ Output (112 Parquet files, 88.9% success rate)
- `TASK_1.2_COMPLETE.md` - ✅ Completion documentation
- `TASK_1.2_TECHNICAL_GUIDE.md` - ✅ Technical guide

#### Task 1.3 - Data Integration (🔄 Week 10-11)
- `scripts/integrate_data.py` - Data fusion script
- `data/parquet/integrated/` - Combined datasets
- `src/integrators/multi_modal_fusion.py` - Integration logic

### 📦 Data Flow

```
RAW DATA → PARSERS → PARQUET → INTEGRATION → ML-READY
   ↓          ↓         ↓           ↓            ↓
nanoFACS/  fcs_parser  events/  integrate  ml_ready/
NTA/       nta_parser  nta/     _data.py   datasets/
```

### 🔧 Development Workflow

1. **Edit Code**: `src/` directory
2. **Run Scripts**: `scripts/` directory
3. **Run Tests**: `python -m pytest tests/`
4. **Check Output**: `data/parquet/`
5. **View Logs**: `logs/`
6. **Update Docs**: Root `.md` files

---

## Executive Summary

This development plan focuses on **backend data processing infrastructure** for CRMIT, with priority on:

1. **FCS file parsing** (Flow Cytometry data)
2. **NTA text file parsing** (ZetaView Nanoparticle Tracking)
3. **Parquet-based unified data storage** (replacing CSV approach)
4. **Data preprocessing and quality control**
5. **Multi-modal data fusion** (sample matching)
6. **Basic anomaly detection**
7. **Minimal UI for file upload and analysis triggers**

**Key Technical Decision**: Using **Apache Parquet** instead of CSV for intermediate data storage provides:
- **87% smaller file sizes** vs CSV
- **34x faster queries**
- **99% less data scanned** for analytics
- Native schema support and column-level compression
- Seamless integration with Pandas, Apache Arrow, and future ML pipelines

---

## Timeline Overview

```
Week 1-2:  Project Setup + FCS Parser (Priority 1)
Week 3-4:  NTA Parser + Parquet Integration (Priority 1)  
Week 5-6:  Data Preprocessing + Quality Control (Priority 2)
Week 7:    Multi-Modal Fusion + Sample Matching (Priority 2)
Week 8:    Basic Anomaly Detection + Dashboard Backend (Priority 3)
Week 9:    Minimal UI + Integration Testing + Documentation (Final)
```

**Buffer**: 3-4 days for unexpected issues, client feedback, and refinement

---

## Development Environment Setup

### Phase 0: Environment Configuration (Days 1-2)

#### 0.1 Repository Setup
```bash
# Clone repository
git clone https://github.com/isumitmalhotra/CRMIT-Project-.git
cd CRMIT-Project

# Create development branch
git checkout -b dev/backend-implementation

# Set up virtual environment
python3.9 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 0.2 Install Core Dependencies

**Create `requirements.txt`**:
```txt
# Core Data Processing
pandas==2.1.4
numpy==1.26.2
pyarrow==14.0.1          # Parquet support
fastparquet==2024.2.0    # Alternative Parquet engine

# FCS File Processing
fcsparser==0.2.8         # Primary FCS parser
readfcs==2.0.1           # Alternative with AnnData support
flowkit==1.0.0           # Advanced FCS operations

# Data Validation & QC
pydantic==2.5.3          # Data validation
jsonschema==4.20.0       # Schema validation

# Database
sqlalchemy==2.0.25       # ORM
psycopg2-binary==2.9.9   # PostgreSQL adapter
alembic==1.13.1          # Database migrations

# Computer Vision (for future TEM analysis)
opencv-python==4.9.0.80
scikit-image==0.22.0
pytesseract==0.3.10      # OCR for scale bar detection

# Machine Learning
scikit-learn==1.4.0
scipy==1.12.0

# API & Backend
fastapi==0.109.0         # Web framework
uvicorn==0.27.0          # ASGI server
python-multipart==0.0.6  # File upload support

# Utilities
python-dotenv==1.0.0     # Environment variables
loguru==0.7.2            # Logging
pytest==7.4.4            # Testing
pytest-cov==4.1.0        # Test coverage

# Data Visualization (minimal for backend)
matplotlib==3.8.2
plotly==5.18.0
```

**Install dependencies**:
```bash
pip install -r requirements.txt
```

#### 0.3 Project Structure

```
CRMIT-Project/
├── data/                           # Raw data storage (gitignored)
│   ├── fcs_files/
│   ├── nta_data/
│   ├── tem_images/
│   └── parquet/                    # Processed Parquet files
├── src/
│   ├── __init__.py
│   ├── config/                     # Configuration
│   │   ├── __init__.py
│   │   ├── settings.py             # App settings
│   │   └── logging_config.py       # Logging setup
│   ├── parsers/                    # Data ingestion layer
│   │   ├── __init__.py
│   │   ├── fcs_parser.py           # FCS file parser
│   │   ├── nta_parser.py           # NTA text parser
│   │   ├── base_parser.py          # Abstract base class
│   │   └── parquet_writer.py       # Parquet conversion
│   ├── preprocessing/              # Data preprocessing
│   │   ├── __init__.py
│   │   ├── quality_control.py      # QC checks
│   │   ├── normalization.py        # Data normalization
│   │   └── size_binning.py         # Particle size binning
│   ├── fusion/                     # Multi-modal data fusion
│   │   ├── __init__.py
│   │   ├── sample_matcher.py       # Sample ID matching
│   │   ├── feature_extractor.py    # Feature extraction
│   │   └── data_aligner.py         # Temporal alignment
│   ├── anomaly_detection/          # Anomaly detection
│   │   ├── __init__.py
│   │   ├── statistical_tests.py    # Statistical methods
│   │   ├── outlier_detector.py     # Outlier detection
│   │   └── threshold_manager.py    # Threshold configuration
│   ├── database/                   # Database layer
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── crud.py                 # CRUD operations
│   │   └── connection.py           # DB connection
│   ├── api/                        # FastAPI endpoints
│   │   ├── __init__.py
│   │   ├── main.py                 # Main app
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py           # File upload
│   │   │   ├── analysis.py         # Analysis triggers
│   │   │   └── results.py          # Results retrieval
│   │   └── schemas.py              # Pydantic schemas
│   └── utils/                      # Utilities
│       ├── __init__.py
│       ├── file_utils.py           # File operations
│       ├── validation.py           # Data validation
│       └── helpers.py              # Helper functions
├── tests/                          # Unit tests
│   ├── __init__.py
│   ├── test_parsers/
│   ├── test_preprocessing/
│   ├── test_fusion/
│   └── fixtures/                   # Test data
├── notebooks/                      # Jupyter notebooks for exploration
├── docs/                           # Documentation
├── scripts/                        # Utility scripts
│   ├── setup_db.py                 # Database setup
│   └── seed_data.py                # Sample data generation
├── .env.example                    # Environment variables template
├── .gitignore
├── requirements.txt
├── pytest.ini                      # Pytest configuration
└── README.md
```

#### 0.4 Environment Configuration

**Create `.env` file**:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/crmit_db

# File Storage
DATA_DIR=./data
PARQUET_DIR=./data/parquet
UPLOAD_DIR=./data/uploads

# Application
DEBUG=True
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# Processing
MAX_FILE_SIZE_MB=500
BATCH_SIZE=10000
WORKER_THREADS=4

# Thresholds
TEMPERATURE_TOLERANCE=2.0  # ±2°C
SIZE_DISCREPANCY_THRESHOLD=15.0  # 15% difference
OUTLIER_STD_THRESHOLD=3.0  # 3 standard deviations
```

---

## Phase 0.5: 🚨 Mie Scattering Theory Implementation (Week 1 - CRITICAL)

**Priority**: 🚨 **CRITICAL** - BLOCKING SCIENTIFIC VALIDITY  
**Duration**: 5 working days (Nov 18-22, 2025)  
**Goal**: Replace simplified particle size calculations with physics-based Mie scattering theory

### 0.5.1 Background & Justification (Context)

**Problem Identified**: Current `calculate_particle_size()` function uses arbitrary sqrt approximation:
```python
# Current (WRONG):
particle_size_nm = 30 + (sqrt(normalized_FSC) * 120)  # NO physical basis
```

**Why This Matters**:
- ❌ Particle sizes have no physical meaning
- ❌ Cannot validate against known physics
- ❌ Cannot explain biological observations (e.g., "CD9 at 80nm scatters blue light")
- ❌ Results not scientifically publishable
- ❌ All 66 Parquet files contain inaccurate data

**What Mie Theory Provides**:
- ✅ Physics-based size calculation from light scattering
- ✅ Wavelength-dependent scatter patterns (405nm, 488nm, 561nm, 633nm)
- ✅ Refractive index considerations (particles vs medium)
- ✅ Scientifically valid, publishable results

**Client Evidence**: 3 PDFs in `Literature/` folder provided by client:
1. `FCMPASS_Software-Aids-EVs-Light-Scatter-Stand.pdf` - FCMPASS calibration workflow
2. `Mie functions_scattering_Abs-V1.pdf` - Mie scattering equations
3. `Mie functions_scattering_Abs-V2.pdf` - Updated Mie formulations

### 0.5.2 Install Mie Theory Library (Day 1 - Nov 18)

**Install miepython**:
```bash
pip install miepython
```

**Test installation**:
```python
import miepython
import numpy as np

# Test with 100nm polystyrene bead
m = 1.59 + 0.0j  # Refractive index of polystyrene
x = np.pi * 100 / 488  # Size parameter at 488nm wavelength

qext, qsca, qback, g = miepython.mie(m, x)
print(f"Scattering efficiency: {qsca}")  # Should be ~3.5
```

**Update requirements.txt**:
```txt
# Add to existing requirements.txt
miepython==2.5.3  # Mie scattering calculations
```

### 0.5.3 Implement Mie Calculator (Days 1-2 - Nov 18-19)

**File**: `src/physics/mie_scatter.py` (already stubbed, needs implementation)

**Key Implementation**:
```python
import miepython
import numpy as np
from scipy.optimize import minimize_scalar

class MieScatterCalculator:
    """Calculate light scattering using Mie theory."""
    
    def __init__(
        self,
        wavelength_nm: float = 488.0,  # Blue laser
        n_particle: float = 1.40,      # EV refractive index
        n_medium: float = 1.33          # PBS medium
    ):
        self.wavelength_nm = wavelength_nm
        self.n_particle = n_particle
        self.n_medium = n_medium
        self.m = n_particle / n_medium  # Relative refractive index
    
    def calculate_scattering_efficiency(self, diameter_nm: float) -> dict:
        """Calculate Mie scattering efficiency for given diameter."""
        # Size parameter: x = π * d / λ
        x = np.pi * diameter_nm / self.wavelength_nm
        
        # Call miepython with complex refractive index
        m = self.m + 0.0j  # Assume non-absorbing
        qext, qsca, qback, g = miepython.mie(m, x)
        
        # Calculate scatter intensities (forward and side)
        # Forward scatter ∝ qsca * diameter^2
        # Side scatter ∝ qback * diameter^2
        fsc = qsca * (diameter_nm ** 2)
        ssc = qback * (diameter_nm ** 2)
        
        return {
            'Q_ext': qext,      # Extinction efficiency
            'Q_sca': qsca,      # Scattering efficiency
            'Q_back': qback,    # Backscatter efficiency
            'g': g,             # Asymmetry parameter
            'forward_scatter': fsc,
            'side_scatter': ssc,
            'size_parameter_x': x
        }
    
    def diameter_from_scatter(
        self,
        fsc_intensity: float,
        min_diameter: float = 30.0,
        max_diameter: float = 200.0
    ) -> float:
        """
        Inverse problem: Calculate diameter from FSC intensity.
        Uses optimization to find diameter that matches observed scatter.
        """
        def objective(diameter):
            """Minimize difference between calculated and observed FSC."""
            result = self.calculate_scattering_efficiency(diameter)
            return abs(result['forward_scatter'] - fsc_intensity)
        
        # Optimize to find best-fit diameter
        res = minimize_scalar(
            objective,
            bounds=(min_diameter, max_diameter),
            method='bounded'
        )
        
        return res.x  # Return optimized diameter
    
    def calculate_wavelength_response(
        self,
        diameter_nm: float,
        wavelengths: list = [405, 488, 561, 633]
    ) -> dict:
        """Calculate scatter at multiple wavelengths."""
        original_wavelength = self.wavelength_nm
        
        results = {}
        for wavelength in wavelengths:
            self.wavelength_nm = wavelength
            result = self.calculate_scattering_efficiency(diameter_nm)
            results[f'{wavelength}nm'] = result['forward_scatter']
        
        self.wavelength_nm = original_wavelength  # Restore
        return results
```

**Testing**:
```python
# Test with known polystyrene beads
calc = MieScatterCalculator(
    wavelength_nm=488.0,
    n_particle=1.59,  # Polystyrene
    n_medium=1.33
)

# 100nm bead should give specific scatter
result = calc.calculate_scattering_efficiency(100.0)
assert 3.0 < result['Q_sca'] < 4.0  # Expected range

# Inverse problem: given scatter, find size
fsc_observed = result['forward_scatter']
diameter_calc = calc.diameter_from_scatter(fsc_observed)
assert abs(diameter_calc - 100.0) < 1.0  # Within 1nm
```

### 0.5.4 Implement FCMPASS Calibration (Days 2-3 - Nov 19-20)

**File**: `src/physics/mie_scatter.py` (FCMPASSCalibrator class)

**Implementation**:
```python
class FCMPASSCalibrator:
    """FCMPASS-style calibration using reference beads."""
    
    def __init__(self, wavelength_nm: float = 488.0):
        self.wavelength_nm = wavelength_nm
        self.calibration_curve = None
    
    def load_bead_data(self, bead_sizes: list, bead_fsc: list):
        """Load reference bead measurements."""
        self.bead_data = pd.DataFrame({
            'diameter_nm': bead_sizes,
            'fsc_measured': bead_fsc
        })
    
    def create_calibration_curve(self, n_particle: float = 1.59, n_medium: float = 1.33):
        """Fit Mie theory to bead data."""
        calc = MieScatterCalculator(self.wavelength_nm, n_particle, n_medium)
        
        # Calculate theoretical Mie scatter for each bead size
        self.bead_data['fsc_theory'] = self.bead_data['diameter_nm'].apply(
            lambda d: calc.calculate_scattering_efficiency(d)['forward_scatter']
        )
        
        # Fit linear relationship: FSC_measured = a * FSC_theory + b
        from sklearn.linear_model import LinearRegression
        X = self.bead_data[['fsc_theory']].values
        y = self.bead_data['fsc_measured'].values
        
        self.calibration_curve = LinearRegression().fit(X, y)
        self.mie_calculator = calc
    
    def calibrate_sample(self, sample_fsc: np.ndarray) -> np.ndarray:
        """Convert sample FSC values to physical diameters."""
        # Inverse transform: FSC_measured -> FSC_theory
        fsc_theory = (sample_fsc - self.calibration_curve.intercept_) / self.calibration_curve.coef_[0]
        
        # Use Mie inverse to get diameters
        diameters = np.array([
            self.mie_calculator.diameter_from_scatter(fsc)
            for fsc in fsc_theory
        ])
        
        return diameters
```

**Testing with Mock Bead Data**:
```python
# Mock reference beads (100nm, 200nm, 500nm polystyrene)
bead_sizes = [100, 200, 500]
bead_fsc = [1500, 5800, 35000]  # Mock measured FSC values

calibrator = FCMPASSCalibrator(wavelength_nm=488)
calibrator.load_bead_data(bead_sizes, bead_fsc)
calibrator.create_calibration_curve(n_particle=1.59, n_medium=1.33)

# Test with sample data
sample_fsc = np.array([2000, 3500, 6000])
sample_diameters = calibrator.calibrate_sample(sample_fsc)
print(f"Sample diameters: {sample_diameters}")
# Should give physically reasonable values (100-200nm range)
```

### 0.5.5 Update FCS Plotting Module (Day 3 - Nov 20)

**File**: `src/visualization/fcs_plots.py`

**Replace simplified calculation**:
```python
# OLD (DELETE):
def calculate_particle_size(data, fsc_channel='VFSC-H'):
    fsc_norm = (fsc_values - min) / (max - min)
    particle_size_nm = 30 + (sqrt(fsc_norm) * 120)  # WRONG

# NEW (WITH MIE):
from src.physics.mie_scatter import MieScatterCalculator

def calculate_particle_size_mie(
    data,
    fsc_channel='VFSC-H',
    wavelength_nm=488.0,
    n_particle=1.40,  # EV refractive index
    n_medium=1.33
):
    """Calculate particle size using Mie scattering theory."""
    calc = MieScatterCalculator(wavelength_nm, n_particle, n_medium)
    
    fsc_values = data[fsc_channel].values
    
    # Calculate diameter for each event using Mie inverse
    diameters = np.array([
        calc.diameter_from_scatter(fsc, min_diameter=30, max_diameter=200)
        for fsc in fsc_values
    ])
    
    data['particle_size_nm'] = diameters
    logger.info(f"✅ Calculated particle sizes using Mie theory (mean: {diameters.mean():.1f}nm)")
    
    return data
```

### 0.5.6 Reprocess All Parquet Files (Day 4 - Nov 21)

**Update conversion script**: `scripts/convert_fcs_to_parquet.py`

```python
# Update to use Mie-based calculation
from src.visualization.fcs_plots import calculate_particle_size_mie

# In process_fcs_file function:
data = calculate_particle_size_mie(
    data,
    fsc_channel=fsc_channel,
    wavelength_nm=488.0,
    n_particle=1.40,  # EV refractive index (adjustable)
    n_medium=1.33
)
```

**Re-run batch conversion**:
```bash
python scripts/convert_fcs_to_parquet.py
```

**Expected changes**:
- All 66 Parquet files updated with accurate `particle_size_nm` column
- Size distributions should now be physically meaningful
- Sizes should correlate better with NTA measurements

### 0.5.7 Validate Against NTA (Day 5 - Nov 22)

**Create validation script**: `scripts/validate_mie_vs_nta.py`

```python
#!/usr/bin/env python3
"""Validate Mie-calculated FCS sizes against NTA camera-based sizes."""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import pearsonr
import matplotlib.pyplot as plt

# Load FCS statistics (with Mie sizes)
fcs_stats = pd.read_csv('data/parquet/nanofacs/statistics/batch_summary.csv')

# Load NTA statistics
nta_stats = pd.read_csv('data/parquet/nta/statistics/nta_summary.csv')

# Match samples by ID
merged = fcs_stats.merge(nta_stats, on='sample_id', how='inner')

# Compare mean sizes
fcs_mean = merged['mean_particle_size_nm']
nta_d50 = merged['D50_nm']

# Calculate correlation
corr, p_value = pearsonr(fcs_mean, nta_d50)
print(f"Correlation: {corr:.3f} (p={p_value:.4f})")

# Plot correlation
plt.figure(figsize=(8, 6))
plt.scatter(fcs_mean, nta_d50, alpha=0.6)
plt.plot([50, 150], [50, 150], 'r--', label='Perfect agreement')
plt.xlabel('FCS Mean Size (nm, Mie theory)')
plt.ylabel('NTA D50 (nm)')
plt.title(f'FCS vs NTA Size Comparison (r={corr:.3f})')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('figures/mie_validation.png', dpi=300, bbox_inches='tight')

# Calculate agreement metrics
difference_pct = abs(fcs_mean - nta_d50) / nta_d50 * 100
agreement = (difference_pct < 20).sum() / len(difference_pct) * 100

print(f"\nAgreement (<20% difference): {agreement:.1f}%")
print(f"Mean difference: {difference_pct.mean():.1f}%")
```

**Success Criteria**:
- ✅ Correlation coefficient > 0.7 (strong positive correlation)
- ✅ >70% of samples within 20% agreement
- ✅ No systematic bias (scatter around perfect agreement line)

### 0.5.8 Documentation & Testing (Day 5 - Nov 22)

**Update documentation**:
```markdown
# docs/MIE_SCATTERING_GUIDE.md

## Mie Theory Implementation

### Overview
Particle sizes are calculated using Mie scattering theory, which relates
light scatter intensity to particle diameter based on wavelength and
refractive indices.

### Theory
- Size parameter: x = πd/λ
- Relative refractive index: m = n_particle / n_medium
- Scattering efficiency calculated via miepython library

### Configuration
Default parameters for EVs:
- Wavelength: 488nm (blue laser)
- n_particle: 1.40 (typical for EVs)
- n_medium: 1.33 (PBS buffer)

### Validation
Cross-validated against NTA measurements (correlation > 0.7)
```

**Unit tests**: `tests/test_mie_scatter.py`
```python
import pytest
from src.physics.mie_scatter import MieScatterCalculator, FCMPASSCalibrator

def test_mie_calculator_100nm_bead():
    calc = MieScatterCalculator(488.0, 1.59, 1.33)
    result = calc.calculate_scattering_efficiency(100.0)
    assert 3.0 < result['Q_sca'] < 4.0

def test_inverse_problem():
    calc = MieScatterCalculator(488.0, 1.59, 1.33)
    result = calc.calculate_scattering_efficiency(100.0)
    diameter = calc.diameter_from_scatter(result['forward_scatter'])
    assert abs(diameter - 100.0) < 1.0

def test_wavelength_response():
    calc = MieScatterCalculator(488.0, 1.59, 1.33)
    response = calc.calculate_wavelength_response(80.0)
    assert '405nm' in response
    assert '488nm' in response
```

**Deliverables for Phase 0.5**:
- ✅ miepython library installed and tested
- ✅ MieScatterCalculator fully implemented (200+ lines)
- ✅ FCMPASSCalibrator implemented (150+ lines)
- ✅ FCS plotting updated with Mie calculations
- ✅ All 66 Parquet files reprocessed with accurate sizes
- ✅ Validation against NTA complete (correlation report)
- ✅ Documentation updated (MIE_SCATTERING_GUIDE.md)
- ✅ Unit tests passing (>90% coverage)
- ✅ Physically valid, publishable particle sizes ✨

---

## Phase 1: FCS File Parser (Week 1-2)

**Priority**: CRITICAL  
**Duration**: 10 working days  
**Goal**: Parse FCS files, extract metadata and events, convert to Parquet

### 1.1 FCS File Format Understanding (Days 1-2)

#### Research & Documentation
1. **Study FCS file structure**:
   - FCS 2.0, 3.0, 3.1 specifications
   - Header structure (TEXT, DATA, ANALYSIS segments)
   - Metadata (keywords like $PnN, $PnS, $PnR)
   - Event data encoding

2. **Analyze existing data**:
   - Review sample FCS files from Bio Varam
   - Identify channels used (FSC, SSC, FL1-FL6)
   - Document fluorophore markers (CD9, CD63, CD81, etc.)
   - Note any instrument-specific quirks

3. **Study existing parsers**:
   - `fcsparser` library capabilities
   - `readfcs` library advantages
   - `FlowKit` advanced features

**Deliverable**: FCS Format Documentation (Markdown)

### 1.2 Base Parser Class (Day 3)

**File**: `src/parsers/base_parser.py`

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import pyarrow as pa
from loguru import logger

class BaseParser(ABC):
    """Abstract base class for all data parsers."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.metadata: Dict[str, Any] = {}
        self.data: Optional[pd.DataFrame] = None
        
    @abstractmethod
    def parse(self) -> pd.DataFrame:
        """Parse the file and return DataFrame."""
        pass
    
    @abstractmethod
    def extract_metadata(self) -> Dict[str, Any]:
        """Extract metadata from file."""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate file integrity."""
        pass
    
    def to_parquet(self, output_path: Path, compression: str = 'snappy') -> None:
        """Convert parsed data to Parquet format."""
        if self.data is None:
            raise ValueError("No data to convert. Call parse() first.")
        
        # Add metadata as Parquet file metadata
        table = pa.Table.from_pandas(self.data)
        
        # Store metadata in Parquet schema
        metadata_dict = {
            'source_file': str(self.file_path),
            'parser_version': '1.0.0',
            **self.metadata
        }
        
        # Convert metadata values to strings for Parquet
        metadata_bytes = {
            k.encode(): str(v).encode() 
            for k, v in metadata_dict.items()
        }
        
        # Create new schema with metadata
        schema = table.schema.with_metadata(metadata_bytes)
        table = table.cast(schema)
        
        # Write to Parquet with compression
        import pyarrow.parquet as pq
        pq.write_table(
            table, 
            output_path, 
            compression=compression,
            use_dictionary=True,  # Enable dictionary encoding
            write_statistics=True  # Enable column statistics
        )
        
        logger.info(f"Saved Parquet file: {output_path}")
```

**Testing**:
```python
# tests/test_parsers/test_base_parser.py
import pytest
from src.parsers.base_parser import BaseParser

def test_base_parser_is_abstract():
    with pytest.raises(TypeError):
        BaseParser("dummy.fcs")
```

### 1.3 FCS Parser Implementation (Days 4-7)

**File**: `src/parsers/fcs_parser.py`

```python
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import fcsparser
from loguru import logger
from .base_parser import BaseParser

class FCSParser(BaseParser):
    """Parser for Flow Cytometry Standard (FCS) files."""
    
    REQUIRED_CHANNELS = ['FSC-A', 'SSC-A']  # Minimum required
    
    def __init__(self, file_path: Path, compensate: bool = False):
        super().__init__(file_path)
        self.compensate = compensate
        self.channel_names: List[str] = []
        self.sample_id: Optional[str] = None
        
    def validate(self) -> bool:
        """Validate FCS file."""
        try:
            # Check file exists and is readable
            if not self.file_path.exists():
                logger.error(f"File not found: {self.file_path}")
                return False
            
            # Check file extension
            if self.file_path.suffix.lower() != '.fcs':
                logger.warning(f"Unexpected extension: {self.file_path.suffix}")
            
            # Try to read header
            with open(self.file_path, 'rb') as f:
                header = f.read(6).decode('ascii')
                if not header.startswith('FCS'):
                    logger.error(f"Invalid FCS header: {header}")
                    return False
            
            logger.info(f"FCS file validated: {self.file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False
    
    def parse(self) -> pd.DataFrame:
        """Parse FCS file and return event data as DataFrame."""
        try:
            # Parse FCS file using fcsparser
            meta, data = fcsparser.parse(
                str(self.file_path),
                meta_data_only=False,
                reformat_meta=True
            )
            
            self.metadata = meta
            self.data = data
            
            # Extract sample ID from filename or metadata
            self.sample_id = self._extract_sample_id()
            
            # Get channel names
            self.channel_names = list(data.columns)
            
            # Add sample ID and timestamp columns
            self.data['sample_id'] = self.sample_id
            self.data['file_name'] = self.file_path.name
            self.data['instrument_type'] = 'flow_cytometry'
            self.data['parse_timestamp'] = pd.Timestamp.now()
            
            # Apply compensation if requested
            if self.compensate and self._has_compensation_matrix():
                self.data = self._apply_compensation(self.data)
            
            logger.info(f"Parsed {len(self.data)} events from {self.file_path.name}")
            logger.info(f"Channels: {self.channel_names}")
            
            return self.data
            
        except Exception as e:
            logger.error(f"Failed to parse FCS file: {e}")
            raise
    
    def extract_metadata(self) -> Dict[str, Any]:
        """Extract relevant metadata from FCS file."""
        if not self.metadata:
            raise ValueError("No metadata available. Call parse() first.")
        
        # Extract key metadata fields
        extracted = {
            'sample_id': self.sample_id,
            'file_name': self.file_path.name,
            'instrument_type': 'flow_cytometry',
            'total_events': int(self.metadata.get('$TOT', 0)),
            'parameters': int(self.metadata.get('$PAR', 0)),
            'acquisition_date': self.metadata.get('$DATE', 'Unknown'),
            'acquisition_time': self.metadata.get('$BTIM', 'Unknown'),
            'cytometer': self.metadata.get('$CYT', 'Unknown'),
            'operator': self.metadata.get('$OP', 'Unknown'),
            'specimen': self.metadata.get('$SMNO', 'Unknown'),
        }
        
        # Extract channel information
        channels = {}
        n_params = int(self.metadata.get('$PAR', 0))
        
        for i in range(1, n_params + 1):
            name = self.metadata.get(f'$P{i}N', f'Param{i}')
            stain = self.metadata.get(f'$P{i}S', 'Unstained')
            range_val = self.metadata.get(f'$P{i}R', 'Unknown')
            
            channels[name] = {
                'stain': stain,
                'range': range_val,
                'index': i
            }
        
        extracted['channels'] = channels
        extracted['channel_count'] = len(channels)
        extracted['channel_names'] = list(channels.keys())
        
        # Temperature if available
        if '$TEMP' in self.metadata:
            extracted['temperature'] = float(self.metadata['$TEMP'])
        
        return extracted
    
    def _extract_sample_id(self) -> str:
        """Extract sample ID from filename or metadata."""
        # Try to extract from filename (e.g., BV_EXO_001_FC.fcs)
        filename = self.file_path.stem
        parts = filename.split('_')
        
        # If filename follows convention: SAMPLEID_INSTRUMENT
        if len(parts) >= 2:
            sample_id = '_'.join(parts[:-1])  # Everything except last part
            logger.info(f"Extracted sample ID: {sample_id}")
            return sample_id
        
        # Fallback to metadata
        sample_id = self.metadata.get('$SMNO', filename)
        logger.info(f"Using sample ID from metadata: {sample_id}")
        return sample_id
    
    def _has_compensation_matrix(self) -> bool:
        """Check if compensation matrix is available."""
        return '$COMP' in self.metadata or '$SPILLOVER' in self.metadata
    
    def _apply_compensation(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply compensation matrix to data."""
        # Implementation depends on compensation format
        # This is a placeholder - actual implementation needed
        logger.warning("Compensation not yet implemented")
        return data
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate basic statistics for each channel."""
        if self.data is None:
            raise ValueError("No data available. Call parse() first.")
        
        stats = {}
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if col in self.channel_names:
                stats[col] = {
                    'mean': float(self.data[col].mean()),
                    'median': float(self.data[col].median()),
                    'std': float(self.data[col].std()),
                    'min': float(self.data[col].min()),
                    'max': float(self.data[col].max()),
                    'q25': float(self.data[col].quantile(0.25)),
                    'q75': float(self.data[col].quantile(0.75)),
                }
        
        return stats
```

**Usage Example**:
```python
from pathlib import Path
from src.parsers.fcs_parser import FCSParser

# Parse FCS file
fcs_path = Path("data/fcs_files/BV_EXO_001_FC.fcs")
parser = FCSParser(fcs_path, compensate=False)

# Validate
if parser.validate():
    # Parse data
    data = parser.parse()
    print(f"Loaded {len(data)} events")
    
    # Extract metadata
    metadata = parser.extract_metadata()
    print(f"Channels: {metadata['channel_names']}")
    
    # Get statistics
    stats = parser.get_statistics()
    print(f"FSC-A mean: {stats['FSC-A']['mean']}")
    
    # Save to Parquet
    output_path = Path("data/parquet/BV_EXO_001_FC.parquet")
    parser.to_parquet(output_path, compression='snappy')
```

### 1.4 Testing FCS Parser (Day 8)

**File**: `tests/test_parsers/test_fcs_parser.py`

```python
import pytest
from pathlib import Path
import pandas as pd
from src.parsers.fcs_parser import FCSParser

@pytest.fixture
def sample_fcs_file():
    """Fixture for test FCS file."""
    return Path("tests/fixtures/sample.fcs")

def test_fcs_parser_initialization(sample_fcs_file):
    parser = FCSParser(sample_fcs_file)
    assert parser.file_path == sample_fcs_file
    assert parser.data is None

def test_fcs_parser_validation(sample_fcs_file):
    parser = FCSParser(sample_fcs_file)
    assert parser.validate() == True

def test_fcs_parser_invalid_file():
    parser = FCSParser(Path("nonexistent.fcs"))
    assert parser.validate() == False

def test_fcs_parser_parse(sample_fcs_file):
    parser = FCSParser(sample_fcs_file)
    data = parser.parse()
    
    assert isinstance(data, pd.DataFrame)
    assert len(data) > 0
    assert 'sample_id' in data.columns
    assert 'instrument_type' in data.columns

def test_fcs_metadata_extraction(sample_fcs_file):
    parser = FCSParser(sample_fcs_file)
    parser.parse()
    metadata = parser.extract_metadata()
    
    assert 'sample_id' in metadata
    assert 'total_events' in metadata
    assert 'channels' in metadata
    assert metadata['instrument_type'] == 'flow_cytometry'

def test_fcs_to_parquet(sample_fcs_file, tmp_path):
    parser = FCSParser(sample_fcs_file)
    parser.parse()
    
    output_file = tmp_path / "test_output.parquet"
    parser.to_parquet(output_file)
    
    assert output_file.exists()
    
    # Verify can read back
    df = pd.read_parquet(output_file)
    assert len(df) == len(parser.data)

def test_fcs_sample_id_extraction(sample_fcs_file):
    # Test with standard naming convention
    parser = FCSParser(Path("BV_EXO_001_FC.fcs"))
    parser.parse()
    assert parser.sample_id == "BV_EXO_001"
```

### 1.5 Parquet Writer Utility (Day 9)

**File**: `src/parsers/parquet_writer.py`

```python
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from loguru import logger

class ParquetWriter:
    """Utility class for writing DataFrames to Parquet with metadata."""
    
    @staticmethod
    def write(
        data: pd.DataFrame,
        output_path: Path,
        metadata: Optional[Dict[str, Any]] = None,
        compression: str = 'snappy',
        partition_cols: Optional[list] = None
    ) -> None:
        """
        Write DataFrame to Parquet file with optional metadata and partitioning.
        
        Args:
            data: DataFrame to write
            output_path: Output file path
            metadata: Dictionary of metadata to embed
            compression: Compression codec ('snappy', 'gzip', 'zstd', 'none')
            partition_cols: Columns to partition by (for dataset writing)
        """
        try:
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert DataFrame to Arrow Table
            table = pa.Table.from_pandas(data)
            
            # Add metadata if provided
            if metadata:
                metadata_bytes = {
                    k.encode(): str(v).encode() 
                    for k, v in metadata.items()
                }
                schema = table.schema.with_metadata(metadata_bytes)
                table = table.cast(schema)
            
            # Write to Parquet
            pq.write_table(
                table,
                output_path,
                compression=compression,
                use_dictionary=True,
                write_statistics=True,
                version='2.6'  # Latest Parquet format version
            )
            
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"Wrote Parquet file: {output_path} ({file_size_mb:.2f} MB)")
            
        except Exception as e:
            logger.error(f"Failed to write Parquet file: {e}")
            raise
    
    @staticmethod
    def read_with_metadata(parquet_path: Path) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Read Parquet file and extract embedded metadata.
        
        Returns:
            Tuple of (DataFrame, metadata_dict)
        """
        try:
            # Read Parquet file
            table = pq.read_table(parquet_path)
            
            # Extract metadata
            metadata = {}
            if table.schema.metadata:
                metadata = {
                    k.decode(): v.decode() 
                    for k, v in table.schema.metadata.items()
                }
            
            # Convert to DataFrame
            df = table.to_pandas()
            
            logger.info(f"Read Parquet file: {parquet_path}")
            return df, metadata
            
        except Exception as e:
            logger.error(f"Failed to read Parquet file: {e}")
            raise
    
    @staticmethod
    def get_file_info(parquet_path: Path) -> Dict[str, Any]:
        """Get information about a Parquet file without loading data."""
        try:
            parquet_file = pq.ParquetFile(parquet_path)
            
            info = {
                'num_rows': parquet_file.metadata.num_rows,
                'num_columns': parquet_file.metadata.num_columns,
                'num_row_groups': parquet_file.metadata.num_row_groups,
                'format_version': parquet_file.metadata.format_version,
                'created_by': parquet_file.metadata.created_by,
                'serialized_size': parquet_file.metadata.serialized_size,
                'schema': parquet_file.schema_arrow,
            }
            
            # Get column names and types
            info['columns'] = [
                {
                    'name': field.name,
                    'type': str(field.type)
                }
                for field in parquet_file.schema_arrow
            ]
            
            # Get compression info from first row group
            if parquet_file.metadata.num_row_groups > 0:
                rg = parquet_file.metadata.row_group(0)
                compressions = set()
                for i in range(rg.num_columns):
                    col = rg.column(i)
                    compressions.add(col.compression)
                info['compression'] = list(compressions)
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get Parquet file info: {e}")
            raise
```

### 1.6 Documentation & Examples (Day 10)

Create comprehensive documentation:

**File**: `docs/parsers/fcs_parser_guide.md`

```markdown
# FCS Parser Guide

## Overview
The FCS Parser handles Flow Cytometry Standard files (versions 2.0, 3.0, 3.1).

## Usage

### Basic Parsing
\`\`\`python
from src.parsers.fcs_parser import FCSParser

parser = FCSParser("data/BV_EXO_001_FC.fcs")
data = parser.parse()
\`\`\`

### Extract Metadata
\`\`\`python
metadata = parser.extract_metadata()
print(f"Sample ID: {metadata['sample_id']}")
print(f"Total events: {metadata['total_events']}")
print(f"Channels: {metadata['channel_names']}")
\`\`\`

### Convert to Parquet
\`\`\`python
parser.to_parquet("data/parquet/BV_EXO_001_FC.parquet")
\`\`\`

### Get Statistics
\`\`\`python
stats = parser.get_statistics()
for channel, channel_stats in stats.items():
    print(f"{channel}: mean={channel_stats['mean']:.2f}")
\`\`\`

## Naming Convention
Files should follow: `SAMPLEID_INSTRUMENT_DATE.fcs`
Example: `BV_EXO_001_FC_20251114.fcs`

## Output Schema
Parquet files contain:
- All original FCS channels (FSC-A, SSC-A, FL1-H, etc.)
- `sample_id`: Extracted from filename
- `file_name`: Original FCS filename
- `instrument_type`: "flow_cytometry"
- `parse_timestamp`: When file was parsed

## Troubleshooting
...
```

**Deliverables for Phase 1**:
- ✅ Functional FCS parser with validation
- ✅ Parquet conversion with embedded metadata
- ✅ Comprehensive unit tests (>90% coverage)
- ✅ Documentation and usage examples
- ✅ Sample Parquet files for testing

---

## Phase 2: NTA Text Parser (Week 3-4)

**Priority**: CRITICAL  
**Duration**: 10 working days  
**Goal**: Parse ZetaView NTA text files, extract size distributions and metadata

### 2.1 NTA Format Analysis (Days 11-12)

#### Research & Documentation
1. **Study ZetaView text file format**:
   - Review sample files from Bio Varam
   - Identify header structure
   - Document data columns (Size, Concentration, Volume, Area)
   - Note metadata fields (Temperature, pH, Conductivity)

2. **Understand NTA measurements**:
   - Particle size range (20-2000 nm)
   - Size distribution representation
   - Concentration calculations
   - Zeta potential (if available)

**Sample NTA file structure** (hypothetical):
```
ZetaView NTA Analysis Results
Date: 2025-11-14
Time: 10:30:15
Operator: Researcher1
Sample: BV_EXO_001
Temperature: 25.2 C
pH: 7.4
Conductivity: 15.8 mS/cm
Viscosity: 0.89 mPa·s
...

Size (nm), Concentration (particles/mL), Volume, Area
40, 1.2e8, 0.05, 100
45, 2.3e8, 0.08, 150
50, 3.5e8, 0.12, 200
...
```

**Deliverable**: NTA Format Specification Document

### 2.2 NTA Parser Implementation (Days 13-16)

**File**: `src/parsers/nta_parser.py`

```python
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import re
from loguru import logger
from .base_parser import BaseParser

class NTAParser(BaseParser):
    """Parser for Nanoparticle Tracking Analysis (NTA) text files from ZetaView."""
    
    EXPECTED_COLUMNS = ['Size (nm)', 'Concentration', 'Volume', 'Area']
    
    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self.sample_id: Optional[str] = None
        self.measurement_params: Dict[str, Any] = {}
        
    def validate(self) -> bool:
        """Validate NTA text file."""
        try:
            if not self.file_path.exists():
                logger.error(f"File not found: {self.file_path}")
                return False
            
            # Check file extension
            if self.file_path.suffix.lower() not in ['.txt', '.csv']:
                logger.warning(f"Unexpected extension: {self.file_path.suffix}")
            
            # Try to read first few lines
            with open(self.file_path, 'r', encoding='utf-8') as f:
                lines = [f.readline() for _ in range(10)]
                
            # Check for ZetaView signature or expected content
            content = ''.join(lines)
            if 'ZetaView' not in content and 'Size' not in content:
                logger.warning("File may not be ZetaView NTA format")
            
            logger.info(f"NTA file validated: {self.file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False
    
    def parse(self) -> pd.DataFrame:
        """Parse NTA text file and return size distribution data."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into metadata and data sections
            lines = content.split('\n')
            
            # Extract metadata
            self.metadata = self._parse_metadata(lines)
            self.sample_id = self._extract_sample_id()
            
            # Find where data table starts
            data_start_idx = self._find_data_start(lines)
            
            if data_start_idx is None:
                raise ValueError("Could not find data table in NTA file")
            
            # Parse data table
            data_lines = lines[data_start_idx:]
            self.data = self._parse_data_table(data_lines)
            
            # Add metadata columns
            self.data['sample_id'] = self.sample_id
            self.data['file_name'] = self.file_path.name
            self.data['instrument_type'] = 'nta'
            self.data['parse_timestamp'] = pd.Timestamp.now()
            
            # Add measurement parameters
            for key, value in self.measurement_params.items():
                self.data[f'param_{key}'] = value
            
            logger.info(f"Parsed {len(self.data)} size bins from {self.file_path.name}")
            
            return self.data
            
        except Exception as e:
            logger.error(f"Failed to parse NTA file: {e}")
            raise
    
    def _parse_metadata(self, lines: List[str]) -> Dict[str, Any]:
        """Extract metadata from header lines."""
        metadata = {}
        
        # Common metadata patterns
        patterns = {
            'date': r'Date[:\s]+(.+)',
            'time': r'Time[:\s]+(.+)',
            'operator': r'Operator[:\s]+(.+)',
            'sample': r'Sample[:\s]+(.+)',
            'temperature': r'Temperature[:\s]+([0-9.]+)',
            'ph': r'pH[:\s]+([0-9.]+)',
            'conductivity': r'Conductivity[:\s]+([0-9.]+)',
            'viscosity': r'Viscosity[:\s]+([0-9.]+)',
            'scattering_intensity': r'Scattering[:\s]+([0-9.]+)',
            'frame_rate': r'Frame Rate[:\s]+([0-9.]+)',
            'number_of_frames': r'Frames[:\s]+([0-9]+)',
        }
        
        for line in lines[:50]:  # Check first 50 lines for metadata
            for key, pattern in patterns.items():
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    
                    # Convert numeric values
                    if key in ['temperature', 'ph', 'conductivity', 'viscosity', 
                             'scattering_intensity', 'frame_rate']:
                        try:
                            value = float(value)
                            self.measurement_params[key] = value
                        except ValueError:
                            pass
                    elif key == 'number_of_frames':
                        try:
                            value = int(value)
                            self.measurement_params[key] = value
                        except ValueError:
                            pass
                    
                    metadata[key] = value
        
        return metadata
    
    def _find_data_start(self, lines: List[str]) -> Optional[int]:
        """Find the line index where data table starts."""
        for i, line in enumerate(lines):
            # Look for column headers
            if 'Size' in line and ('Concentration' in line or 'particles' in line):
                return i
        return None
    
    def _parse_data_table(self, lines: List[str]) -> pd.DataFrame:
        """Parse the data table section."""
        # First line should be headers
        header_line = lines[0]
        
        # Detect delimiter (comma, tab, or whitespace)
        if ',' in header_line:
            delimiter = ','
        elif '\t' in header_line:
            delimiter = '\t'
        else:
            delimiter = r'\s+'
        
        # Parse headers
        headers = re.split(delimiter, header_line.strip())
        headers = [h.strip() for h in headers if h.strip()]
        
        # Parse data rows
        data_rows = []
        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            values = re.split(delimiter, line)
            values = [v.strip() for v in values if v.strip()]
            
            if len(values) == len(headers):
                data_rows.append(values)
        
        # Create DataFrame
        df = pd.DataFrame(data_rows, columns=headers)
        
        # Convert columns to appropriate types
        for col in df.columns:
            try:
                # Try to convert to numeric
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except:
                pass
        
        # Standardize column names
        df = self._standardize_column_names(df)
        
        return df
    
    def _standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names to consistent format."""
        rename_map = {}
        
        for col in df.columns:
            col_lower = col.lower()
            
            if 'size' in col_lower or 'diameter' in col_lower:
                rename_map[col] = 'size_nm'
            elif 'concentration' in col_lower or 'particles' in col_lower:
                rename_map[col] = 'concentration'
            elif 'volume' in col_lower:
                rename_map[col] = 'volume'
            elif 'area' in col_lower:
                rename_map[col] = 'area'
            elif 'intensity' in col_lower or 'scatter' in col_lower:
                rename_map[col] = 'scattering_intensity'
        
        df = df.rename(columns=rename_map)
        
        # Ensure size_nm exists
        if 'size_nm' not in df.columns:
            raise ValueError("Could not find particle size column")
        
        return df
    
    def extract_metadata(self) -> Dict[str, Any]:
        """Extract relevant metadata from NTA file."""
        if not self.metadata:
            raise ValueError("No metadata available. Call parse() first.")
        
        extracted = {
            'sample_id': self.sample_id,
            'file_name': self.file_path.name,
            'instrument_type': 'nta',
            'date': self.metadata.get('date', 'Unknown'),
            'time': self.metadata.get('time', 'Unknown'),
            'operator': self.metadata.get('operator', 'Unknown'),
            'measurement_params': self.measurement_params,
        }
        
        return extracted
    
    def _extract_sample_id(self) -> str:
        """Extract sample ID from filename or metadata."""
        # Try metadata first
        if 'sample' in self.metadata:
            return self.metadata['sample']
        
        # Extract from filename (e.g., BV_EXO_001_NTA.txt)
        filename = self.file_path.stem
        parts = filename.split('_')
        
        if len(parts) >= 2:
            sample_id = '_'.join(parts[:-1])
            logger.info(f"Extracted sample ID from filename: {sample_id}")
            return sample_id
        
        logger.warning(f"Could not extract sample ID, using filename: {filename}")
        return filename
    
    def get_size_distribution_stats(self) -> Dict[str, Any]:
        """Calculate size distribution statistics."""
        if self.data is None or 'size_nm' not in self.data.columns:
            raise ValueError("No size data available")
        
        size_col = 'size_nm'
        conc_col = 'concentration' if 'concentration' in self.data.columns else None
        
        if conc_col:
            # Weighted statistics by concentration
            total_conc = self.data[conc_col].sum()
            weights = self.data[conc_col] / total_conc
            
            mean_size = (self.data[size_col] * weights).sum()
            
            # Find mode (size with highest concentration)
            mode_idx = self.data[conc_col].idxmax()
            mode_size = self.data.loc[mode_idx, size_col]
            
            # Calculate D10, D50, D90 (cumulative distribution)
            cumsum = (self.data[conc_col].cumsum() / total_conc * 100)
            d10 = self.data.loc[cumsum >= 10, size_col].iloc[0] if any(cumsum >= 10) else None
            d50 = self.data.loc[cumsum >= 50, size_col].iloc[0] if any(cumsum >= 50) else None
            d90 = self.data.loc[cumsum >= 90, size_col].iloc[0] if any(cumsum >= 90) else None
        else:
            # Simple statistics without weighting
            mean_size = self.data[size_col].mean()
            mode_size = self.data[size_col].mode()[0] if len(self.data[size_col].mode()) > 0 else None
            d10 = self.data[size_col].quantile(0.1)
            d50 = self.data[size_col].quantile(0.5)
            d90 = self.data[size_col].quantile(0.9)
        
        stats = {
            'mean_size_nm': float(mean_size),
            'mode_size_nm': float(mode_size) if mode_size else None,
            'min_size_nm': float(self.data[size_col].min()),
            'max_size_nm': float(self.data[size_col].max()),
            'd10_nm': float(d10) if d10 is not None else None,
            'd50_nm': float(d50) if d50 is not None else None,
            'd90_nm': float(d90) if d90 is not None else None,
            'size_range_nm': float(self.data[size_col].max() - self.data[size_col].min()),
        }
        
        if conc_col:
            stats['total_concentration'] = float(self.data[conc_col].sum())
            stats['peak_concentration'] = float(self.data[conc_col].max())
        
        return stats
```

**Usage Example**:
```python
from src.parsers.nta_parser import NTAParser

# Parse NTA file
nta_path = Path("data/nta_data/BV_EXO_001_NTA.txt")
parser = NTAParser(nta_path)

if parser.validate():
    data = parser.parse()
    print(f"Loaded {len(data)} size bins")
    
    # Get size distribution stats
    stats = parser.get_size_distribution_stats()
    print(f"Mean size: {stats['mean_size_nm']:.1f} nm")
    print(f"D50: {stats['d50_nm']:.1f} nm")
    
    # Save to Parquet
    output_path = Path("data/parquet/BV_EXO_001_NTA.parquet")
    parser.to_parquet(output_path)
```

### 2.3 Testing NTA Parser (Days 17-18)

**File**: `tests/test_parsers/test_nta_parser.py`

```python
import pytest
from pathlib import Path
import pandas as pd
from src.parsers.nta_parser import NTAParser

@pytest.fixture
def sample_nta_file():
    return Path("tests/fixtures/sample_nta.txt")

def test_nta_parser_validation(sample_nta_file):
    parser = NTAParser(sample_nta_file)
    assert parser.validate() == True

def test_nta_parser_parse(sample_nta_file):
    parser = NTAParser(sample_nta_file)
    data = parser.parse()
    
    assert isinstance(data, pd.DataFrame)
    assert 'size_nm' in data.columns
    assert 'sample_id' in data.columns
    assert len(data) > 0

def test_nta_metadata_extraction(sample_nta_file):
    parser = NTAParser(sample_nta_file)
    parser.parse()
    metadata = parser.extract_metadata()
    
    assert 'sample_id' in metadata
    assert metadata['instrument_type'] == 'nta'

def test_nta_size_distribution_stats(sample_nta_file):
    parser = NTAParser(sample_nta_file)
    parser.parse()
    stats = parser.get_size_distribution_stats()
    
    assert 'mean_size_nm' in stats
    assert 'd50_nm' in stats
    assert stats['mean_size_nm'] > 0
```

### 2.4 Unified Parquet Schema (Day 19)

Create a unified schema that accommodates both FCS and NTA data:

**File**: `src/parsers/unified_schema.py`

```python
from typing import Dict, Any, List
import pyarrow as pa

class UnifiedSchema:
    """Defines unified Parquet schema for all instrument types."""
    
    # Common columns across all instruments
    COMMON_SCHEMA = {
        'sample_id': pa.string(),
        'file_name': pa.string(),
        'instrument_type': pa.string(),  # 'flow_cytometry', 'nta', 'tem', 'western_blot'
        'parse_timestamp': pa.timestamp('ms'),
    }
    
    # Instrument-specific schemas
    FCS_SCHEMA = {
        # Dynamic - depends on FCS channels
        # Typically: FSC-A, SSC-A, FL1-H, FL2-H, etc.
    }
    
    NTA_SCHEMA = {
        'size_nm': pa.float64(),
        'concentration': pa.float64(),
        'volume': pa.float64(),
        'area': pa.float64(),
        'scattering_intensity': pa.float64(),
        # Measurement parameters
        'param_temperature': pa.float64(),
        'param_ph': pa.float64(),
        'param_conductivity': pa.float64(),
    }
    
    @classmethod
    def get_schema(cls, instrument_type: str) -> pa.Schema:
        """Get PyArrow schema for given instrument type."""
        if instrument_type == 'flow_cytometry':
            # FCS schema is dynamic, return common fields only
            return pa.schema(cls.COMMON_SCHEMA)
        elif instrument_type == 'nta':
            return pa.schema({**cls.COMMON_SCHEMA, **cls.NTA_SCHEMA})
        else:
            raise ValueError(f"Unknown instrument type: {instrument_type}")
```

### 2.5 Batch Processing Script (Day 20)

Create utility to batch process multiple files:

**File**: `scripts/batch_parse.py`

```python
#!/usr/bin/env python3
"""
Batch process FCS and NTA files to Parquet format.
"""

from pathlib import Path
from typing import List
from concurrent.futures import ProcessPoolExecutor, as_completed
from loguru import logger
from src.parsers.fcs_parser import FCSParser
from src.parsers.nta_parser import NTAParser

def process_fcs_file(file_path: Path, output_dir: Path) -> bool:
    """Process single FCS file."""
    try:
        parser = FCSParser(file_path)
        if parser.validate():
            parser.parse()
            output_path = output_dir / f"{file_path.stem}.parquet"
            parser.to_parquet(output_path)
            logger.info(f"✓ Processed: {file_path.name}")
            return True
    except Exception as e:
        logger.error(f"✗ Failed to process {file_path.name}: {e}")
    return False

def process_nta_file(file_path: Path, output_dir: Path) -> bool:
    """Process single NTA file."""
    try:
        parser = NTAParser(file_path)
        if parser.validate():
            parser.parse()
            output_path = output_dir / f"{file_path.stem}.parquet"
            parser.to_parquet(output_path)
            logger.info(f"✓ Processed: {file_path.name}")
            return True
    except Exception as e:
        logger.error(f"✗ Failed to process {file_path.name}: {e}")
    return False

def batch_process(
    input_dir: Path,
    output_dir: Path,
    file_pattern: str,
    parser_type: str,
    max_workers: int = 4
) -> None:
    """
    Batch process files in parallel.
    
    Args:
        input_dir: Directory containing input files
        output_dir: Directory for output Parquet files
        file_pattern: Glob pattern for files (e.g., "*.fcs")
        parser_type: "fcs" or "nta"
        max_workers: Number of parallel workers
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    files = list(input_dir.glob(file_pattern))
    logger.info(f"Found {len(files)} files to process")
    
    process_func = process_fcs_file if parser_type == "fcs" else process_nta_file
    
    success_count = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_func, file_path, output_dir): file_path
            for file_path in files
        }
        
        for future in as_completed(futures):
            if future.result():
                success_count += 1
    
    logger.info(f"Processed {success_count}/{len(files)} files successfully")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch convert files to Parquet")
    parser.add_argument("input_dir", type=Path, help="Input directory")
    parser.add_argument("output_dir", type=Path, help="Output directory")
    parser.add_argument("--type", choices=["fcs", "nta"], required=True)
    parser.add_argument("--pattern", default="*", help="File pattern (default: *)")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers")
    
    args = parser.parse_args()
    
    batch_process(
        args.input_dir,
        args.output_dir,
        f"{args.pattern}.{'fcs' if args.type == 'fcs' else 'txt'}",
        args.type,
        args.workers
    )
```

**Usage**:
```bash
# Process all FCS files
python scripts/batch_parse.py data/fcs_files data/parquet --type fcs

# Process all NTA files
python scripts/batch_parse.py data/nta_data data/parquet --type nta --workers 8
```

**Deliverables for Phase 2**:
- ✅ Functional NTA parser with metadata extraction
- ✅ Size distribution statistics calculation
- ✅ Unified Parquet schema for all instruments
- ✅ Batch processing script for parallel conversion
- ✅ Comprehensive tests
- ✅ Documentation

---

## Phase 3: Data Preprocessing & Quality Control (Week 5-6)

**Priority**: HIGH  
**Duration**: 10 working days  
**Goal**: Implement data validation, normalization, and quality control checks

### 3.1 Quality Control Module (Days 21-25)

**File**: `src/preprocessing/quality_control.py`

```python
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from loguru import logger
from dataclasses import dataclass
from enum import Enum

class QCStatus(Enum):
    """Quality control status levels."""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"

@dataclass
class QCResult:
    """Quality control check result."""
    check_name: str
    status: QCStatus
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None

class QualityController:
    """Quality control checks for instrument data."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.temperature_tolerance = config.get('temperature_tolerance', 2.0)
        self.min_events_fcs = config.get('min_events_fcs', 1000)
        self.min_size_bins_nta = config.get('min_size_bins_nta', 10)
        
    def check_fcs_quality(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[QCResult]:
        """Run quality checks on FCS data."""
        results = []
        
        # Check 1: Minimum event count
        event_count = len(data)
        if event_count < self.min_events_fcs:
            results.append(QCResult(
                check_name="event_count",
                status=QCStatus.FAIL,
                message=f"Insufficient events: {event_count} < {self.min_events_fcs}",
                value=event_count,
                threshold=self.min_events_fcs
            ))
        else:
            results.append(QCResult(
                check_name="event_count",
                status=QCStatus.PASS,
                message=f"Sufficient events: {event_count}",
                value=event_count
            ))
        
        # Check 2: Flow rate stability (if available)
        if 'Time' in data.columns:
            flow_rate_stable = self._check_flow_rate_stability(data['Time'])
            results.append(flow_rate_stable)
        
        # Check 3: Signal saturation
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col.startswith(('FSC', 'SSC', 'FL')):
                saturation_check = self._check_saturation(data[col], col)
                if saturation_check.status != QCStatus.PASS:
                    results.append(saturation_check)
        
        # Check 4: Negative values in scatter channels
        if 'FSC-A' in data.columns:
            neg_fsc = (data['FSC-A'] < 0).sum()
            if neg_fsc > len(data) * 0.01:  # More than 1% negative
                results.append(QCResult(
                    check_name="negative_fsc",
                    status=QCStatus.WARNING,
                    message=f"High negative FSC values: {neg_fsc} events",
                    value=neg_fsc / len(data) * 100
                ))
        
        return results
    
    def check_nta_quality(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> List[QCResult]:
        """Run quality checks on NTA data."""
        results = []
        
        # Check 1: Temperature compliance
        if 'param_temperature' in data.columns:
            temp = data['param_temperature'].iloc[0]
            target_temp = 25.0  # Standard room temperature
            temp_diff = abs(temp - target_temp)
            
            if temp_diff > self.temperature_tolerance:
                results.append(QCResult(
                    check_name="temperature",
                    status=QCStatus.WARNING,
                    message=f"Temperature deviation: {temp:.1f}°C (target: {target_temp}°C)",
                    value=temp,
                    threshold=target_temp
                ))
            else:
                results.append(QCResult(
                    check_name="temperature",
                    status=QCStatus.PASS,
                    message=f"Temperature OK: {temp:.1f}°C",
                    value=temp
                ))
        
        # Check 2: Minimum size bins
        bin_count = len(data)
        if bin_count < self.min_size_bins_nta:
            results.append(QCResult(
                check_name="size_bins",
                status=QCStatus.FAIL,
                message=f"Insufficient size bins: {bin_count} < {self.min_size_bins_nta}",
                value=bin_count,
                threshold=self.min_size_bins_nta
            ))
        else:
            results.append(QCResult(
                check_name="size_bins",
                status=QCStatus.PASS,
                message=f"Sufficient size bins: {bin_count}",
                value=bin_count
            ))
        
        # Check 3: Size range validation (exosomes: 30-150 nm)
        if 'size_nm' in data.columns:
            min_size = data['size_nm'].min()
            max_size = data['size_nm'].max()
            
            if min_size > 150 or max_size < 30:
                results.append(QCResult(
                    check_name="size_range",
                    status=QCStatus.WARNING,
                    message=f"Unusual size range: {min_size:.1f}-{max_size:.1f} nm (expected: 30-150 nm)"
                ))
        
        # Check 4: Concentration consistency
        if 'concentration' in data.columns:
            # Check for sudden drops/spikes
            conc = data['concentration']
            conc_diff = conc.diff().abs()
            max_diff = conc_diff.max()
            mean_conc = conc.mean()
            
            if max_diff > mean_conc * 2:  # Spike > 2x mean
                results.append(QCResult(
                    check_name="concentration_stability",
                    status=QCStatus.WARNING,
                    message="Large concentration variation detected"
                ))
        
        return results
    
    def _check_flow_rate_stability(self, time_data: pd.Series) -> QCResult:
        """Check if flow rate is stable throughout acquisition."""
        time_diff = time_data.diff().dropna()
        mean_diff = time_diff.mean()
        std_diff = time_diff.std()
        
        cv = (std_diff / mean_diff) * 100  # Coefficient of variation
        
        if cv > 10:  # More than 10% variation
            return QCResult(
                check_name="flow_rate_stability",
                status=QCStatus.WARNING,
                message=f"Flow rate variability: CV={cv:.1f}%",
                value=cv,
                threshold=10.0
            )
        else:
            return QCResult(
                check_name="flow_rate_stability",
                status=QCStatus.PASS,
                message="Flow rate stable",
                value=cv
            )
    
    def _check_saturation(self, channel_data: pd.Series, channel_name: str) -> QCResult:
        """Check for signal saturation in channel."""
        max_value = channel_data.max()
        # Assume 262144 (2^18) or 1023 (2^10) as typical max
        potential_max = 262144 if max_value > 1023 else 1023
        
        saturated_events = (channel_data >= potential_max * 0.99).sum()
        saturation_pct = (saturated_events / len(channel_data)) * 100
        
        if saturation_pct > 1:  # More than 1% saturated
            return QCResult(
                check_name=f"saturation_{channel_name}",
                status=QCStatus.WARNING,
                message=f"{channel_name} saturation: {saturation_pct:.1f}% of events",
                value=saturation_pct,
                threshold=1.0
            )
        else:
            return QCResult(
                check_name=f"saturation_{channel_name}",
                status=QCStatus.PASS,
                message=f"{channel_name} not saturated",
                value=saturation_pct
            )
    
    def generate_qc_report(self, results: List[QCResult]) -> Dict[str, Any]:
        """Generate summary QC report."""
        report = {
            'total_checks': len(results),
            'passed': sum(1 for r in results if r.status == QCStatus.PASS),
            'warnings': sum(1 for r in results if r.status == QCStatus.WARNING),
            'failed': sum(1 for r in results if r.status == QCStatus.FAIL),
            'checks': [
                {
                    'name': r.check_name,
                    'status': r.status.value,
                    'message': r.message,
                    'value': r.value,
                    'threshold': r.threshold
                }
                for r in results
            ]
        }
        
        # Overall status
        if report['failed'] > 0:
            report['overall_status'] = 'fail'
        elif report['warnings'] > 0:
            report['overall_status'] = 'warning'
        else:
            report['overall_status'] = 'pass'
        
        return report
```

### 3.2 Data Normalization (Days 26-28)

**File**: `src/preprocessing/normalization.py`

```python
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from loguru import logger

class DataNormalizer:
    """Normalize data across different instruments."""
    
    @staticmethod
    def normalize_fcs_channels(
        data: pd.DataFrame,
        channels: List[str],
        method: str = 'arcsinh'
    ) -> pd.DataFrame:
        """
        Normalize FCS channel data.
        
        Args:
            data: FCS DataFrame
            channels: List of channels to normalize
            method: 'arcsinh', 'log', or 'logicle'
        """
        df = data.copy()
        
        for channel in channels:
            if channel not in df.columns:
                continue
            
            if method == 'arcsinh':
                # Inverse hyperbolic sine transformation
                df[f'{channel}_norm'] = np.arcsinh(df[channel] / 5)
            
            elif method == 'log':
                # Log transformation (add 1 to avoid log(0))
                df[f'{channel}_norm'] = np.log10(df[channel] + 1)
            
            elif method == 'logicle':
                # Logicle transformation (simplified)
                # Full implementation requires flowkit or similar
                logger.warning("Logicle transformation not fully implemented")
                df[f'{channel}_norm'] = np.arcsinh(df[channel] / 5)
        
        return df
    
    @staticmethod
    def standardize_size_units(
        data: pd.DataFrame,
        size_column: str = 'size_nm'
    ) -> pd.DataFrame:
        """Ensure size is in nanometers."""
        df = data.copy()
        
        if size_column not in df.columns:
            return df
        
        # Check if values seem to be in micrometers (μm)
        max_size = df[size_column].max()
        if max_size < 10:  # Likely in μm
            logger.info(f"Converting {size_column} from μm to nm")
            df[size_column] = df[size_column] * 1000
        
        return df
    
    @staticmethod
    def standardize_concentration_units(
        data: pd.DataFrame,
        concentration_column: str = 'concentration'
    ) -> pd.DataFrame:
        """Standardize concentration to particles/mL."""
        df = data.copy()
        
        if concentration_column not in df.columns:
            return df
        
        # Check magnitude to infer units
        median_conc = df[concentration_column].median()
        
        if median_conc < 1e6:  # Likely in particles/μL
            logger.info(f"Converting {concentration_column} from /μL to /mL")
            df[concentration_column] = df[concentration_column] * 1000
        
        return df
```

### 3.3 Size Binning (Days 29-30)

**File**: `src/preprocessing/size_binning.py`

```python
import pandas as pd
from typing import Dict, List
from loguru import logger

class SizeBinner:
    """Bin particles by size categories."""
    
    # Standard exosome size categories
    SIZE_CATEGORIES = {
        'small_exosomes': (40, 80),
        'medium_exosomes': (80, 100),
        'large_exosomes': (100, 120),
        'microvesicles': (120, 200),
        'apoptotic_bodies': (200, 1000),
    }
    
    @staticmethod
    def assign_size_categories(
        data: pd.DataFrame,
        size_column: str = 'size_nm',
        categories: Dict[str, tuple] = None
    ) -> pd.DataFrame:
        """Assign size category labels to data."""
        df = data.copy()
        
        if size_column not in df.columns:
            logger.error(f"Column {size_column} not found")
            return df
        
        if categories is None:
            categories = SizeBinner.SIZE_CATEGORIES
        
        # Create category column
        df['size_category'] = 'other'
        
        for category_name, (min_size, max_size) in categories.items():
            mask = (df[size_column] >= min_size) & (df[size_column] < max_size)
            df.loc[mask, 'size_category'] = category_name
        
        logger.info(f"Assigned size categories to {len(df)} rows")
        return df
    
    @staticmethod
    def bin_by_size_range(
        data: pd.DataFrame,
        size_column: str = 'size_nm',
        bin_width: float = 10.0
    ) -> pd.DataFrame:
        """Create uniform size bins."""
        df = data.copy()
        
        if size_column not in df.columns:
            return df
        
        min_size = df[size_column].min()
        max_size = df[size_column].max()
        
        bins = np.arange(min_size, max_size + bin_width, bin_width)
        df['size_bin'] = pd.cut(df[size_column], bins=bins, include_lowest=True)
        
        return df
```

**Deliverables for Phase 3**:
- ✅ Quality control module with configurable checks
- ✅ Data normalization for FCS and NTA
- ✅ Size binning and categorization
- ✅ QC report generation
- ✅ Unit tests

---

## Phase 4: Multi-Modal Fusion & Sample Matching (Week 7)

**Priority**: HIGH  
**Duration**: 5 working days  
**Goal**: Link data from same sample across different instruments

### 4.1 Sample Matcher (Days 31-33)

**File**: `src/fusion/sample_matcher.py`

```python
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger
from datetime import datetime, timedelta

class SampleMatcher:
    """Match samples across different instruments."""
    
    def __init__(self, parquet_dir: Path, time_tolerance_hours: int = 24):
        self.parquet_dir = parquet_dir
        self.time_tolerance = timedelta(hours=time_tolerance_hours)
    
    def find_matching_samples(self, sample_id: str) -> Dict[str, List[Path]]:
        """Find all files for a given sample ID across instruments."""
        matching_files = {
            'flow_cytometry': [],
            'nta': [],
            'tem': [],
            'western_blot': []
        }
        
        # Scan parquet directory
        for parquet_file in self.parquet_dir.glob("*.parquet"):
            # Check if sample ID is in filename
            if sample_id in parquet_file.stem:
                # Read minimal metadata to determine instrument type
                df = pd.read_parquet(parquet_file, columns=['instrument_type'])
                inst_type = df['instrument_type'].iloc[0]
                
                if inst_type in matching_files:
                    matching_files[inst_type].append(parquet_file)
        
        return matching_files
    
    def get_all_sample_ids(self) -> List[str]:
        """Get list of all unique sample IDs."""
        sample_ids = set()
        
        for parquet_file in self.parquet_dir.glob("*.parquet"):
            df = pd.read_parquet(parquet_file, columns=['sample_id'])
            sample_ids.update(df['sample_id'].unique())
        
        return sorted(list(sample_ids))
    
    def create_sample_manifest(self) -> pd.DataFrame:
        """Create manifest of all samples and available data."""
        manifest_data = []
        
        sample_ids = self.get_all_sample_ids()
        
        for sample_id in sample_ids:
            matching = self.find_matching_samples(sample_id)
            
            entry = {
                'sample_id': sample_id,
                'has_flow_cytometry': len(matching['flow_cytometry']) > 0,
                'has_nta': len(matching['nta']) > 0,
                'has_tem': len(matching['tem']) > 0,
                'has_western_blot': len(matching['western_blot']) > 0,
                'fcs_files': len(matching['flow_cytometry']),
                'nta_files': len(matching['nta']),
                'tem_files': len(matching['tem']),
                'total_files': sum(len(files) for files in matching.values())
            }
            
            manifest_data.append(entry)
        
        manifest = pd.DataFrame(manifest_data)
        logger.info(f"Created manifest for {len(manifest)} samples")
        
        return manifest
```

### 4.2 Feature Extractor (Days 34-35)

**File**: `src/fusion/feature_extractor.py`

```python
import pandas as pd
import numpy as np
from typing import Dict, Any
from loguru import logger

class FeatureExtractor:
    """Extract key features from each instrument type."""
    
    @staticmethod
    def extract_fcs_features(data: pd.DataFrame) -> Dict[str, Any]:
        """Extract features from FCS data."""
        features = {}
        
        # Get numeric channels
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        channel_cols = [col for col in numeric_cols if any(col.startswith(prefix) 
                       for prefix in ['FSC', 'SSC', 'FL'])]
        
        for channel in channel_cols:
            features[f'{channel}_median'] = float(data[channel].median())
            features[f'{channel}_mean'] = float(data[channel].mean())
            features[f'{channel}_cv'] = float(data[channel].std() / data[channel].mean())
        
        # Event count
        features['total_events'] = len(data)
        
        # Positive populations (simplified - assumes gating is done)
        # This would need actual gating logic
        
        return features
    
    @staticmethod
    def extract_nta_features(data: pd.DataFrame) -> Dict[str, Any]:
        """Extract features from NTA data."""
        features = {}
        
        if 'size_nm' in data.columns:
            if 'concentration' in data.columns:
                # Weighted statistics
                total_conc = data['concentration'].sum()
                weights = data['concentration'] / total_conc
                
                features['mean_size_nm'] = float((data['size_nm'] * weights).sum())
                
                # Mode (peak)
                mode_idx = data['concentration'].idxmax()
                features['mode_size_nm'] = float(data.loc[mode_idx, 'size_nm'])
                
                # Total concentration
                features['total_concentration'] = float(total_conc)
            else:
                features['mean_size_nm'] = float(data['size_nm'].mean())
            
            # Percentiles
            features['d10_nm'] = float(data['size_nm'].quantile(0.1))
            features['d50_nm'] = float(data['size_nm'].quantile(0.5))
            features['d90_nm'] = float(data['size_nm'].quantile(0.9))
            features['size_range_nm'] = float(data['size_nm'].max() - data['size_nm'].min())
        
        return features
    
    @staticmethod
    def create_feature_matrix(sample_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Create unified feature matrix from all instruments."""
        feature_rows = []
        
        # Extract features for each instrument
        if 'flow_cytometry' in sample_data:
            fcs_features = FeatureExtractor.extract_fcs_features(sample_data['flow_cytometry'])
            fcs_features['instrument'] = 'flow_cytometry'
            feature_rows.append(fcs_features)
        
        if 'nta' in sample_data:
            nta_features = FeatureExtractor.extract_nta_features(sample_data['nta'])
            nta_features['instrument'] = 'nta'
            feature_rows.append(nta_features)
        
        return pd.DataFrame(feature_rows)
```

**Deliverables for Phase 4**:
- ✅ Sample matching across instruments
- ✅ Sample manifest generation
- ✅ Feature extraction for FCS and NTA
- ✅ Unified feature matrix creation

---

## Phase 5: Basic Anomaly Detection (Week 8)

**Priority**: MEDIUM  
**Duration**: 5 working days  
**Goal**: Implement threshold-based anomaly detection

### 5.1 Statistical Anomaly Detector (Days 36-38)

**File**: `src/anomaly_detection/statistical_tests.py`

```python
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from scipy import stats
from loguru import logger

class StatisticalAnomalyDetector:
    """Statistical methods for anomaly detection."""
    
    def __init__(self, threshold_std: float = 3.0):
        self.threshold_std = threshold_std
    
    def detect_size_discrepancy(
        self,
        nta_size: float,
        tem_size: float,
        tolerance_pct: float = 15.0
    ) -> Dict[str, Any]:
        """Check if NTA and TEM sizes match within tolerance."""
        diff_pct = abs(nta_size - tem_size) / nta_size * 100
        
        is_anomaly = diff_pct > tolerance_pct
        
        return {
            'anomaly_type': 'size_discrepancy',
            'is_anomaly': is_anomaly,
            'nta_size_nm': nta_size,
            'tem_size_nm': tem_size,
            'difference_pct': diff_pct,
            'tolerance_pct': tolerance_pct,
            'message': f"Size difference: {diff_pct:.1f}% (NTA: {nta_size:.1f} nm, TEM: {tem_size:.1f} nm)"
        }
    
    def detect_outliers_zscore(
        self,
        data: pd.Series,
        column_name: str
    ) -> Dict[str, Any]:
        """Detect outliers using z-score method."""
        z_scores = np.abs(stats.zscore(data))
        outliers = z_scores > self.threshold_std
        outlier_indices = np.where(outliers)[0].tolist()
        
        return {
            'anomaly_type': 'outliers',
            'is_anomaly': len(outlier_indices) > 0,
            'column': column_name,
            'outlier_count': len(outlier_indices),
            'outlier_indices': outlier_indices,
            'outlier_pct': len(outlier_indices) / len(data) * 100,
            'message': f"Found {len(outlier_indices)} outliers in {column_name} ({len(outlier_indices)/len(data)*100:.1f}%)"
        }
```

### 5.2 Threshold Manager (Days 39-40)

**File**: `src/anomaly_detection/threshold_manager.py`

```python
from typing import Dict, Any
import json
from pathlib import Path

class ThresholdManager:
    """Manage anomaly detection thresholds."""
    
    DEFAULT_THRESHOLDS = {
        'size_discrepancy_pct': 15.0,
        'temperature_tolerance_c': 2.0,
        'outlier_std_threshold': 3.0,
        'min_events_fcs': 1000,
        'min_size_bins_nta': 10,
        'saturation_pct': 1.0,
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        self.thresholds = self.DEFAULT_THRESHOLDS.copy()
        
        if config_path and config_path.exists():
            self.load(config_path)
    
    def load(self, config_path: Path) -> None:
        """Load thresholds from JSON file."""
        with open(config_path, 'r') as f:
            user_thresholds = json.load(f)
        self.thresholds.update(user_thresholds)
    
    def save(self, config_path: Path) -> None:
        """Save thresholds to JSON file."""
        with open(config_path, 'w') as f:
            json.dump(self.thresholds, f, indent=2)
    
    def get(self, key: str) -> Any:
        """Get threshold value."""
        return self.thresholds.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """Set threshold value."""
        self.thresholds[key] = value
```

**Deliverables for Phase 5**:
- ✅ Statistical anomaly detection methods
- ✅ Size discrepancy checks
- ✅ Outlier detection
- ✅ Configurable thresholds
- ✅ JSON-based threshold configuration

---

## Phase 6: Minimal UI & Integration (Week 9)

**Priority**: MEDIUM  
**Duration**: 5 working days  
**Goal**: Create minimal web interface for file upload and analysis

### 6.1 FastAPI Backend (Days 41-43)

**File**: `src/api/main.py`

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import List
import shutil
from loguru import logger

from src.parsers.fcs_parser import FCSParser
from src.parsers.nta_parser import NTAParser
from src.preprocessing.quality_control import QualityController
from src.fusion.sample_matcher import SampleMatcher

app = FastAPI(title="CRMIT API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = Path("data/uploads")
PARQUET_DIR = Path("data/parquet")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PARQUET_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/")
async def root():
    return {"message": "CRMIT API v1.0.0"}

@app.post("/upload/fcs")
async def upload_fcs(file: UploadFile = File(...)):
    """Upload and process FCS file."""
    try:
        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Parse FCS file
        parser = FCSParser(file_path)
        if not parser.validate():
            raise HTTPException(status_code=400, detail="Invalid FCS file")
        
        data = parser.parse()
        metadata = parser.extract_metadata()
        
        # Save to Parquet
        parquet_path = PARQUET_DIR / f"{file_path.stem}.parquet"
        parser.to_parquet(parquet_path)
        
        # Quality control
        qc_config = {'min_events_fcs': 1000}
        qc = QualityController(qc_config)
        qc_results = qc.check_fcs_quality(data, metadata)
        qc_report = qc.generate_qc_report(qc_results)
        
        return {
            "success": True,
            "file_name": file.filename,
            "sample_id": parser.sample_id,
            "event_count": len(data),
            "channels": parser.channel_names,
            "qc_report": qc_report,
            "parquet_file": str(parquet_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to process FCS file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/nta")
async def upload_nta(file: UploadFile = File(...)):
    """Upload and process NTA file."""
    try:
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        parser = NTAParser(file_path)
        if not parser.validate():
            raise HTTPException(status_code=400, detail="Invalid NTA file")
        
        data = parser.parse()
        metadata = parser.extract_metadata()
        stats = parser.get_size_distribution_stats()
        
        parquet_path = PARQUET_DIR / f"{file_path.stem}.parquet"
        parser.to_parquet(parquet_path)
        
        return {
            "success": True,
            "file_name": file.filename,
            "sample_id": parser.sample_id,
            "size_bins": len(data),
            "size_stats": stats,
            "parquet_file": str(parquet_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to process NTA file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/samples")
async def list_samples():
    """List all processed samples."""
    matcher = SampleMatcher(PARQUET_DIR)
    manifest = matcher.create_sample_manifest()
    return manifest.to_dict(orient='records')

@app.get("/samples/{sample_id}")
async def get_sample_details(sample_id: str):
    """Get details for specific sample."""
    matcher = SampleMatcher(PARQUET_DIR)
    matching = matcher.find_matching_samples(sample_id)
    
    return {
        "sample_id": sample_id,
        "available_data": {
            "flow_cytometry": [str(f) for f in matching['flow_cytometry']],
            "nta": [str(f) for f in matching['nta']],
            "tem": [str(f) for f in matching['tem']],
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 6.2 Simple HTML Frontend (Days 44-45)

**File**: `static/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CRMIT - Upload Files</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }
        .upload-section {
            border: 2px dashed #ccc;
            padding: 30px;
            margin: 20px 0;
            border-radius: 8px;
        }
        .upload-section:hover {
            border-color: #007bff;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #0056b3;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <h1>CRMIT File Upload</h1>
    
    <div class="upload-section">
        <h2>Upload FCS File</h2>
        <input type="file" id="fcsFile" accept=".fcs">
        <button onclick="uploadFCS()">Upload & Process</button>
        <div id="fcsResult" class="result"></div>
    </div>
    
    <div class="upload-section">
        <h2>Upload NTA File</h2>
        <input type="file" id="ntaFile" accept=".txt,.csv">
        <button onclick="uploadNTA()">Upload & Process</button>
        <div id="ntaResult" class="result"></div>
    </div>
    
    <script>
        async function uploadFCS() {
            const fileInput = document.getElementById('fcsFile');
            const file = fileInput.files[0];
            if (!file) {
                alert('Please select a file');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('http://localhost:8000/upload/fcs', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                document.getElementById('fcsResult').innerHTML = `
                    <h3>Processing Complete</h3>
                    <p><strong>Sample ID:</strong> ${result.sample_id}</p>
                    <p><strong>Events:</strong> ${result.event_count}</p>
                    <p><strong>QC Status:</strong> ${result.qc_report.overall_status}</p>
                    <p><strong>Channels:</strong> ${result.channels.join(', ')}</p>
                `;
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }
        
        async function uploadNTA() {
            const fileInput = document.getElementById('ntaFile');
            const file = fileInput.files[0];
            if (!file) {
                alert('Please select a file');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('http://localhost:8000/upload/nta', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                document.getElementById('ntaResult').innerHTML = `
                    <h3>Processing Complete</h3>
                    <p><strong>Sample ID:</strong> ${result.sample_id}</p>
                    <p><strong>Size Bins:</strong> ${result.size_bins}</p>
                    <p><strong>Mean Size:</strong> ${result.size_stats.mean_size_nm.toFixed(1)} nm</p>
                    <p><strong>D50:</strong> ${result.size_stats.d50_nm.toFixed(1)} nm</p>
                `;
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }
    </script>
</body>
</html>
```

**Deliverables for Phase 6**:
- ✅ FastAPI backend with file upload endpoints
- ✅ Simple HTML frontend for testing
- ✅ Integration with parsers and QC modules
- ✅ Sample listing and details endpoints

---

## Phase 7: UI Enhancements & Gap Closure (Week 10-11)

**Priority**: HIGH  
**Duration**: 8-10 working days  
**Goal**: Address identified gaps from Requirements Analysis

**Reference**: See `docs/planning/GAP_ANALYSIS.md` for detailed gap analysis

### 7.1 FCS Best Practices Guide (Day 46 - 0.5 day)

**Files**: `apps/biovaram_streamlit/app.py`

**Implementation**:
```python
# Add to Flow Cytometry tab (mirror NTA best practices pattern)
with st.expander("📚 Flow Cytometry Best Practices", expanded=False):
    st.markdown("""
    ### 🎓 Best Practices for NanoFACS Analysis
    
    #### Sample Preparation
    - **Dilution**: 1:100 to 1:1000 for concentrated samples
    - **Temperature**: Record and maintain at 4°C or RT consistently
    - **pH**: Maintain between 7.2-7.4 for most EV samples
    
    #### Acquisition Settings
    - **FSC Threshold**: Set above noise floor (~200-500)
    - **Flow Rate**: Low (10 µL/min) for better resolution
    - **Events**: Collect minimum 10,000 events per sample
    
    #### Antibody Controls
    - **Isotype Control**: Always run matched isotype
    - **FMO Controls**: Fluorescence minus one for gating
    - **Unstained**: Reference for autofluorescence
    
    #### Quality Checks
    - **Water Wash**: Should have <100 events
    - **Blank Media**: Background characterization
    - **Reference Beads**: For daily calibration
    """)
```

**Deliverable**: FCS Best Practices panel in Flow Cytometry tab

### 7.2 Anomaly Detection UI (Days 46-47 - 1.5 days)

**Files**: 
- `src/visualization/anomaly_detection.py` (existing)
- `apps/biovaram_streamlit/app.py` (update)

**Implementation**:
```python
# Add toggle in visualization section
detect_anomalies = st.checkbox("🔍 Detect Anomalies", value=False)

if detect_anomalies:
    from src.visualization.anomaly_detection import AnomalyDetector
    detector = AnomalyDetector()
    anomaly_mask = detector.detect_anomalies(data, method='isolation_forest')
    
    # Highlight anomalies in plot
    fig.add_trace(go.Scatter(
        x=data.loc[anomaly_mask, x_col],
        y=data.loc[anomaly_mask, y_col],
        mode='markers',
        marker=dict(color='red', size=10, symbol='x'),
        name='Anomalies'
    ))
    
    st.info(f"Detected {anomaly_mask.sum()} anomalies ({anomaly_mask.mean()*100:.1f}%)")
```

**Deliverable**: Anomaly detection toggle with visual highlighting

### 7.3 Interactive Plotly Graphs (Days 47-50 - 3 days)

**Files**: 
- `src/visualization/interactive_plots.py` (new)
- `apps/biovaram_streamlit/app.py` (update)

**Implementation**:
```python
# src/visualization/interactive_plots.py

import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, List
import pandas as pd

def create_interactive_scatter(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: Optional[str] = None,
    title: str = "Scatter Plot"
) -> go.Figure:
    """Create interactive scatter plot with hover details."""
    
    fig = px.scatter(
        data,
        x=x_col,
        y=y_col,
        color=color_col,
        title=title,
        hover_data=data.columns.tolist()[:5]  # Show first 5 columns on hover
    )
    
    fig.update_layout(
        hovermode='closest',
        dragmode='zoom',  # Enable zoom by default
        xaxis=dict(title=x_col),
        yaxis=dict(title=y_col)
    )
    
    # Add modebar for export options
    fig.update_layout(
        modebar_add=['drawline', 'drawrect', 'eraseshape']
    )
    
    return fig

def create_interactive_histogram(
    data: pd.DataFrame,
    col: str,
    nbins: int = 50,
    title: str = "Distribution"
) -> go.Figure:
    """Create interactive histogram with dynamic binning."""
    
    fig = px.histogram(
        data,
        x=col,
        nbins=nbins,
        title=title
    )
    
    fig.update_layout(
        bargap=0.1,
        hovermode='x unified'
    )
    
    return fig

def create_size_distribution_overlay(
    fcs_sizes: pd.Series,
    nta_sizes: pd.Series,
    title: str = "Size Distribution Comparison"
) -> go.Figure:
    """Create overlay of FCS and NTA size distributions."""
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=fcs_sizes,
        name='NanoFACS',
        opacity=0.7,
        marker_color='blue'
    ))
    
    fig.add_trace(go.Histogram(
        x=nta_sizes,
        name='NTA',
        opacity=0.7,
        marker_color='green'
    ))

---

## Phase 8: Critical Calculation Fixes (December 5-6, 2025)

**Priority**: 🔴 CRITICAL  
**Duration**: 2 days  
**Goal**: Fix production bugs affecting data accuracy  
**Meeting Reference**: December 5, 2025 Technical Review with Parvesh

### Background
December 5 meeting with Parvesh revealed critical bugs in production:
- Size distribution histograms showing artificial spikes at 40nm and 180nm
- Median calculations skewed by clamped outlier values
- SSC channel selection needs explicit row-wise max logic

### 8.1 Size Range Calculation Fix (HIGH PRIORITY - 0.5 days)

**Problem**: Values outside 40-180nm range are being clamped to boundary values, causing:
- Artificial histogram spikes at 40nm and 180nm boundaries
- Skewed median and percentile calculations
- Inaccurate particle size distributions

**Current Logic** (INCORRECT):
```python
# In app.py, lines ~2900-3100 (diameter calculation)
# Values <40nm → set to 40nm (creates histogram spike)
# Values >180nm → set to 180nm (creates histogram spike)
diameters = np.clip(calculated_diameters, 40, 180)
```

**Required Fix**:
```python
# Step 1: Extend search range
SEARCH_MIN = 30  # nm
SEARCH_MAX = 220  # nm

# Step 2: Calculate diameters with extended range
diameters_raw = calculate_diameter_mie_theory(ssc_data, range=(SEARCH_MIN, SEARCH_MAX))

# Step 3: FILTER (don't clamp) - exclude outliers completely
mask_valid = (diameters_raw > SEARCH_MIN) & (diameters_raw < SEARCH_MAX)
diameters_filtered = diameters_raw[mask_valid]

# Step 4: Calculate statistics ONLY on filtered data
median_size = np.median(diameters_filtered)  # NOT including clamped values
d10 = np.percentile(diameters_filtered, 10)
d50 = np.percentile(diameters_filtered, 50)
d90 = np.percentile(diameters_filtered, 90)

# Step 5: Display range for visualization (subset of filtered data)
DISPLAY_MIN = 40  # nm
DISPLAY_MAX = 200  # nm
display_mask = (diameters_filtered >= DISPLAY_MIN) & (diameters_filtered <= DISPLAY_MAX)
diameters_display = diameters_filtered[display_mask]
```

**Files to Modify**:
- `apps/biovaram_streamlit/app.py` (lines ~2900-3100, diameter calculation section)
- `apps/biovaram_streamlit/app.py` (lines ~4150-4250, statistics calculation)

**Testing Required**:
- Load sample FCS file with known outliers
- Verify histogram no longer shows spikes at 40nm/180nm
- Confirm median value changes appropriately
- Validate D10/D50/D90 percentiles shift

**Deliverable**: Size range fix with no histogram artifacts

---

### 8.2 VSSC Max Column Logic (HIGH PRIORITY - 0.5 days)

**Problem**: SSC channel selection using column-level median is not explicit enough. Need row-by-row maximum selection.

**Current Logic** (WORKS BUT NOT EXPLICIT):
```python
# Selecting channel based on median comparison
vssc1_median = df['VSSC-1-H'].median()
vssc2_median = df['VSSC-2-H'].median()
selected_channel = 'VSSC-1-H' if vssc1_median > vssc2_median else 'VSSC-2-H'
```

**Required Implementation**:
```python
# Create new column with row-wise maximum
df['VSSC_max'] = df[['VSSC-1-H', 'VSSC-2-H']].max(axis=1)

# Use VSSC_max for all size calculations
ssc_data = df['VSSC_max'].values

# Update UI to show VSSC_max in column selection dropdown
column_options = ['VSSC_max', 'VSSC-1-H', 'VSSC-2-H', 'FSC-A', ...]
```

**Benefits**:
- More explicit logic (easier to understand and debug)
- Per-event optimization (not per-column)
- Matches user's mental model better
- Transparent in data export

**Files to Modify**:
- `apps/biovaram_streamlit/app.py` (lines ~2400-2450, SSC column selection)
- `apps/biovaram_streamlit/app.py` (lines ~1850-1900, column dropdown UI)

**Testing Required**:
- Verify VSSC_max column appears in dropdown
- Confirm VSSC_max values = max(VSSC-1-H, VSSC-2-H) for each row
- Validate size calculations produce same/better results

**Deliverable**: VSSC_max column implementation with UI integration

---

### 8.3 Size Range Filter Sync (MEDIUM PRIORITY - 0.5 days)

**Problem**: Custom size range sidebar controls don't update the diameter search range dynamically.

**Required Implementation**:
```python
# In sidebar: User selects custom ranges
min_size = st.number_input("Min Size (nm)", value=40, min_value=30, max_value=100)
max_size = st.number_input("Max Size (nm)", value=200, min_value=100, max_value=220)

# Automatically update search range (slightly wider than display)
SEARCH_MIN = max(30, min_size - 10)
SEARCH_MAX = min(220, max_size + 20)

# Preset buttons should also update search range
if st.button("Standard EV (30-200nm)"):
    min_size = 40
    max_size = 200
    SEARCH_MIN = 30
    SEARCH_MAX = 220
    
if st.button("Exosome-Focused (30-150nm)"):
    min_size = 40
    max_size = 150
    SEARCH_MIN = 30
    SEARCH_MAX = 170
```

**Files to Modify**:
- `apps/biovaram_streamlit/app.py` (lines ~800-850, size range sidebar)

**Deliverable**: Synced size range controls

---

### 8.4 Light Mode Theme (LOW PRIORITY - 0.5 days)

**Problem**: Current UI only has dark theme. Some users prefer light mode.

**Required Implementation**:
```python
# In app header
theme_mode = st.toggle("☀️ Light Mode", value=False)

if theme_mode:
    # Light theme colors
    st.markdown("""
    <style>
    .stApp {
        background-color: #ffffff;
        color: #1a1a1a;
    }
    .stMetric {
        background-color: #f0f0f0;
    }
    </style>
    """, unsafe_allow_html=True)
else:
    # Keep existing dark theme
    pass
```

**Files to Modify**:
- `apps/biovaram_streamlit/app.py` (lines ~200-250, theme configuration)

**Deliverable**: Light/dark theme toggle

---

### 8.5 React Migration Consideration (LOW PRIORITY - FUTURE)

**Discussion**: Parvesh approved React migration if Streamlit state management becomes blocking issue.

**Action Items**:
1. Use existing `V0_DEV_UI_PROMPT.txt` for React prototype
2. Create proof-of-concept with v0.dev
3. Demo to Parvesh for approval
4. Migrate if approved

**Status**: ⏳ DEFERRED - Fix critical bugs first, then reassess

---

## Phase 8 Testing Checklist

**Size Range Fix**:
- [ ] Load FCS file with particles <30nm
- [ ] Load FCS file with particles >220nm
- [ ] Verify no histogram spikes at 40nm
- [ ] Verify no histogram spikes at 180nm
- [ ] Confirm median calculation excludes outliers
- [ ] Validate D10/D50/D90 percentiles shift appropriately

**VSSC_max Column**:
- [ ] VSSC_max appears in column dropdown
- [ ] VSSC_max values = max(VSSC-1-H, VSSC-2-H) for random rows
- [ ] Size calculations produce reasonable results
- [ ] Export data includes VSSC_max column

**Size Range Sync**:
- [ ] Custom range inputs update diameter search range
- [ ] Preset buttons update both display and search ranges
- [ ] Edge cases handled (min > max, etc.)

**Light Mode**:
- [ ] Toggle switches between light and dark themes
- [ ] All UI elements readable in both modes
- [ ] Charts adapt colors appropriately

---

## Phase 8 Estimated Effort

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Size Range Fix | 🔴 CRITICAL | 0.5 days | None |
| VSSC_max Column | 🔴 CRITICAL | 0.5 days | None |
| Range Sync | 🟡 MEDIUM | 0.5 days | Size Range Fix |
| Light Mode | 🟢 LOW | 0.5 days | None |

**Total**: 2 days (can parallelize size fix + VSSC column)

**Target Completion**: December 6, 2025
    
    fig.update_layout(
        barmode='overlay',
        title=title,
        xaxis_title='Particle Size (nm)',
        yaxis_title='Count',
        hovermode='x unified'
    )
    
    return fig
```

**Deliverables**:
- Interactive scatter plots with hover
- Interactive histograms with dynamic binning
- Overlay comparison plots
- Export to PNG/SVG/PDF

### 7.4 Cross-Instrument Comparison View (Days 50-52 - 2 days)

**Files**: `apps/biovaram_streamlit/app.py`

**Implementation**:
```python
# New tab: Comparison
with tab_comparison:
    st.header("🔬 Cross-Instrument Comparison")
    
    # Get matched samples from fusion module
    from src.fusion.sample_matcher import SampleMatcher
    matcher = SampleMatcher()
    matched_samples = matcher.get_matched_samples()
    
    if matched_samples:
        sample_id = st.selectbox("Select Sample", matched_samples)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("NanoFACS (Flow Cytometry)")
            fcs_data = load_fcs_for_sample(sample_id)
            st.plotly_chart(create_size_histogram(fcs_data))
            
            st.metric("Mean Size", f"{fcs_data['size'].mean():.1f} nm")
            st.metric("Events", len(fcs_data))
        
        with col2:
            st.subheader("NTA (ZetaView)")
            nta_data = load_nta_for_sample(sample_id)
            st.plotly_chart(create_size_histogram(nta_data))
            
            st.metric("Mean Size", f"{nta_data['size'].mean():.1f} nm")
            st.metric("Concentration", f"{nta_data['concentration'].mean():.1e}")
        
        # Overlay comparison
        st.subheader("📊 Overlay Comparison")
        overlay_fig = create_size_distribution_overlay(
            fcs_data['size'],
            nta_data['size']
        )
        st.plotly_chart(overlay_fig, use_container_width=True)
        
        # Discrepancy analysis
        size_diff_pct = abs(fcs_data['size'].mean() - nta_data['size'].mean()) / nta_data['size'].mean() * 100
        if size_diff_pct > 15:
            st.warning(f"⚠️ Size discrepancy: {size_diff_pct:.1f}% difference")
        else:
            st.success(f"✅ Size agreement: {size_diff_pct:.1f}% difference")
    else:
        st.info("No matched samples found. Upload both FCS and NTA data for the same samples.")
```

**Deliverables**:
- Side-by-side FCS/NTA comparison
- Overlay size distribution
- Discrepancy highlighting
- Statistical comparison

### 7.5 NTA Parameter Corrections (Days 52-54 - 2 days)

**Files**: 
- `src/preprocessing/nta_corrections.py` (new)
- `apps/biovaram_streamlit/app.py` (update)

**Implementation**:
```python
# src/preprocessing/nta_corrections.py

import numpy as np
from scipy.constants import Boltzmann

def calculate_water_viscosity(temp_celsius: float) -> float:
    """
    Calculate water viscosity at given temperature using empirical formula.
    
    Uses Vogel-Fulcher-Tammann equation.
    Returns viscosity in Pa·s.
    """
    A = 2.414e-5  # Pa·s
    B = 247.8     # K
    C = 140       # K
    
    temp_kelvin = temp_celsius + 273.15
    viscosity = A * 10**(B / (temp_kelvin - C))
    
    return viscosity

def correct_nta_size(
    raw_size_nm: float,
    measurement_temp_c: float,
    reference_temp_c: float = 25.0,
    viscosity_pa_s: float = None
) -> float:
    """
    Apply Stokes-Einstein correction to NTA size measurements.
    
    The diffusion coefficient D = kT / (3πηd)
    
    When temperature differs from reference, particle sizes need correction.
    """
    if viscosity_pa_s is None:
        viscosity_meas = calculate_water_viscosity(measurement_temp_c)
        viscosity_ref = calculate_water_viscosity(reference_temp_c)
    else:
        viscosity_meas = viscosity_pa_s
        viscosity_ref = calculate_water_viscosity(reference_temp_c)
    
    # Temperature in Kelvin
    T_meas = measurement_temp_c + 273.15
    T_ref = reference_temp_c + 273.15
    
    # Correction factor: d_corrected = d_measured * (η_ref/η_meas) * (T_meas/T_ref)
    correction = (viscosity_ref / viscosity_meas) * (T_meas / T_ref)
    
    return raw_size_nm * correction

def batch_correct_sizes(
    sizes: np.ndarray,
    temp_c: float,
    reference_temp_c: float = 25.0
) -> np.ndarray:
    """Batch correction for array of sizes."""
    correction = get_correction_factor(temp_c, reference_temp_c)
    return sizes * correction

def get_correction_factor(temp_c: float, reference_temp_c: float = 25.0) -> float:
    """Get the correction factor for a given temperature."""
    viscosity_meas = calculate_water_viscosity(temp_c)
    viscosity_ref = calculate_water_viscosity(reference_temp_c)
    
    T_meas = temp_c + 273.15
    T_ref = reference_temp_c + 273.15
    
    return (viscosity_ref / viscosity_meas) * (T_meas / T_ref)
```

**Deliverables**:
- Temperature-viscosity correction
- Stokes-Einstein size adjustment
- UI toggle for corrected vs raw values

### 7.6 Persistent Chat History (Day 54-55 - 1 day)

**Files**: 
- `src/database/models.py` (update)
- `apps/biovaram_streamlit/app.py` (update)

**Implementation**:
```python
# Add to src/database/models.py

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    user_id = Column(String, index=True, nullable=True)
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ChatHistory {self.id}: {self.role}>"

# Add to app.py
def save_chat_message(session_id: str, role: str, content: str):
    """Persist chat message to database."""
    msg = ChatHistory(session_id=session_id, role=role, content=content)
    db.add(msg)
    db.commit()

def load_chat_history(session_id: str) -> List[Dict]:
    """Load chat history from database."""
    messages = db.query(ChatHistory).filter_by(
        session_id=session_id
    ).order_by(ChatHistory.created_at).all()
    
    return [{"role": m.role, "content": m.content} for m in messages]
```

**Deliverables**:
- ChatHistory database model
- Session-based message persistence
- Cross-session retrieval

### Phase 7 Summary

| Task | Days | Status | Priority |
|------|------|--------|----------|
| 7.1 FCS Best Practices | 0.5 | ❌ TODO | HIGH |
| 7.2 Anomaly Detection UI | 1.5 | ❌ TODO | MEDIUM |
| 7.3 Interactive Plotly | 3 | ❌ TODO | HIGH |
| 7.4 Cross-Instrument Compare | 2 | ❌ TODO | HIGH |
| 7.5 NTA Corrections | 2 | ❌ TODO | MEDIUM |
| 7.6 Persistent Chat | 1 | ❌ TODO | LOW |

**Total**: 10 working days

---

## Testing Strategy

### Unit Tests
- Test each parser independently
- Test preprocessing modules
- Test quality control checks
- Target: >85% code coverage

### Integration Tests
- End-to-end file processing
- Multi-sample matching
- API endpoint testing

### Performance Tests
- Large FCS files (>1M events)
- Batch processing speed
- Parquet file size comparison

---

## Documentation Requirements

1. **API Documentation** (auto-generated by FastAPI)
2. **Parser Usage Guide** (Markdown)
3. **Configuration Guide** (JSON schemas)
4. **Troubleshooting Guide**
5. **Code Comments** (inline docstrings)

---

## Deployment Checklist

- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Code reviewed
- [ ] Documentation complete
- [ ] Environment variables configured
- [ ] Database schema created
- [ ] Sample data tested
- [ ] Client demo prepared

---

## Post-Deadline Roadmap (Post-January 15)

### Phase 7: TEM Image Analysis (Future)
- Computer vision for scale bar detection
- Particle segmentation
- Size measurement from images

### Phase 8: Advanced Anomaly Detection (Future)
- Machine learning models
- Historical baseline learning
- Pattern recognition

### Phase 9: Visualization Dashboard (Future)
- Interactive plots
- Scatter plot generation
- Multi-sample comparisons

### Phase 10: Production Deployment (Future)
- Docker containerization
- Cloud deployment
- Monitoring and logging

---

## Success Criteria (Mid-January 2026)

✅ **Must Have (Priority 1)**:
- FCS files parse correctly and convert to Parquet
- NTA files parse correctly and convert to Parquet
- Files uploaded via UI
- Basic quality control checks run
- Sample ID matching works
- Parquet files generated with metadata

✅ **Should Have (Priority 2)**:
- Data normalization
- Size binning
- Basic anomaly detection (size discrepancy)
- Sample manifest generation

⭕ **Nice to Have (Priority 3)**:
- Batch processing optimization
- Advanced QC checks
- Detailed UI dashboard

---

## Risk Mitigation

### Risk 1: Unknown FCS File Format Variations
**Mitigation**: Test with all Bio Varam sample files early (Week 1)

### Risk 2: NTA Text File Format Inconsistencies
**Mitigation**: Document all format variations, create flexible parser

### Risk 3: Performance Issues with Large Files
**Mitigation**: Implement chunked reading, parallel processing

### Risk 4: Timeline Slippage
**Mitigation**: 3-4 day buffer, prioritize must-haves first

---

## Daily Standup Questions

1. What did you complete yesterday?
2. What will you work on today?
3. Any blockers?
4. Are we on track for the weekly milestone?

---

## Communication Protocol

- **Daily**: Commit code with descriptive messages
- **Weekly**: Progress report to Bio Varam (Fridays)
- **Blockers**: Immediate Slack/email notification
- **Code Reviews**: Submit PR at end of each phase

---

## Tools & Resources

- **Version Control**: Git + GitHub
- **IDE**: VS Code / PyCharm
- **Testing**: pytest
- **Documentation**: Markdown + Sphinx (optional)
- **API Testing**: Postman / Thunder Client
- **Database**: PostgreSQL + PgAdmin

---

## Conclusion

This development plan prioritizes **backend data processing infrastructure** with a focus on:

1. **Robust FCS and NTA parsing** with validation
2. **Parquet-based storage** for efficiency and scalability
3. **Quality control** to ensure data integrity
4. **Multi-modal fusion** for sample matching
5. **Minimal UI** for testing and client demo

By mid-January 2026, you will have a functional backend that can ingest FCS and NTA files, perform quality checks, convert to Parquet, and match samples across instruments—ready for the next phases of TEM analysis, advanced ML, and production deployment.

**Total Working Days**: 45 days (9 weeks)  
**Buffer**: 3-4 days for unexpected issues  
**Client Demo**: January 10-12, 2026  
**Final Delivery**: January 15, 2026
