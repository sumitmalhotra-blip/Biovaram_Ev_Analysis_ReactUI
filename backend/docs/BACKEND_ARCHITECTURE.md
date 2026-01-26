# Backend Architecture Documentation

**BioVaram EV Analysis Platform - Python Backend**

*Last Updated: January 2026*

---

## 📁 Directory Structure

```
backend/
├── run_api.py                 # Entry point for FastAPI server
├── requirements.txt           # Python dependencies
├── alembic.ini               # Database migrations config
│
├── src/                       # Core source code (20+ modules)
│   ├── api/                  # REST API layer
│   ├── parsers/              # File parsing
│   ├── physics/              # Scientific calculations
│   ├── visualization/        # Plot generation
│   ├── database/             # Database models
│   ├── preprocessing/        # Data cleaning
│   ├── analysis/             # Analysis pipelines
│   ├── fusion/               # Data fusion
│   ├── utils/                # Utilities
│   └── fcs_calibration.py    # SSC calibration module
│
├── scripts/                   # Standalone scripts (50+)
├── data/                      # Data storage
├── figures/                   # Generated plots
├── docs/                      # Documentation
├── tests/                     # Unit tests
├── nanoFACS/                  # Sample FCS data
├── NTA/                       # Sample NTA data
└── Literature/                # Reference papers
```

---

## 🔧 Core Modules

### 1. API Layer (`src/api/`)

```
src/api/
├── main.py           # FastAPI app initialization
├── config.py         # Settings management
└── routers/          # API endpoints
    ├── upload.py     # POST /upload/fcs, /upload/nta
    ├── samples.py    # GET/POST/DELETE /samples
    ├── results.py    # GET /results/{sample_id}
    ├── auth.py       # Authentication endpoints
    └── jobs.py       # Background job management
```

**Key File: `main.py`**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BioVaram EV Analysis API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(upload.router, prefix="/api/v1")
app.include_router(samples.router, prefix="/api/v1")
```

**API Endpoints Summary:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/upload/fcs` | POST | Upload FCS file |
| `/api/v1/upload/nta` | POST | Upload NTA file |
| `/api/v1/samples` | GET | List all samples |
| `/api/v1/samples/{id}` | GET | Get sample details |
| `/api/v1/samples/{id}/results` | GET | Get analysis results |
| `/api/v1/auth/login` | POST | User login |
| `/api/v1/auth/register` | POST | User registration |

---

### 2. Parsers (`src/parsers/`)

```
src/parsers/
├── base_parser.py      # Abstract base class
├── fcs_parser.py       # FCS file parsing (CRITICAL)
├── nta_parser.py       # NTA text file parsing
├── nta_pdf_parser.py   # NTA PDF parsing
└── parquet_writer.py   # Parquet output
```

#### FCS Parser (`fcs_parser.py`)

Parses Flow Cytometry Standard files (`.fcs`).

**Key Features:**
- Supports FCS 2.0, 3.0, 3.1 formats
- Extracts all channel data (FSC, SSC, fluorescence)
- Reads embedded metadata (acquisition date, cytometer, etc.)
- Memory-efficient chunked processing for large files

**Usage:**
```python
from src.parsers.fcs_parser import FCSParser
from pathlib import Path

# Parse FCS file
parser = FCSParser(Path("data/uploads/sample.fcs"))
parser.validate()  # Check file format
data = parser.parse()  # Returns pandas DataFrame

# Access data
print(f"Events: {len(data)}")
print(f"Channels: {data.columns.tolist()}")
print(data['SSC-H'].describe())
```

**Output DataFrame Structure:**
| Column | Type | Description |
|--------|------|-------------|
| FSC-H | float64 | Forward scatter height |
| FSC-A | float64 | Forward scatter area |
| SSC-H | float64 | Side scatter height |
| SSC-A | float64 | Side scatter area |
| FL1-H | float64 | Fluorescence channel 1 |
| ... | ... | Additional channels |

#### NTA Parser (`nta_parser.py`)

Parses ZetaView NTA text files.

**Key Features:**
- Parses size distribution data
- Extracts concentration measurements
- Handles 11-position uniformity files
- Reads zeta potential profiles

