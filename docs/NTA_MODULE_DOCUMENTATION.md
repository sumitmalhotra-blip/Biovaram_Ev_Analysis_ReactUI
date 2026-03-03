# NTA Module — Complete Documentation

## BioVaram EV Analysis Platform

**Prepared for:** Charmi  
**Last Updated:** March 2026  
**Version:** 1.0  

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [System Architecture](#2-system-architecture)
3. [Setup & Installation](#3-setup--installation)
4. [Backend Files — Detailed Reference](#4-backend-files--detailed-reference)
   - 4.1 [NTA Text Parser](#41-nta-text-parser)
   - 4.2 [NTA PDF Parser](#42-nta-pdf-parser)
   - 4.3 [NTA Physics Corrections](#43-nta-physics-corrections)
   - 4.4 [Database Model](#44-database-model)
   - 4.5 [API Endpoints](#45-api-endpoints)
5. [Frontend Files — Detailed Reference](#5-frontend-files--detailed-reference)
   - 5.1 [NTA Tab (Upload View)](#51-nta-tab-upload-view)
   - 5.2 [Analysis Results View](#52-analysis-results-view)
   - 5.3 [Statistics Cards](#53-statistics-cards)
   - 5.4 [Size Distribution Breakdown](#54-size-distribution-breakdown)
   - 5.5 [Position Analysis](#55-position-analysis)
   - 5.6 [Temperature Settings](#56-temperature-settings)
   - 5.7 [Supplementary Metadata Table](#57-supplementary-metadata-table)
   - 5.8 [Best Practices Guide](#58-best-practices-guide)
   - 5.9 [Charts](#59-charts)
6. [State Management & API Client](#6-state-management--api-client)
7. [Data Flow — End to End](#7-data-flow--end-to-end)
8. [Cross-Validation with FCS](#8-cross-validation-with-fcs)
9. [File Summary Table](#9-file-summary-table)
10. [How to Run the Tool](#10-how-to-run-the-tool)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Module Overview

The **NTA (Nanoparticle Tracking Analysis)** module processes data from a **ZetaView** instrument. ZetaView tracks individual nanoparticles in solution using laser light scattering and Brownian motion to determine their size and concentration.

### What the NTA Module Does

| Capability | Description |
|------------|-------------|
| **File Parsing** | Reads ZetaView `.txt` and `.csv` files (size distribution, zeta potential, 11-position uniformity) |
| **PDF Parsing** | Extracts original concentration and dilution factor from ZetaView PDF reports |
| **Temperature-Viscosity Correction** | Applies Stokes-Einstein corrections to adjust sizes measured at different temperatures back to a 25°C reference |
| **Size Binning** | Categorizes particles into EV sub-type bins (50–80 nm, 80–100 nm, 100–120 nm, 120–150 nm, 150–200 nm, 200+ nm) |
| **Statistics** | Calculates D10, D50 (median), D90, mean, mode, weighted standard deviation |
| **Cross-Validation** | Compares NTA size distributions against Flow Cytometry (FCS) data for quality assurance |
| **Visualization** | Renders interactive size distribution, concentration profile, pie chart, and temperature-corrected comparison charts |
| **Alerting** | Generates quality alerts for low concentration, high polydispersity, and abnormal temperatures |
| **Export** | Supports Markdown, Excel, PDF, and Parquet export formats |

### Key Scientific Concepts

**Stokes-Einstein Equation:**

$$D = \frac{k_B \cdot T}{3\pi \cdot \eta \cdot d}$$

Where:
- $D$ = diffusion coefficient (m²/s)
- $k_B$ = Boltzmann constant ($1.380649 \times 10^{-23}$ J/K)
- $T$ = temperature (K)
- $\eta$ = dynamic viscosity (Pa·s)
- $d$ = hydrodynamic diameter (m)

The NTA instrument measures $D$ from particle Brownian motion and calculates $d$. If the measurement temperature differs from 25°C, a correction must be applied:

$$d_{\text{corrected}} = d_{\text{raw}} \times \frac{\eta_{\text{ref}}}{\eta_{\text{meas}}} \times \frac{T_{\text{meas}}}{T_{\text{ref}}}$$

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                       │
│                                                                   │
│  components/nta/nta-tab.tsx          ← Upload UI                 │
│  components/nta/nta-analysis-results ← Results container          │
│  components/nta/statistics-cards     ← Key metrics                │
│  components/nta/charts/              ← 4 interactive charts       │
│  components/nta/position-analysis    ← 11-position data           │
│  components/nta/temperature-settings ← Stokes-Einstein controls   │
│  lib/store.ts                        ← Zustand state management   │
│  lib/api-client.ts                   ← HTTP client to backend     │
│                                                                   │
├───────────────────── HTTP (localhost:8000) ───────────────────────┤
│                                                                   │
│                       BACKEND (FastAPI/Python)                    │
│                                                                   │
│  routers/upload.py                                                │
│    POST /upload/nta       ← Upload NTA text file                  │
│    POST /upload/nta-pdf   ← Upload NTA PDF report                 │
│                                                                   │
│  routers/samples.py                                               │
│    GET /{id}/nta          ← Get NTA results from DB               │
│    GET /{id}/nta/metadata ← Get NTA file metadata                 │
│    GET /{id}/nta/values   ← Get per-bin size/concentration data   │
│    GET /{fcs}/cross-validate/{nta} ← FCS vs NTA comparison        │
│                                                                   │
│  parsers/nta_parser.py    ← Parse .txt/.csv files                 │
│  parsers/nta_pdf_parser.py ← Parse PDF reports                    │
│  physics/nta_corrections.py ← Temperature/viscosity corrections   │
│  database/models.py       ← NTAResult SQLAlchemy model            │
│                                                                   │
│                    DATABASE (SQLite)                               │
│  Tables: samples, nta_results, processing_jobs, alerts            │
└───────────────────────────────────────────────────────────────────┘
```

---

## 3. Setup & Installation

### Prerequisites

| Software | Version | Notes |
|----------|---------|-------|
| **Node.js** | 18.0+ | For Next.js frontend |
| **pnpm** | Latest | Package manager (`npm install -g pnpm`) |
| **Python** | 3.10 – 3.13 | For FastAPI backend |
| **Git** | Latest | For version control |

### Step-by-Step Installation

#### 1. Clone the Repository

```powershell
git clone https://github.com/sumitmalhotra-blip/Biovaram_Ev_Analysis_ReactUI.git
cd Biovaram_Ev_Analysis_ReactUI
```

#### 2. Install Frontend Dependencies

```powershell
pnpm install
```

#### 3. Setup Python Backend

```powershell
cd backend

# Create virtual environment
python -m venv venv

# Activate it (PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

cd ..
```

#### 4. Configure Environment Variables

**Frontend** — Create `.env.local` in root:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Backend** — Create `.env` in `backend/`:
```env
CRMIT_DB_URL=sqlite+aiosqlite:///./data/crmit.db
CRMIT_ENVIRONMENT=development
CRMIT_LOG_LEVEL=DEBUG
CRMIT_CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

#### 5. Start the Application

**Option A: Quick Start Script (Windows)**
```powershell
.\start.ps1
```

**Option B: Manual (Two Terminals)**

Terminal 1 — Backend API:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python run_api.py
```

Terminal 2 — Frontend:
```powershell
pnpm dev
```

#### 6. Verify

- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

The database (`data/crmit.db`) is created automatically on first run.

### NTA-Specific Dependencies (in `requirements.txt`)

| Package | Purpose |
|---------|---------|
| `pandas>=2.0.0` | DataFrame operations for parsed NTA data |
| `numpy>=1.24.0` | Numerical computations, percentiles, weighted statistics |
| `pdfplumber>=0.10.0` | Extract text from ZetaView PDF reports |
| `loguru>=0.7.2` | Structured logging with colored output |
| `fastapi` | REST API framework |
| `sqlalchemy[asyncio]` | Async ORM for database operations |
| `aiosqlite` | Async SQLite driver |

---

## 4. Backend Files — Detailed Reference

### 4.1 NTA Text Parser

**File:** `backend/src/parsers/nta_parser.py` (609 lines)

**Purpose:** Parses ZetaView NTA text files (`.txt` / `.csv`) containing size distribution, zeta potential profile, or 11-position uniformity data.

**Class: `NTAParser`** (extends `BaseParser`)

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__(file_path)` | `Path \| str` | — | Initialize parser with file path |
| `validate()` | — | `bool` | Check file exists and contains ZetaView indicators |
| `parse()` | — | `pd.DataFrame` | Main entry point — detects file type and parses accordingly |
| `_detect_file_type()` | — | `str` | Determines `'size'`, `'prof'`, `'11pos'`, or combinations from filename |
| `_parse_metadata(lines)` | `List[str]` | `Dict[str, str]` | Extracts 30+ metadata fields (operator, temperature, viscosity, pH, etc.) |
| `_extract_sample_id()` | — | `str` | Derives sample ID from metadata or filename pattern |
| `_extract_measurement_params()` | — | `None` | Converts metadata strings to numeric measurement parameters |
| `_parse_size_distribution(lines)` | `List[str]` | `pd.DataFrame` | Parses "Size Distribution" section — tab/space delimited |
| `_parse_profile_data(lines)` | `List[str]` | `pd.DataFrame` | Parses "ZP Profile:" section for zeta potential data |
| `_parse_11pos_data(lines)` | `List[str]` | `pd.DataFrame` | Parses 11-position uniformity measurement with position-wise statistics |
| `_standardize_column_names(df, data_type)` | `DataFrame, str` | `pd.DataFrame` | Maps vendor-specific column names to standard names |
| `_add_metadata_columns()` | — | `None` | Adds `sample_id`, `file_name`, `instrument_type`, `measurement_type` columns |
| `extract_metadata()` | — | `Dict[str, Any]` | Returns complete metadata dictionary including measurement params |
| `get_summary_statistics()` | — | `Dict[str, Any]` | Calculates weighted mean, median, D10/D50/D90, concentration CV |

**Standardized Column Names:**

| Original (ZetaView) | Standardized |
|---------------------|-------------|
| `Size / nm` | `size_nm` |
| `Orig. Conc. p./cm³` | `concentration_particles_cm3` |
| `Conc. p./mL` | `concentration_particles_ml` |
| `Volume nm³` | `volume_nm3` |
| `Area nm²` | `area_nm2` |
| `Number` | `particle_count` |
| `ZP (mV)` | `zeta_potential_mv` |
| `Mean Int.` | `mean_intensity` |
| `X50 (nm)` | `median_size_nm` |

**Supported File Types:**

| Pattern in Filename | Type | Description |
|--------------------|------|-------------|
| `_size_488` | Size distribution | Per-bin particle size and concentration data |
| `_prof_488` | Zeta potential profile | Position-wise zeta potential measurements |
| `_11pos` | 11-position uniformity | Cell uniformity check across 11 positions |

**Example Usage:**
```python
from src.parsers.nta_parser import NTAParser
from pathlib import Path

parser = NTAParser(Path("data/uploads/sample_size_488.txt"))
if parser.validate():
    df = parser.parse()
    metadata = parser.extract_metadata()
    stats = parser.get_summary_statistics()
    print(f"Median size: {stats.get('median_size_nm')} nm")
```

---

### 4.2 NTA PDF Parser

**File:** `backend/src/parsers/nta_pdf_parser.py` (413 lines)

**Purpose:** Extracts critical information from ZetaView PDF reports that is **NOT** available in the text file — specifically the **original concentration** and **dilution factor**.

> **Client Quote (Surya, Dec 3, 2025):**  
> *"That number is not ever mentioned in a text format... it is always mentioned only in the PDF file... I was struggling through"*

**Dataclass: `NTAPDFData`**

| Field | Type | Description |
|-------|------|-------------|
| `original_concentration` | `float \| None` | particles/mL |
| `dilution_factor` | `int \| None` | e.g., 500 |
| `true_particle_population` | `float \| None` | = concentration × dilution |
| `mean_size_nm` | `float \| None` | Mean diameter |
| `mode_size_nm` | `float \| None` | Mode diameter |
| `median_size_nm` | `float \| None` | Median diameter |
| `d10_nm`, `d50_nm`, `d90_nm` | `float \| None` | Percentile diameters |
| `sample_name` | `str \| None` | From PDF |
| `measurement_date` | `str \| None` | Acquisition date |
| `operator` | `str \| None` | Operator name |
| `extraction_successful` | `bool` | Whether extraction worked |
| `extraction_errors` | `List[str]` | Errors encountered |

**Class: `NTAPDFParser`**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__(pdf_path)` | `Path` | — | Initialize with PDF file path |
| `validate()` | — | `bool` | Checks pdfplumber availability, file existence, and extension |
| `_extract_text()` | — | `bool` | Extracts text from all PDF pages using pdfplumber |
| `_extract_value(pattern, text)` | `str, str` | `str \| None` | Helper: apply regex and return first capture group |
| `_extract_concentration(text)` | `str` | `(float, str)` | Extracts concentration (scientific notation, E-notation, or plain) |
| `_extract_dilution(text)` | `str` | `int \| None` | Extracts dilution factor |
| `parse()` | — | `NTAPDFData` | Main entry — extracts all fields from PDF |
| `to_dict()` | — | `Dict[str, Any]` | Returns results as dictionary |

**Convenience Function:**
```python
from src.parsers.nta_pdf_parser import parse_nta_pdf
result = parse_nta_pdf(Path("report.pdf"))
print(f"Concentration: {result['original_concentration']:.2e} particles/mL")
print(f"Dilution: {result['dilution_factor']}x")
print(f"True population: {result['true_particle_population']:.2e}")
```

**Dependency:** Requires `pdfplumber` (`pip install pdfplumber`). If not installed, PDF parsing is disabled gracefully.

---

### 4.3 NTA Physics Corrections

**File:** `backend/src/physics/nta_corrections.py` (679 lines)

**Purpose:** Implements Stokes-Einstein temperature-viscosity corrections for NTA measurements. When the ZetaView measures at a temperature other than 25°C, the particle sizes must be corrected because water viscosity changes with temperature.

**Constants:**
- `BOLTZMANN_CONSTANT = 1.380649e-23` J/K
- `REFERENCE_TEMPERATURE_C = 25.0` °C

**Key Functions:**

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `celsius_to_kelvin(temp_c)` | `float` | `float` | Temperature conversion |
| `calculate_water_viscosity(temperature_c)` | `float` | `float` (Pa·s) | Kestin et al. (1978) correlation, ±0.5% accuracy for 0–100°C |
| `calculate_water_viscosity_simple(temperature_c)` | `float` | `float` (Pa·s) | Polynomial approximation, ±2% accuracy for 15–40°C |
| `stokes_einstein_diffusion(diameter_nm, temperature_c, viscosity_pas?)` | `float, float, float?` | `float` (m²/s) | Calculate diffusion coefficient from diameter |
| `stokes_einstein_diameter(diffusion_coeff, temperature_c, viscosity_pas?)` | `float, float, float?` | `float` (nm) | Calculate diameter from diffusion coefficient (inverse) |
| `correct_nta_size(raw_size_nm, measurement_temp_c, reference_temp_c=25, ...)` | `float\|ndarray, ...` | `float\|ndarray` | **Main correction function** — applies viscosity-temperature correction |
| `get_correction_factor(measurement_temp_c, reference_temp_c=25, ...)` | `float, ...` | `(float, Dict)` | Returns correction factor + detailed parameter breakdown |
| `apply_corrections_to_dataframe(df, size_column, measurement_temp_c, ...)` | `DataFrame, str, float, ...` | `DataFrame` | Add corrected size column to DataFrame |
| `get_viscosity_temperature_table(temp_start, temp_end, temp_step)` | `float, float, float` | `DataFrame` | Reference table of viscosity vs temperature |
| `get_correction_reference_table(measurement_temps?, reference_temp_c?)` | `list?, float?` | `DataFrame` | Reference table of correction factors |
| `get_media_viscosity(media_type, temperature_c)` | `str, float` | `(float, str)` | Estimated viscosity for common lab media |
| `create_correction_summary(raw_sizes, measurement_temp_c, reference_temp_c, media_type)` | `ndarray, float, float, str` | `Dict` | Comprehensive summary with raw/corrected statistics |

**Media Viscosity Factors (relative to water):**

| Media | Factor |
|-------|--------|
| Water | 1.00 |
| PBS | 1.02 |
| DMEM | 1.05 |
| Serum-free | 1.03 |
| 10% FBS | 1.15 |
| 20% FBS | 1.30 |
| 10% sucrose | 1.35 |
| 20% sucrose | 1.95 |

**Correction Factor Examples (reference = 25°C):**

| Measurement Temp | Correction Factor | Size Change |
|-----------------|-------------------|-------------|
| 20°C | 0.936 | -6.4% |
| 22°C | 0.959 | -4.1% |
| 25°C | 1.000 | 0% |
| 30°C | 1.060 | +6.0% |
| 37°C | 1.146 | +14.6% |

**Example:**
```python
from src.physics.nta_corrections import correct_nta_size, get_correction_factor

# Correct a single size
corrected = correct_nta_size(100, measurement_temp_c=22, reference_temp_c=25)
# Result: ~95.9 nm

# Correct an array
import numpy as np
sizes = np.array([80, 100, 120, 150])
corrected = correct_nta_size(sizes, measurement_temp_c=37, reference_temp_c=25)
```

---

### 4.4 Database Model

**File:** `backend/src/database/models.py` — class `NTAResult`

**Table name:** `nta_results`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | Integer | No (PK) | Auto-increment primary key |
| `sample_id` | Integer | No (FK → samples.id) | Foreign key to samples table |
| `mean_size_nm` | Float | No | Weighted mean particle size |
| `median_size_nm` | Float | No | D50 median size |
| `mode_size_nm` | Float | Yes | Most frequent size bin |
| `d10_nm` | Float | Yes | 10th percentile size |
| `d50_nm` | Float | Yes | 50th percentile (median) |
| `d90_nm` | Float | Yes | 90th percentile size |
| `std_dev_nm` | Float | Yes | Standard deviation |
| `concentration_particles_ml` | Float | Yes | Total particle concentration |
| `bin_30_50nm_pct` | Float | Yes | % particles in 30–50 nm |
| `bin_50_80nm_pct` | Float | Yes | % particles in 50–80 nm |
| `bin_80_100nm_pct` | Float | Yes | % particles in 80–100 nm |
| `bin_100_120nm_pct` | Float | Yes | % particles in 100–120 nm |
| `bin_120_150nm_pct` | Float | Yes | % particles in 120–150 nm |
| `bin_150_200nm_pct` | Float | Yes | % particles in 150–200 nm |
| `temperature_celsius` | Float | Yes | Measurement temperature |
| `ph` | Float | Yes | Solution pH |
| `conductivity` | Float | Yes | Solution conductivity |
| `parquet_file_path` | Text | Yes | Path to Parquet data file |
| `measurement_date` | DateTime | Yes | When measurement was taken |
| `processed_at` | DateTime | No | When record was created |

**Relationships:**
- `sample` → belongs to `Sample` (back_populates `nta_results`)
- Cascade: `all, delete-orphan` — deleting a sample deletes all its NTA results

**CRUD Functions** (in `backend/src/database/crud.py`):
- `create_nta_result(db, sample_id, mean_size_nm, median_size_nm, ...)` — Insert new NTA result
- `get_sample_by_id(db, sample_id)` — Retrieve sample (includes NTA results via eager loading)

---

### 4.5 API Endpoints

All endpoints are prefixed with `/api/v1/`.

#### `POST /upload/nta` — Upload NTA Text File

**File:** `backend/src/api/routers/upload.py` (line 1254)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | UploadFile | Yes | `.txt` or `.csv` NTA file |
| `treatment` | str | No | Treatment name (e.g., "CD81") |
| `temperature_celsius` | float | No | Measurement temperature |
| `operator` | str | No | Operator name |
| `notes` | str | No | Additional notes |
| `user_id` | int | No | User ID for ownership |

**Processing Pipeline:**
1. Validate file extension (`.txt` or `.csv`)
2. Generate `sample_id` from filename
3. Save to `data/uploads/{timestamp}_{filename}`
4. Parse using `NTAParser` → DataFrame
5. Calculate weighted percentiles (D10, D50, D90)
6. Calculate size bin percentages
7. Create/update `Sample` record in database
8. Create `NTAResult` record
9. Create `ProcessingJob` record (status: completed)
10. Generate quality alerts (low concentration, high polydispersity, temp issues)
11. Extract file metadata for auto-filling experimental conditions
12. Return results with metadata

**Response:**
```json
{
  "success": true,
  "id": 42,
  "sample_id": "P5_F10_CD81",
  "job_id": "uuid",
  "status": "uploaded",
  "processing_status": "completed",
  "nta_results": {
    "mean_size_nm": 85.3,
    "median_size_nm": 82.1,
    "d10_nm": 65.2,
    "d50_nm": 82.1,
    "d90_nm": 105.3,
    "concentration_particles_ml": 1.5e11,
    "total_particles": 45000,
    "bin_50_80nm_pct": 35.2,
    "bin_80_100nm_pct": 28.7,
    "size_statistics": { "d10": 65.2, "d50": 82.1, "d90": 105.3, "mean": 85.3, "std": 22.1 }
  },
  "file_metadata": {
    "operator": "Lab Operator",
    "acquisition_date": "2025-12-17",
    "temperature_celsius": "22.5",
    "instrument": "D03231"
  }
}
```

---

#### `POST /upload/nta-pdf` — Upload NTA PDF Report

**File:** `backend/src/api/routers/upload.py` (line 1614)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | UploadFile | Yes | `.pdf` ZetaView report |
| `linked_sample_id` | str | No | Link PDF data to existing sample |

**Response:**
```json
{
  "success": true,
  "pdf_file": "report.pdf",
  "pdf_data": {
    "original_concentration": 3.5e10,
    "dilution_factor": 500,
    "true_particle_population": 1.75e13,
    "mean_size_nm": 120.5,
    "mode_size_nm": 95.3,
    "extraction_successful": true,
    "extraction_errors": []
  },
  "linked_sample_id": "P5_F10_CD81"
}
```

---

#### `GET /samples/{sample_id}/nta` — Get NTA Results

**File:** `backend/src/api/routers/samples.py` (line 570)

Returns all stored NTA results for a sample from the database.

---

#### `GET /samples/{sample_id}/nta/metadata` — Get NTA File Metadata

**File:** `backend/src/api/routers/samples.py` (line 3696)

Re-parses the NTA file to return instrument settings, acquisition parameters, and sample info. Includes:
- `file_info` — file name, size, measurement type
- `sample_info` — sample name, operator, experiment, electrolyte
- `instrument` — instrument serial, cell serial, software version, SOP
- `acquisition` — date, time, temperature, viscosity, pH, conductivity
- `measurement_params` — positions, traces, sensitivity, shutter, laser wavelength, dilution
- `quality` — cell check result, detected particles, scattering intensity

---

#### `GET /samples/{sample_id}/nta/values` — Get NTA Size/Concentration Data

**File:** `backend/src/api/routers/samples.py` (line 3796)

Returns per-bin data for plotting:
```json
{
  "sample_id": "P5_F10_CD81",
  "measurement_type": "size",
  "values": [
    { "bin_id": 0, "size_nm": 10.0, "concentration_particles_ml": 0 },
    { "bin_id": 1, "size_nm": 20.0, "concentration_particles_ml": 5230000 },
    ...
  ],
  "size_statistics": { "count": 100, "mean_nm": 85.3, "weighted_mean_nm": 82.1, ... },
  "concentration_statistics": { "total_particles_ml": 1.5e11, "peak_size_nm": 85.0 }
}
```

---

#### `GET /samples/{fcs_sample_id}/cross-validate/{nta_sample_id}` — Cross-Validation

**File:** `backend/src/api/routers/samples.py` (line 3936)

Compares FCS and NTA size distributions. Parameters include laser wavelength, particle/medium refractive indices, bin count, size range, and normalization flag.

---

## 5. Frontend Files — Detailed Reference

### 5.1 NTA Tab (Upload View)

**File:** `components/nta/nta-tab.tsx` (425 lines)

**Component:** `NTATab()` — The main NTA tab view.

**What it does:**
- Shows a **drag-and-drop file upload zone** for NTA `.txt`/`.csv` files
- Provides form fields for treatment, temperature, and operator
- Shows recent NTA samples as clickable badges
- Uploads the file to `POST /upload/nta` and stores results in Zustand
- After upload, shows `ExperimentalConditionsDialog` for capturing experiment metadata
- Includes a separate **PDF Report Upload** card (for ZetaView PDFs) that calls `POST /upload/nta-pdf`
- Also includes `NTATemperatureSettings` and `NTABestPracticesGuide` components above the upload area
- Shows loading spinner during analysis and error state with retry button
- Once results are available, renders `NTAAnalysisResults`

**Key State:**
- `selectedFile`, `selectedPdfFile` — uploaded files
- `treatment`, `temperature`, `operator` — form fields
- `ntaAnalysis` — from Zustand store (file, sampleId, results, isAnalyzing, error)

---

### 5.2 Analysis Results View

**File:** `components/nta/nta-analysis-results.tsx` (672 lines)

**Component:** `NTAAnalysisResults({ results, sampleId?, fileName? })`

**What it does:**
- Main results container with tabbed interface
- Contains 5 tabs:
  1. **Distribution** — `NTASizeDistributionChart` (size vs concentration histogram)
  2. **Categories** — `EVSizeCategoryPieChart` + `NTASizeDistributionBreakdown`
  3. **Profile** — `ConcentrationProfileChart` + `PositionAnalysis`
  4. **Correction** — `TemperatureCorrectedComparison`
  5. **Metadata** — `SupplementaryMetadataTable`
- Header bar with: `NTAStatisticsCards`, "New Analysis" button, Export dropdown
- **Overlay comparison**: Toggle to enable secondary NTA file overlay, upload secondary file
- **Export options**: Markdown report, Excel, PDF, Parquet
- **Pin to dashboard**: Pin any chart to the dashboard

---

### 5.3 Statistics Cards

**File:** `components/nta/statistics-cards.tsx`

**Component:** `NTAStatisticsCards({ results })`

Displays key metrics as cards:
- **Mean Size** (nm) — with standard deviation
- **Median Size** (D50) (nm) — with mode if available
- **D10 / D90** (nm) — 10th and 90th percentile
- **Concentration** (particles/mL) — in scientific notation
- **Total Particles**

---

### 5.4 Size Distribution Breakdown

**File:** `components/nta/size-distribution-breakdown.tsx`

**Component:** `NTASizeDistributionBreakdown({ results })`

Displays a stacked breakdown of EV size categories:

| Bin | Range | EV Subtype |
|-----|-------|-----------|
| Exosomes (small) | 50–80 nm | Small exosomes |
| Exosomes | 80–100 nm | Typical exosomes |
| Large Exosomes | 100–120 nm | Large exosomes |
| Microvesicles (small) | 120–150 nm | Small microvesicles |
| Microvesicles | 150–200 nm | Standard microvesicles |
| Large particles | 200+ nm | Large EVs / debris |

Each category shows percentage and color-coded bar.

---

### 5.5 Position Analysis

**File:** `components/nta/position-analysis.tsx`

**Component:** `PositionAnalysis({ results })`

For 11-position uniformity measurements, displays:
- Position-wise concentration or size data
- CV (coefficient of variation) to assess cell uniformity
- Pass/fail quality indicator

---

### 5.6 Temperature Settings

**File:** `components/nta/temperature-settings.tsx`

**Component:** `NTATemperatureSettings()`

**What it does:**
- Collapsible card that controls Stokes-Einstein correction parameters
- Settings:
  - **Apply Temperature Correction** toggle (on/off)
  - **Measurement Temperature** input (°C)
  - **Reference Temperature** input (default: 25°C)
  - **Media Type** selector (Water, PBS, DMEM, 10% FBS, etc.)
- Displays calculated correction factor and percentage change
- All settings stored in Zustand `ntaAnalysisSettings`

---

### 5.7 Supplementary Metadata Table

**File:** `components/nta/supplementary-metadata-table.tsx`

**Component:** `SupplementaryMetadataTable({ results, sampleId? })`

Shows raw metadata from the NTA file in a table format:
- Instrument serial number
- Cell serial number
- Software version
- SOP used
- Laser wavelength
- Shutter, sensitivity settings
- Electrolyte, pH, conductivity
- Number of positions and traces

Fetches data from `GET /{sample_id}/nta/metadata` endpoint.

---

### 5.8 Best Practices Guide

**File:** `components/nta/best-practices-guide.tsx`

**Component:** `NTABestPracticesGuide()`

Collapsible panel providing guidance on:
- Optimal particle concentration ranges for ZetaView
- Temperature equilibration recommendations
- Sample dilution best practices
- ZetaView-specific settings (sensitivity, shutter, min brightness, frame rate)
- Common issues and their solutions

---

### 5.9 Charts

#### 5.9.1 Size Distribution Chart

**File:** `components/nta/charts/nta-size-distribution-chart.tsx`

**Component:** `NTASizeDistributionChart({ results, secondaryResults?, primaryLabel?, secondaryLabel? })`

- **Type:** Bar chart (Recharts `BarChart`)
- **X-axis:** Particle size (nm)
- **Y-axis:** Concentration (particles/mL) or normalized count
- Shows size distribution as a histogram
- Supports overlay of two datasets for comparison (primary + secondary)
- D10/D50/D90 reference lines (toggleable)
- Responsive, interactive tooltips

#### 5.9.2 Concentration Profile Chart

**File:** `components/nta/charts/concentration-profile-chart.tsx`

**Component:** `ConcentrationProfileChart({ results })`

- **Type:** Line chart
- Shows concentration across measurement positions
- Useful for evaluating measurement consistency
- Highlights positions with anomalous concentration

#### 5.9.3 EV Size Category Pie Chart

**File:** `components/nta/charts/ev-size-category-pie-chart.tsx`

**Component:** `EVSizeCategoryPieChart({ results })`

- **Type:** Pie chart (Recharts `PieChart`)
- Visualizes the proportion of particles in each EV size category
- Color-coded: green (small EVs), purple (exosomes), amber (large EVs), red (microvesicles)
- Shows percentage labels

#### 5.9.4 Temperature-Corrected Comparison

**File:** `components/nta/charts/temperature-corrected-comparison.tsx`

**Component:** `TemperatureCorrectedComparison({ results })`

- **Type:** Dual bar chart
- Compares raw vs temperature-corrected size distribution side-by-side
- Uses correction factor from NTA Analysis Settings (Zustand)
- Visualizes how temperature correction shifts the size distribution

---

## 6. State Management & API Client

### Zustand Store (`lib/store.ts`)

**NTA-Related Interfaces:**

```typescript
// Main NTA state
interface NTAAnalysisState {
  file: File | null              // Currently uploaded NTA file
  sampleId: string | null        // Sample ID from backend
  results: NTAResult | null      // Parsed NTA results
  isAnalyzing: boolean           // Upload/parse in progress
  error: string | null           // Error message
  experimentalConditions: ExperimentalConditions | null
  fileMetadata: FileMetadata | null  // Auto-extracted metadata
}

// Secondary NTA state (for overlay comparison)
interface SecondaryNTAAnalysisState {
  file: File | null
  sampleId: string | null
  results: NTAResult | null
  isAnalyzing: boolean
  error: string | null
}

// NTA Analysis Settings (temperature correction)
interface NTAAnalysisSettings {
  applyTemperatureCorrection: boolean  // Toggle correction on/off
  measurementTemp: number              // Current measurement temp (°C)
  referenceTemp: number                // Reference temp (default 25°C)
  mediaType: string                    // 'water' | 'pbs' | 'dmem' | etc.
  correctionFactor: number             // Calculated factor
  showPercentileLines: boolean         // Show D10/D50/D90 lines on charts
  binSize: number                      // Histogram bin size (nm)
  yAxisMode: "count" | "normalized"    // Y-axis display mode
}
```

**Store Actions (NTA-related):**
- `setNTAFile(file)` — Set the uploaded NTA file
- `setNTAResults(results)` — Store parsed results
- `setNTASampleId(id)` — Set sample ID
- `setNTAAnalyzing(bool)` — Toggle loading state
- `setNTAError(msg)` — Set error message
- `resetNTAAnalysis()` — Clear all NTA state
- `setNTAExperimentalConditions(conditions)` — Store experiment metadata
- `setNtaOverlayEnabled(bool)` — Toggle overlay comparison
- `setSecondaryNTAFile/Results/SampleId/Analyzing/Error(...)` — Secondary dataset controls
- `resetSecondaryNTAAnalysis()` — Clear secondary dataset
- `updateNtaAnalysisSettings(partial)` — Update temperature correction settings

---

### API Client (`lib/api-client.ts`)

**NTA-Related Methods:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `uploadNTA(file, metadata?)` | `POST /upload/nta` | Upload NTA text file with optional metadata |
| `uploadNtaPdf(file, linkedSampleId?)` | `POST /upload/nta-pdf` | Upload PDF report |
| `getSampleNTAResults(sampleId)` | `GET /samples/{id}/nta` | Fetch stored NTA results |
| `getSampleNTAMetadata(sampleId)` | `GET /samples/{id}/nta/metadata` | Fetch file metadata |
| `getSampleNTAValues(sampleId)` | `GET /samples/{id}/nta/values` | Fetch per-bin data |

**NTAResult TypeScript Interface:**

```typescript
interface NTAResult {
  id: number
  mean_size_nm?: number
  median_size_nm?: number
  d10_nm?: number
  d50_nm?: number
  d90_nm?: number
  concentration_particles_ml?: number
  temperature_celsius?: number
  ph?: number
  total_particles?: number
  bin_50_80nm_pct?: number
  bin_80_100nm_pct?: number
  bin_100_120nm_pct?: number
  bin_120_150nm_pct?: number
  bin_150_200nm_pct?: number
  bin_200_plus_pct?: number
  size_distribution?: Array<{ size: number; count?: number; concentration?: number }>
  size_statistics?: { d10: number; d50: number; d90: number; mean: number; std: number }
  pdf_data?: {
    original_concentration: number | null
    dilution_factor: number | null
    true_particle_population: number | null
    mode_size_nm: number | null
    pdf_file_name: string | null
    extraction_successful: boolean
  }
}
```

---

### Hook (`hooks/use-api.ts`)

NTA-related functions exposed:
- `uploadNTA(file, metadata?)` — Calls `apiClient.uploadNTA()`, updates Zustand store
- `uploadNtaPdf(file, sampleId?)` — Calls `apiClient.uploadNtaPdf()`
- `openSampleInTab(sampleId)` — Opens a sample's NTA results in the NTA tab

---

## 7. Data Flow — End to End

```
User drops NTA file in browser
        │
        ▼
  NTATab (nta-tab.tsx)
  ├─ Sets file in Zustand state
  ├─ Calls useApi().uploadNTA(file, metadata)
  │       │
  │       ▼
  │  api-client.ts → POST /upload/nta (FormData)
  │       │
  │       ▼
  │  upload.py endpoint:
  │  ├─ Validates file extension
  │  ├─ Saves to data/uploads/{timestamp}_{filename}
  │  ├─ Creates NTAParser(file_path)
  │  │   ├─ parser.validate()
  │  │   ├─ parser.parse() → DataFrame
  │  │   └─ Detects size/prof/11pos type
  │  ├─ Calculates weighted D10, D50, D90, mean, std
  │  ├─ Calculates size bin percentages
  │  ├─ Creates Sample record in DB
  │  ├─ Creates NTAResult record in DB
  │  ├─ Creates ProcessingJob record
  │  ├─ Generates quality alerts
  │  ├─ Extracts file metadata
  │  └─ Returns JSON response with nta_results + file_metadata
  │       │
  │       ▼
  │  useApi hook:
  │  ├─ Stores results in Zustand (setNTAResults)
  │  ├─ Stores sampleId, fileMetadata
  │  └─ Shows toast notification
  │       │
  │       ▼
  └─ NTATab detects results → renders NTAAnalysisResults
        │
        ├─ NTAStatisticsCards (mean, median, D10, D90, concentration)
        ├─ NTASizeDistributionChart (histogram)
        ├─ EVSizeCategoryPieChart (pie chart of size bins)
        ├─ NTASizeDistributionBreakdown (table of bin percentages)
        ├─ ConcentrationProfileChart (concentration profile)
        ├─ PositionAnalysis (11-position data)
        ├─ TemperatureCorrectedComparison (raw vs corrected)
        └─ SupplementaryMetadataTable (fetches /nta/metadata)
```

---

## 8. Cross-Validation with FCS

The platform supports comparing NTA and FCS size distributions for cross-validation:

**Endpoint:** `GET /samples/{fcs_id}/cross-validate/{nta_id}`

**What it does:**
1. Loads FCS-derived sizes (from Mie scattering calculations)
2. Loads NTA sizes (from text file parsing)
3. Creates normalized histograms for both
4. Calculates:
   - Pearson correlation coefficient
   - KS (Kolmogorov-Smirnov) statistic
   - Mean size difference
   - Overlapping coefficient
5. Returns side-by-side comparison data for visualization

**Frontend:** Cross-validation is accessed through the "Cross-Compare" tab in the application.

---

## 9. File Summary Table

| File | Location | Lines | Purpose |
|------|----------|-------|---------|
| `nta_parser.py` | `backend/src/parsers/` | 609 | Parse ZetaView .txt/.csv files |
| `nta_pdf_parser.py` | `backend/src/parsers/` | 413 | Parse ZetaView PDF reports |
| `nta_corrections.py` | `backend/src/physics/` | 679 | Stokes-Einstein corrections |
| `models.py` (NTAResult) | `backend/src/database/` | ~60 | Database model |
| `upload.py` (NTA endpoints) | `backend/src/api/routers/` | ~530 | Upload API endpoints |
| `samples.py` (NTA endpoints) | `backend/src/api/routers/` | ~380 | Query API endpoints |
| `nta-tab.tsx` | `components/nta/` | 425 | Upload UI |
| `nta-analysis-results.tsx` | `components/nta/` | 672 | Results container |
| `statistics-cards.tsx` | `components/nta/` | ~120 | Key metric cards |
| `size-distribution-breakdown.tsx` | `components/nta/` | ~150 | Size bin table |
| `position-analysis.tsx` | `components/nta/` | ~100 | 11-position view |
| `temperature-settings.tsx` | `components/nta/` | ~160 | Correction controls |
| `supplementary-metadata-table.tsx` | `components/nta/` | ~150 | Metadata display |
| `best-practices-guide.tsx` | `components/nta/` | ~120 | Usage guide |
| `nta-size-distribution-chart.tsx` | `components/nta/charts/` | ~200 | Size histogram |
| `concentration-profile-chart.tsx` | `components/nta/charts/` | ~150 | Profile chart |
| `ev-size-category-pie-chart.tsx` | `components/nta/charts/` | ~130 | Pie chart |
| `temperature-corrected-comparison.tsx` | `components/nta/charts/` | ~200 | Raw vs corrected |
| `store.ts` (NTA state) | `lib/` | ~100 | Zustand state management |
| `api-client.ts` (NTA methods) | `lib/` | ~120 | HTTP client methods |
| `use-api.ts` (NTA hooks) | `hooks/` | ~50 | React hooks |
| **Total** | | **~4,500+** | |

---

## 10. How to Run the Tool

### Running the NTA Analysis

1. **Start the backend** (`python run_api.py` or `.\start.ps1`)
2. **Start the frontend** (`pnpm dev` or `.\start.ps1`)
3. **Open the browser** at http://localhost:3000
4. **Navigate to the NTA tab** (click "NTA" in the sidebar)
5. **Configure temperature correction** (optional — expand the Temperature Settings card)
6. **Upload an NTA file** — drag and drop a ZetaView `.txt` file
7. **Fill in metadata** — treatment, temperature, operator
8. **Click "Upload & Analyze"**
9. **View results** — charts, statistics, and metadata are displayed
10. **Optionally upload PDF** — for concentration/dilution data
11. **Export** — use the export dropdown for Markdown, Excel, PDF, or Parquet

### Running the Backend Only (for API Testing)

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python run_api.py
```

Then use the Swagger UI at http://localhost:8000/docs to test endpoints directly.

### Running as Desktop Application

```powershell
cd packaging
.\build.ps1
# Produces dist/BioVaram/ folder with standalone EXE
```

---

## 11. Troubleshooting

| Issue | Solution |
|-------|---------|
| **"Backend Offline" alert** | Start the backend: `cd backend; .\venv\Scripts\Activate.ps1; python run_api.py` |
| **PDF parsing disabled** | Install pdfplumber: `pip install pdfplumber` |
| **No size data found** | Ensure file is a ZetaView format `.txt` with "Size Distribution" section |
| **NTA file validation warning** | File may still parse — this is a non-fatal warning |
| **Database error during upload** | The system auto-retries. Check `data/` directory exists |
| **Temperature correction not applied** | Ensure "Apply Temperature Correction" is toggled on in settings |
| **Wrong correction factor** | Check measurement temperature matches actual instrument temperature |
| **Cross-validation fails** | Both FCS and NTA samples must be uploaded first |
| **pnpm install fails** | Run `npm cache clean --force` then `pnpm install` |
| **Python import errors** | Ensure virtual environment is activated: `.\venv\Scripts\Activate.ps1` |
| **Port 8000 in use** | Run `netstat -ano | findstr :8000` and kill the process |

---

*This document covers all NTA-related files, their code, architecture, setup, and usage for the BioVaram EV Analysis Platform. For questions, contact the CRMIT development team.*
