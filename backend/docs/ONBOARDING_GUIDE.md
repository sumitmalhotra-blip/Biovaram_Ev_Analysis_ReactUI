# 🎓 Backend Onboarding Guide for New Developers

> **Welcome to the CRMIT EV Analysis Platform!**  
> This guide is designed to help you understand the backend codebase from scratch.  
> Follow this document step-by-step, and you'll have a solid understanding of how everything works.

---

## 📋 Table of Contents

1. [First Things First - Understanding the Project](#1-first-things-first---understanding-the-project)
2. [The Big Picture - System Architecture](#2-the-big-picture---system-architecture)
3. [Your Learning Path - Where to Start](#3-your-learning-path---where-to-start)
4. [Directory Map - What's Where](#4-directory-map---whats-where)
5. [Following a Request - End-to-End Flow](#5-following-a-request---end-to-end-flow)
6. [Core Modules Deep Dive](#6-core-modules-deep-dive)
7. [The Science Behind It - Mie Theory Explained](#7-the-science-behind-it---mie-theory-explained)
8. [Database Structure](#8-database-structure)
9. [Common Code Patterns](#9-common-code-patterns)
10. [Cheat Sheet - Quick Reference](#10-cheat-sheet---quick-reference)

---

## 1. First Things First - Understanding the Project

### What Does This Platform Do?

This is a **scientific analysis platform** for studying **Extracellular Vesicles (EVs)** - tiny particles released by cells. The platform:

1. **Reads scientific data files** (FCS from flow cytometry, NTA from nanoparticle tracking)
2. **Calculates particle sizes** using physics (Mie scattering theory)
3. **Visualizes results** with charts and statistics
4. **Detects anomalies** in the data
5. **Stores everything** in a database for later analysis

### Key Terms You'll See Everywhere

| Term | What It Means |
|------|---------------|
| **EV** | Extracellular Vesicle - tiny particles (30-500nm) from cells |
| **FCS** | Flow Cytometry Standard - file format for flow cytometry data |
| **NTA** | Nanoparticle Tracking Analysis - another measurement technique |
| **FSC** | Forward Scatter - light scattered forward, relates to particle SIZE |
| **SSC** | Side Scatter - light scattered to the side, relates to particle COMPLEXITY |
| **Mie Theory** | Physics that explains how light scatters off spherical particles |

### How to Run the Backend

```bash
# 1. Navigate to backend folder
cd backend

# 2. Activate virtual environment (Windows)
.\venv\Scripts\Activate.ps1

# 3. Start the server
python run_api.py

# 4. Open in browser
# API: http://localhost:8000
# Docs: http://localhost:8000/docs (Interactive Swagger UI!)
```

---

## 2. The Big Picture - System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React/Next.js)                          │
│            User uploads files, views charts, interacts               │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ HTTP Requests
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         run_api.py                                   │
│                    (Entry Point - Starts Server)                     │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    src/api/main.py                                   │
│        FastAPI App - Middleware, CORS, Request Handling              │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    src/api/routers/                                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│   │upload.py │  │samples.py│  │analysis.py│  │ auth.py  │           │
│   │ Upload   │  │  Query   │  │ Reanalyze│  │  Login   │           │
│   │ Files    │  │  Data    │  │  Samples │  │  Auth    │           │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
└────────┼─────────────┼─────────────┼─────────────┼──────────────────┘
         │             │             │             │
         ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐     │
│  │   PARSERS   │  │   PHYSICS   │  │    VISUALIZATION        │     │
│  │ fcs_parser  │  │ mie_scatter │  │  anomaly_detection      │     │
│  │ nta_parser  │  │ size_config │  │  cross_comparison       │     │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘     │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DATABASE LAYER                                    │
│           models.py │ crud.py │ connection.py                        │
│                PostgreSQL / SQLite                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Your Learning Path - Where to Start

### 📚 Recommended Reading Order

Follow this order to build understanding progressively:

#### Week 1: Entry Points & API
| Order | File | Time | What You'll Learn |
|-------|------|------|-------------------|
| 1 | `run_api.py` | 5 min | How the server starts |
| 2 | `src/api/main.py` | 15 min | FastAPI setup, middleware, lifecycle |
| 3 | `src/api/config.py` | 10 min | Configuration management |
| 4 | `src/api/routers/samples.py` | 30 min | How API endpoints work (big file, skim first) |

#### Week 2: Data Processing
| Order | File | Time | What You'll Learn |
|-------|------|------|-------------------|
| 5 | `src/parsers/fcs_parser.py` | 20 min | How FCS files are read |
| 6 | `src/parsers/nta_parser.py` | 15 min | How NTA files are read |
| 7 | `src/physics/size_config.py` | 10 min | Size category definitions |

#### Week 3: Core Science
| Order | File | Time | What You'll Learn |
|-------|------|------|-------------------|
| 8 | `src/physics/mie_scatter.py` | 45 min | **THE CORE** - Particle sizing physics |
| 9 | `src/visualization/anomaly_detection.py` | 20 min | Outlier detection |

#### Week 4: Database
| Order | File | Time | What You'll Learn |
|-------|------|------|-------------------|
| 10 | `src/database/models.py` | 20 min | Database table definitions |
| 11 | `src/database/crud.py` | 15 min | Database operations |
| 12 | `src/database/connection.py` | 10 min | Connection management |

---

## 4. Directory Map - What's Where

```
backend/
│
├── 🚀 run_api.py              # START HERE! Entry point
│
├── 📦 src/                    # All source code lives here
│   │
│   ├── 🌐 api/                # HTTP API Layer
│   │   ├── main.py            # FastAPI app setup
│   │   ├── config.py          # Settings (.env reader)
│   │   └── routers/           # API endpoints
│   │       ├── upload.py      # POST /upload/fcs & /upload/nta
│   │       ├── samples.py     # GET /samples, /scatter-data, /size-bins
│   │       ├── analysis.py    # POST /reanalyze
│   │       ├── auth.py        # POST /login, /register
│   │       ├── jobs.py        # GET /jobs (background processing)
│   │       └── alerts.py      # GET /alerts
│   │
│   ├── 📂 parsers/            # File Readers
│   │   ├── base_parser.py     # Abstract base class
│   │   ├── fcs_parser.py      # ⭐ FCS file parser (Flow Cytometry)
│   │   ├── nta_parser.py      # NTA CSV parser
│   │   ├── nta_pdf_parser.py  # NTA PDF parser
│   │   └── parquet_writer.py  # Efficient data storage
│   │
│   ├── 🔬 physics/            # Scientific Calculations
│   │   ├── mie_scatter.py     # ⭐⭐ CORE: Mie theory (FSC → size)
│   │   ├── size_config.py     # Size categories (Small/Medium/Large EV)
│   │   ├── size_distribution.py
│   │   ├── bead_calibration.py
│   │   └── statistics_utils.py
│   │
│   ├── 📊 visualization/      # Analysis & Plotting
│   │   ├── anomaly_detection.py  # ⭐ Detect outliers
│   │   ├── cross_comparison.py   # FCS vs NTA comparison
│   │   ├── auto_axis_selector.py # Smart channel selection
│   │   ├── fcs_plots.py
│   │   └── nta_plots.py
│   │
│   ├── 🗄️ database/            # Database Layer
│   │   ├── models.py          # ⭐ Table definitions (ORM)
│   │   ├── crud.py            # Create/Read/Update/Delete
│   │   └── connection.py      # Connection pool
│   │
│   └── 🔧 utils/              # Utilities
│       └── channel_config.py  # Channel detection (FSC, SSC)
│
├── 📁 data/                   # Data Storage
│   ├── uploads/               # Uploaded files go here
│   ├── parquet/               # Processed data
│   └── temp/                  # Temporary files
│
├── 📁 alembic/                # Database Migrations
│   └── versions/              # Migration scripts
│
├── 📁 tests/                  # Unit Tests
├── 📁 scripts/                # Utility Scripts
├── 📁 docs/                   # Documentation (you are here!)
└── 📁 figures/                # Generated Plots
```

---

## 5. Following a Request - End-to-End Flow

Let's trace what happens when a user uploads an FCS file:

### Step-by-Step: FCS File Upload

```
User clicks "Upload" in frontend
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1: HTTP Request arrives                                         │
│                                                                       │
│   POST /api/v1/upload/fcs                                            │
│   Body: { file: binary_data, treatment: "CD81" }                     │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 2: Router handles request                                       │
│                                                                       │
│   File: src/api/routers/upload.py                                    │
│   Function: upload_fcs_file()                                        │
│                                                                       │
│   What happens:                                                       │
│   - Validates file type (.fcs)                                       │
│   - Saves file to data/uploads/                                      │
│   - Creates database record                                          │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 3: Parse the FCS file                                           │
│                                                                       │
│   File: src/parsers/fcs_parser.py                                    │
│   Class: FCSParser                                                    │
│                                                                       │
│   What happens:                                                       │
│   - Reads binary FCS format                                          │
│   - Extracts channel names (VFSC-H, VSSC1-H, etc.)                   │
│   - Extracts all events (rows of measurements)                       │
│   - Returns DataFrame with all data                                  │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 4: Calculate particle sizes                                     │
│                                                                       │
│   File: src/physics/mie_scatter.py                                   │
│   Class: MieScatterCalculator                                         │
│                                                                       │
│   What happens:                                                       │
│   - Takes FSC (Forward Scatter) values                               │
│   - Applies Mie scattering theory                                    │
│   - Converts light intensity → particle diameter (nm)                │
│   - Returns array of sizes for each event                            │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 5: Detect anomalies                                             │
│                                                                       │
│   File: src/visualization/anomaly_detection.py                       │
│   Class: AnomalyDetector                                              │
│                                                                       │
│   What happens:                                                       │
│   - Checks for outliers using Z-score and IQR                        │
│   - Flags suspicious data points                                     │
│   - Calculates anomaly percentage                                    │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 6: Save results to database                                     │
│                                                                       │
│   File: src/database/crud.py                                         │
│   Functions: create_sample(), create_fcs_result()                    │
│                                                                       │
│   What's saved:                                                       │
│   - Sample metadata (name, treatment, user)                          │
│   - FCS results (total events, median size, size bins)               │
│   - QC status (pass/warn/fail)                                       │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 7: Return response to frontend                                  │
│                                                                       │
│   Response JSON:                                                      │
│   {                                                                   │
│     "sample_id": "EXO_CD81_001",                                     │
│     "total_events": 1187417,                                         │
│     "median_size": 124.5,                                            │
│     "size_distribution": { "small": 30, "medium": 55, "large": 15 } │
│   }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Core Modules Deep Dive

### 6.1 API Routers (`src/api/routers/`)

#### upload.py - File Upload Handler
```python
# This is where files enter the system

@router.post("/fcs")
async def upload_fcs_file(
    file: UploadFile = File(...),           # The uploaded file
    treatment: str = Form(None),             # Optional treatment name
    db: AsyncSession = Depends(get_session)  # Database session
):
    # 1. Save file to disk
    file_path = save_uploaded_file(file)
    
    # 2. Parse the file
    parser = FCSParser(file_path)
    data = parser.parse()
    
    # 3. Calculate sizes using Mie theory
    mie = MieScatterCalculator()
    sizes = mie.diameters_from_scatter_normalized(data['VFSC-H'])
    
    # 4. Save to database
    sample = await create_sample(db, sample_data)
    
    # 5. Return results
    return {"sample_id": sample.sample_id, ...}
```

#### samples.py - Data Query Handler
```python
# This file has MANY endpoints (2700+ lines!)
# Key ones to know:

@router.get("/")                    # List all samples
@router.get("/{sample_id}")         # Get one sample
@router.get("/{sample_id}/scatter-data")  # Get scatter plot data
@router.get("/{sample_id}/size-bins")     # Get size category counts
@router.get("/{sample_id}/fcs/values")    # Get per-event sizes
@router.delete("/{sample_id}")      # Delete a sample
```

### 6.2 Parsers (`src/parsers/`)

#### fcs_parser.py - Reading FCS Files
```python
from src.parsers.fcs_parser import FCSParser

# Initialize with file path
parser = FCSParser(Path("data/uploads/sample.fcs"))

# Parse the file
data = parser.parse()  # Returns pandas DataFrame

# Access channel names
print(parser.channel_names)  
# ['VFSC-H', 'VFSC-A', 'VSSC1-H', 'VSSC1-A', ...]

# Access sample ID (extracted from filename)
print(parser.sample_id)
# 'EXO_CD81_001'
```

### 6.3 Physics (`src/physics/`)

#### mie_scatter.py - The Core Science
```python
from src.physics.mie_scatter import MieScatterCalculator

# Create calculator with optical parameters
mie = MieScatterCalculator(
    wavelength_nm=488,    # Blue laser (common in flow cytometry)
    n_particle=1.40,      # Refractive index of EVs
    n_medium=1.33         # Refractive index of water/buffer
)

# Convert FSC values to particle diameters
# This is the main function you'll use!
diameters, valid_mask = mie.diameters_from_scatter_normalized(
    fsc_values,           # Array of Forward Scatter intensities
    min_diameter=20.0,    # Minimum valid size (nm)
    max_diameter=500.0    # Maximum valid size (nm)
)

# diameters: array of sizes in nanometers [87.3, 124.5, 156.2, ...]
# valid_mask: boolean array [True, True, False, True, ...]
```

### 6.4 Visualization (`src/visualization/`)

#### anomaly_detection.py - Finding Outliers
```python
from src.visualization.anomaly_detection import AnomalyDetector

detector = AnomalyDetector()

# Detect anomalies using multiple methods
results = detector.detect_anomalies(
    data,                    # DataFrame with FCS data
    x_channel='VFSC-H',      # X axis channel
    y_channel='VSSC1-H',     # Y axis channel
    method='both',           # 'zscore', 'iqr', or 'both'
    zscore_threshold=3.0,    # Z-score threshold
    iqr_factor=1.5           # IQR multiplier
)

# results contains:
# - anomalous_indices: list of row indices that are anomalies
# - anomaly_percentage: what % of data is anomalous
# - zscore_anomalies: count from Z-score method
# - iqr_anomalies: count from IQR method
```

---

## 7. The Science Behind It - Mie Theory Explained

### What is Mie Scattering?

When light hits a small particle, it **scatters** in all directions. The pattern of scattering depends on:

1. **Particle size** (d) - diameter in nanometers
2. **Light wavelength** (λ) - laser wavelength (488nm for blue)
3. **Refractive indices** - how much light bends in particle vs medium

### The Key Equation

```
Size Parameter:  x = πd/λ

Where:
- x = dimensionless size parameter
- d = particle diameter (nm)
- λ = wavelength (nm)
```

### What Flow Cytometry Measures

```
        Light Source (Laser)
              │
              ▼
         ┌─────────┐
         │ Particle │ ──────► Side Scatter (SSC)
         └─────────┘         90° to laser
              │              Measures COMPLEXITY
              ▼
       Forward Scatter (FSC)
       Along laser beam
       Measures SIZE
```

### How We Calculate Size

```python
# The Mie calculator does this:

1. Take FSC intensity value (e.g., 500,000)
2. Normalize to physical scatter range (0.01 - 100)
3. Search for diameter that produces this scatter
4. Return diameter in nanometers (e.g., 124.5 nm)
```

### Size Categories (EVs)

| Category | Size Range | What They Are |
|----------|------------|---------------|
| **Small EVs** | 30-100 nm | Exomeres, small exosomes |
| **Medium EVs** | 100-200 nm | Classic exosomes |
| **Large EVs** | 200-500 nm | Microvesicles |
| **Very Large** | 500+ nm | Apoptotic bodies, debris |

---

## 8. Database Structure

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                              USERS                                   │
│  ┌────────┬────────────────┬───────────────┬──────────┬───────────┐ │
│  │   id   │     email      │ password_hash │   role   │ created   │ │
│  │   PK   │    UNIQUE      │               │ enum     │ timestamp │ │
│  └────────┴────────────────┴───────────────┴──────────┴───────────┘ │
│       │                                                              │
│       │ 1:N (One user can have many samples)                        │
│       ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                           SAMPLES                                ││
│  │  ┌────────┬─────────────┬───────────┬───────────┬─────────────┐ ││
│  │  │   id   │  sample_id  │  user_id  │ file_path │   status    │ ││
│  │  │   PK   │   UNIQUE    │    FK     │  string   │   enum      │ ││
│  │  └────────┴─────────────┴───────────┴───────────┴─────────────┘ ││
│  └──────────────────────────────┬──────────────────────────────────┘│
│                                 │                                    │
│       ┌─────────────────────────┼─────────────────────────┐         │
│       │                         │                         │         │
│       ▼                         ▼                         ▼         │
│  ┌───────────────┐       ┌───────────────┐       ┌───────────────┐ │
│  │  FCS_RESULTS  │       │  NTA_RESULTS  │       │  QC_REPORTS   │ │
│  │ ───────────── │       │ ───────────── │       │ ───────────── │ │
│  │ sample_id FK  │       │ sample_id FK  │       │ sample_id FK  │ │
│  │ total_events  │       │ particle_count│       │ status        │ │
│  │ median_size   │       │ mean_size     │       │ passed_checks │ │
│  │ size_dist     │       │ mode_size     │       │ warnings      │ │
│  └───────────────┘       └───────────────┘       └───────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Models (from models.py)

```python
class Sample(Base):
    """Main sample record"""
    id = Column(Integer, primary_key=True)
    sample_id = Column(String, unique=True)  # Human-readable ID
    user_id = Column(Integer, ForeignKey('users.id'))
    file_path_fcs = Column(String)
    file_path_nta = Column(String)
    processing_status = Column(Enum(ProcessingStatus))
    qc_status = Column(Enum(QCStatus))
    upload_timestamp = Column(DateTime, default=func.now())

class FCSResult(Base):
    """Flow cytometry analysis results"""
    id = Column(Integer, primary_key=True)
    sample_id = Column(Integer, ForeignKey('samples.id'))
    total_events = Column(Integer)
    median_size = Column(Float)
    size_distribution = Column(JSON)  # {small: 30, medium: 55, large: 15}
    
class User(Base):
    """User account"""
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password_hash = Column(String)
    role = Column(Enum(UserRole))  # user, researcher, admin
```

---

## 9. Common Code Patterns

### Pattern 1: API Endpoint with Database
```python
@router.get("/{sample_id}")
async def get_sample(
    sample_id: str,
    db: AsyncSession = Depends(get_session)  # Dependency injection
):
    # Query database
    result = await db.execute(
        select(Sample).where(Sample.sample_id == sample_id)
    )
    sample = result.scalar_one_or_none()
    
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    
    return {"sample": sample}
```

### Pattern 2: Using the FCS Parser
```python
from src.parsers.fcs_parser import FCSParser

def process_fcs_file(file_path: Path):
    # Initialize parser
    parser = FCSParser(file_path)
    
    # Validate first
    if not parser.validate():
        raise ValueError("Invalid FCS file")
    
    # Parse and get data
    data = parser.parse()  # Returns DataFrame
    
    # Access channels
    channels = parser.channel_names
    
    return data, channels
```

### Pattern 3: Using Mie Calculator
```python
from src.physics.mie_scatter import MieScatterCalculator

def calculate_sizes(fsc_values: np.ndarray) -> np.ndarray:
    # Initialize with optical parameters
    mie = MieScatterCalculator(
        wavelength_nm=488,
        n_particle=1.40,
        n_medium=1.33
    )
    
    # Calculate sizes
    diameters, valid_mask = mie.diameters_from_scatter_normalized(
        fsc_values,
        min_diameter=20.0,
        max_diameter=500.0
    )
    
    # Return only valid sizes
    return diameters[valid_mask]
```

### Pattern 4: Logging
```python
from loguru import logger

# The codebase uses loguru with emoji markers:
logger.info("📊 Processing sample...")      # Info
logger.success("✅ Analysis complete")       # Success
logger.warning("⚠️ Low event count")         # Warning
logger.error("❌ Failed to parse file")      # Error
```

---

## 10. Cheat Sheet - Quick Reference

### Start the Server
```bash
cd backend
python run_api.py
```

### Key URLs
| URL | Purpose |
|-----|---------|
| `http://localhost:8000` | API root |
| `http://localhost:8000/docs` | Swagger UI (interactive!) |
| `http://localhost:8000/redoc` | ReDoc documentation |
| `http://localhost:8000/health` | Health check |

### Important Files by Task

| If you need to... | Look in... |
|-------------------|------------|
| Add a new endpoint | `src/api/routers/` |
| Modify file parsing | `src/parsers/fcs_parser.py` |
| Change size calculation | `src/physics/mie_scatter.py` |
| Add a database table | `src/database/models.py` |
| Add database operations | `src/database/crud.py` |
| Modify anomaly detection | `src/visualization/anomaly_detection.py` |
| Change size categories | `src/physics/size_config.py` |
| Update configuration | `.env` + `src/api/config.py` |

### Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `FCSParser` | `src/parsers/fcs_parser.py` | Parse FCS files |
| `MieScatterCalculator` | `src/physics/mie_scatter.py` | Calculate sizes |
| `AnomalyDetector` | `src/visualization/anomaly_detection.py` | Find outliers |
| `Sample` | `src/database/models.py` | Sample ORM model |
| `FCSResult` | `src/database/models.py` | FCS results ORM model |

### Database Commands
```bash
# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Check current version
alembic current
```

### Common Imports
```python
# API
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Database
from src.database.connection import get_session
from src.database.models import Sample, FCSResult
from src.database.crud import create_sample, get_sample_by_id

# Parsers
from src.parsers.fcs_parser import FCSParser
from src.parsers.nta_parser import NTAParser

# Physics
from src.physics.mie_scatter import MieScatterCalculator
from src.physics.size_config import DEFAULT_SIZE_CONFIG

# Visualization
from src.visualization.anomaly_detection import AnomalyDetector

# Logging
from loguru import logger
```

---

## 🎯 Next Steps

1. **Run the server** and explore the Swagger UI at `/docs`
2. **Read the files** in the order suggested in Section 3
3. **Try uploading a file** and trace the code path
4. **Set breakpoints** in VS Code to step through the code
5. **Ask questions!** - We're here to help

---

*Welcome to the team! 🚀*

*Last updated: January 2026*