**Usage:**
```python
from src.parsers.nta_parser import NTAParser

parser = NTAParser(Path("data/uploads/sample_size_1.txt"))
data = parser.parse()  # Returns DataFrame

# Access statistics
stats = parser.calculate_statistics()
print(f"D50: {stats['d50']} nm")
```

---

### 3. Physics Module (`src/physics/`)

```
src/physics/
├── mie_scatter.py       # Mie scattering theory (CORE)
├── size_distribution.py # Per-event sizing
├── bead_calibration.py  # Bead-based calibration
├── size_config.py       # Size range configuration
├── statistics_utils.py  # Statistical utilities
└── nta_corrections.py   # NTA-specific corrections
```

#### Mie Scattering (`mie_scatter.py`)

Implements Mie theory for particle sizing.

**The Physics:**
When light hits a small particle, it scatters. The amount of scattering depends on:
- Particle size (diameter)
- Particle refractive index
- Medium refractive index
- Light wavelength

**Key Class: `MieScatterCalculator`**
```python
from src.physics.mie_scatter import MieScatterCalculator

# Initialize for 488nm laser, EVs in PBS
calc = MieScatterCalculator(
    wavelength_nm=488.0,      # Laser wavelength
    n_particle=1.40,          # EV refractive index
    n_medium=1.33             # PBS refractive index
)

# Forward calculation: diameter → scatter
result = calc.calculate_scattering_efficiency(diameter_nm=100)
print(f"Q_sca: {result.Q_sca}")
print(f"FSC proxy: {result.forward_scatter}")

# Inverse calculation: scatter → diameter
diameter, success = calc.diameter_from_scatter(
    fsc_intensity=15000,
    min_diameter=30,
    max_diameter=300
)
print(f"Estimated size: {diameter} nm")
```

**Key Concepts:**

| Parameter | Symbol | Typical Value | Description |
|-----------|--------|---------------|-------------|
| Size parameter | x | 0.1 - 3 | π × diameter / wavelength |
| Refractive index (particle) | n_p | 1.37-1.45 | EV refractive index |
| Refractive index (medium) | n_m | 1.33 | PBS/water |
| Q_sca | - | 0-4 | Scattering efficiency |
| Asymmetry (g) | g | -1 to 1 | Forward scatter bias |

#### Multi-Solution Problem

**IMPORTANT:** The Mie scattering curve is NOT monotonic. One scatter value can correspond to multiple particle sizes.

```
SSC = 5000 could mean:
├── 65 nm  (Solution 1)
├── 128 nm (Solution 2)
└── 215 nm (Solution 3)
```

We use wavelength ratio (VSSC/BSSC) to disambiguate:
- Small particles: High ratio (violet scatters more)
- Large particles: Low ratio (similar scattering)

See `scripts/compare_single_vs_multi_solution.py` for comparison.

#### Size Distribution (`size_distribution.py`)

Calculates sizes for all events in a sample.

```python
from src.physics.size_distribution import PerEventSizeAnalyzer

analyzer = PerEventSizeAnalyzer(
    wavelength_nm=488.0,
    n_particle=1.40,
    size_range_nm=(30, 500)
)

# Analyze sample
result = analyzer.analyze_sample(fsc_values, "PC3_Exo")

print(f"D50: {result.statistics['d50']:.1f} nm")
print(f"D10: {result.statistics['d10']:.1f} nm")
print(f"D90: {result.statistics['d90']:.1f} nm")
```

---

### 4. SSC Calibration (`src/fcs_calibration.py`)

Empirical calibration from SSC to particle size using known standards.

**Calibration Formula:**
```
size_nm = 10^(b + a × log10(SSC))

Where:
  a = 0.1960 (slope)
  b = 1.3537 (intercept)
```

**Usage:**
```python
from src.fcs_calibration import SSCCalibration

# Load calibration
cal = SSCCalibration.from_file("config/calibration.json")

# Convert SSC to size
sizes = cal.ssc_to_size(ssc_values)
```

---

### 5. Visualization (`src/visualization/`)

```
src/visualization/
├── fcs_plots.py          # FCS scatter/histogram plots
├── nta_plots.py          # NTA distribution plots
├── size_intensity_plots.py # Size vs intensity
├── cross_comparison.py   # FCS vs NTA comparison
├── anomaly_detection.py  # Outlier visualization
├── auto_axis_selector.py # Smart axis scaling
└── interactive_plots.py  # Plotly interactive
```

**Key Function: Generate Size Distribution Plot**
```python
from src.visualization.fcs_plots import FCSPlotter

plotter = FCSPlotter()
fig = plotter.plot_size_distribution(
    sizes=size_array,
    sample_name="PC3 EXO1",
    bins=50
)
fig.savefig("figures/size_dist.png", dpi=150)
```

---

### 6. Database (`src/database/`)

```
src/database/
├── models.py       # SQLAlchemy ORM models
├── connection.py   # Database connection
└── crud.py         # CRUD operations
```

**Models:**
```python
class Sample(Base):
    __tablename__ = "samples"
    
    id = Column(UUID, primary_key=True)
    filename = Column(String, nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"))
    sample_type = Column(String)  # 'fcs' or 'nta'
    upload_date = Column(DateTime)
    event_count = Column(Integer)
    
class FCSResult(Base):
    __tablename__ = "fcs_results"
    
    id = Column(UUID, primary_key=True)
    sample_id = Column(UUID, ForeignKey("samples.id"))
    d10 = Column(Float)
    d50 = Column(Float)
    d90 = Column(Float)
    mean_size = Column(Float)
```

---

## 📜 Scripts Directory

The `scripts/` folder contains standalone scripts for:

### Batch Processing
| Script | Purpose |
|--------|---------|
| `batch_process_fcs.py` | Convert multiple FCS files to Parquet |
| `batch_process_nta.py` | Convert multiple NTA files to Parquet |
| `reprocess_with_smart_filtering.py` | Add outlier filtering to existing data |

### Analysis
| Script | Purpose |
|--------|---------|
| `compare_single_vs_multi_solution.py` | Compare Mie solution methods |
| `cross_validate_nta_fcs.py` | Validate FCS vs NTA results |
| `analyze_outliers.py` | Analyze outlier characteristics |

### Visualization
| Script | Purpose |
|--------|---------|
| `generate_fcs_plots.py` | Generate FCS visualization suite |
| `generate_nta_plots.py` | Generate NTA visualizations |
| `batch_visualize_all_fcs.py` | Batch generate all plots |

### Utilities
| Script | Purpose |
|--------|---------|
| `parse_fcs.py` | CLI tool to inspect FCS files |
| `check_parquet.py` | Verify Parquet file integrity |
| `delete_user_data.py` | Remove user data from DB |

---

## 🔌 Key Dependencies

```
# Core Framework
fastapi>=0.109.0        # REST API framework
uvicorn>=0.27.0         # ASGI server
pydantic>=2.6.0         # Data validation

# Data Processing
pandas>=2.2.0           # DataFrames
numpy>=1.26.0           # Numerical computing
pyarrow>=15.0.0         # Parquet support
scipy>=1.12.0           # Scientific computing

# File Parsing
flowio>=1.3.0           # FCS file parsing

# Physics
miepython>=3.0.0        # Mie scattering calculations

# Database
sqlalchemy>=2.0.0       # ORM
asyncpg>=0.29.0         # Async PostgreSQL
alembic>=1.13.0         # Migrations

# Visualization
matplotlib>=3.8.0       # Static plots
plotly>=5.18.0          # Interactive plots
```

---

## 🏃 Running the Backend

### Development
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python run_api.py
# Runs on http://localhost:8000
```

### Production
```powershell
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Running Scripts
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python scripts/batch_process_fcs.py
```

---

## 🧪 Testing

```powershell
cd backend
pytest tests/ -v
```

---

## 📊 Data Flow

```
1. File Upload
   ├── Frontend sends file to /api/v1/upload/fcs
   ├── Save to data/uploads/
   └── Create sample record in DB

2. Parsing
   ├── FCSParser reads .fcs file
   ├── Extract channels (FSC, SSC, FL*)
   └── Return DataFrame

3. Size Calculation
   ├── Get SSC values from DataFrame
   ├── Apply Mie theory or calibration
   └── Calculate D10/D50/D90

4. Storage
   ├── Save processed data to Parquet
   ├── Store results in database
   └── Generate visualization

5. Response
   ├── Return results JSON to frontend
   └── Include statistics and histogram data
```

---

*For API endpoint details, see `API_REFERENCE.md`*
