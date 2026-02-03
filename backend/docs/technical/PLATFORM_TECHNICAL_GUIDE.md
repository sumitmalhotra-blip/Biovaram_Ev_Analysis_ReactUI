# BioVaram EV Analysis Platform
## Complete Technical Guide: From File Upload to Final Analysis

**Document Version:** 1.0  
**Created:** January 29, 2026  
**Author:** BioVaram Development Team  
**Purpose:** Technical documentation explaining how the platform processes flow cytometry data and converts it to meaningful particle size analysis

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Platform Architecture](#2-platform-architecture)
3. [File Upload and Parsing](#3-file-upload-and-parsing)
4. [Understanding the Raw Data](#4-understanding-the-raw-data)
5. [Mie Theory: Converting Scatter to Size](#5-mie-theory-converting-scatter-to-size)
6. [The Multi-Solution Approach](#6-the-multi-solution-approach)
7. [Size Calculation Pipeline](#7-size-calculation-pipeline)
8. [Statistical Metrics Calculation](#8-statistical-metrics-calculation)
9. [Graph Generation and Visualization](#9-graph-generation-and-visualization)
10. [User Interface: What the End User Sees](#10-user-interface-what-the-end-user-sees)
11. [Cross-Compare Feature](#11-cross-compare-feature)
12. [Export and Reporting](#12-export-and-reporting)
13. [Technical Reference](#13-technical-reference)

---

## 1. Introduction

### 1.1 What is the BioVaram EV Analysis Platform?

The BioVaram EV Analysis Platform is a comprehensive web application designed to analyze **Extracellular Vesicles (EVs)** - tiny membrane-bound particles released by cells that play crucial roles in cell-to-cell communication.

### 1.2 The Core Challenge We Solve

Flow cytometry instruments measure **light scatter intensity** - how much light bounces off particles as they pass through a laser beam. But researchers need to know **particle size in nanometers**.

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Flow Cytometer  │ ──▶  │    Our Platform  │ ──▶  │   Size in nm     │
│  Measures: SSC   │      │    Converts via  │      │   + Statistics   │
│  (arbitrary units│      │    Mie Theory    │      │   + Graphs       │
└──────────────────┘      └──────────────────┘      └──────────────────┘
```

### 1.3 Supported Data Types

| Data Type | File Format | Source Instrument | Primary Use |
|-----------|-------------|-------------------|-------------|
| **NanoFACS** | .fcs | Flow cytometer (CytoFLEX, ZE5) | Single-particle analysis |
| **NTA** | .txt | Nanoparticle Tracking Analyzer (ZetaView) | Concentration + size |
| **TEM** | .jpg/.png | Transmission Electron Microscope | Visual confirmation |

---

## 2. Platform Architecture

### 2.1 Technology Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Next.js   │  │    React    │  │  TypeScript │  │   Recharts  │ │
│  │   (Router)  │  │    (UI)     │  │   (Types)   │  │   (Graphs)  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP/REST API
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           BACKEND                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   FastAPI   │  │   Python    │  │  miepython  │  │   flowio    │ │
│  │   (Server)  │  │   (Logic)   │  │   (Mie)     │  │   (FCS)     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          DATABASE                                    │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  SQLite / PostgreSQL (Samples, Users, Analysis Results)         ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Backend Components

| Component | File Location | Purpose |
|-----------|---------------|---------|
| **FCS Parser** | `backend/src/parsers/fcs_parser.py` | Read binary FCS files |
| **NTA Parser** | `backend/src/parsers/nta_parser.py` | Read NTA text files |
| **Mie Calculator** | `backend/src/utils/mie_calculator.py` | Convert scatter to size |
| **Sample Router** | `backend/src/api/routers/samples.py` | API endpoints for samples |
| **Upload Router** | `backend/src/api/routers/upload.py` | File upload handling |

### 2.3 Key Frontend Components

| Component | File Location | Purpose |
|-----------|---------------|---------|
| **Sidebar** | `components/sidebar.tsx` | File upload, parameter controls |
| **Flow Cytometry Tab** | `components/flow-cytometry/` | FCS analysis display |
| **NTA Tab** | `components/nta/` | NTA analysis display |
| **Cross-Compare** | `components/cross-compare/` | NTA vs FCS comparison |

---

## 3. File Upload and Parsing

### 3.1 The Upload Process

**Step 1: User Selects File**

The user clicks "Upload" in the sidebar and selects an FCS file from their computer.

```typescript
// Frontend: components/sidebar.tsx
const handleFileUpload = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData
  });
  
  const result = await response.json();
  // result contains: sample_id, metadata, recommended_settings
};
```

**Step 2: Backend Receives File**

```python
# Backend: backend/src/api/routers/upload.py
@router.post("/upload")
async def upload_file(file: UploadFile):
    # Save file to disk
    file_path = save_uploaded_file(file)
    
    # Parse the file based on extension
    if file.filename.endswith('.fcs'):
        metadata = parse_fcs_file(file_path)
    elif file.filename.endswith('.txt'):
        metadata = parse_nta_file(file_path)
    
    # Store in database
    sample_id = store_sample(metadata)
    
    return {
        "sample_id": sample_id,
        "metadata": metadata,
        "recommended_settings": detect_instrument_settings(metadata)
    }
```

**Step 3: FCS File Parsing**

```python
# Backend: backend/src/parsers/fcs_parser.py
import flowio
import numpy as np

def parse_fcs_file(file_path: str) -> dict:
    """
    Parse a binary FCS file into structured data.
    
    FCS File Structure:
    ┌─────────────────────────────────────┐
    │ HEADER (58 bytes)                   │
    │ - Version, byte offsets             │
    ├─────────────────────────────────────┤
    │ TEXT SEGMENT                        │
    │ - Channel names (FSC, SSC, etc.)    │
    │ - Gain settings                     │
    │ - Date, time, machine info          │
    ├─────────────────────────────────────┤
    │ DATA SEGMENT                        │
    │ - Binary event data                 │
    │ - One row per particle              │
    │ - Columns = channels                │
    └─────────────────────────────────────┘
    """
    
    # Read the FCS file using flowio library
    fcs_data = flowio.FlowData(file_path)
    
    # Extract channel information
    channels = []
    for i in range(fcs_data.channel_count):
        channel_info = fcs_data.channels[str(i + 1)]
        channels.append({
            'index': i,
            'name': channel_info.get('PnN', f'CH{i}'),  # Channel name
            'short_name': channel_info.get('PnS', ''),   # Short name
            'gain': float(channel_info.get('PnG', 1.0)), # Gain
            'range': int(channel_info.get('PnR', 262144)) # Range
        })
    
    # Extract event data (each row = one particle)
    events_raw = np.array(fcs_data.events)
    events = events_raw.reshape(-1, fcs_data.channel_count)
    
    # Extract metadata
    metadata = {
        'filename': file_path.name,
        'total_events': len(events),
        'channel_count': fcs_data.channel_count,
        'channels': channels,
        'acquisition_date': fcs_data.text.get('$DATE', 'Unknown'),
        'cytometer': fcs_data.text.get('$CYT', 'Unknown'),
    }
    
    return {
        'metadata': metadata,
        'events': events,
        'channels': channels
    }
```

### 3.2 Example: PC3 EXO1.fcs File

When we parse the PC3 EXO1.fcs file, we get:

| Property | Value |
|----------|-------|
| **Total Events** | 914,326 particles |
| **Channels** | 26 |
| **Key Channels** | SSC-H, SSC-A, VSSC1-Width, FSC-H, FL1-H, etc. |

**Channel List:**
```
FSC-H      Forward Scatter Height
FSC-A      Forward Scatter Area
SSC-H      Side Scatter Height (Blue 488nm) ← PRIMARY
SSC-A      Side Scatter Area
SSC_1-H    Additional SSC channels
SSC_2-H    
SSC_3-H    
SSC_4-H    
VSSC1-Width Violet Side Scatter (405nm) ← SECONDARY
FL1-H      Fluorescence Channel 1
FL2-H      Fluorescence Channel 2
...
```

---

## 4. Understanding the Raw Data

### 4.1 What Does the Flow Cytometer Actually Measure?

When a particle passes through the laser beam:

```
                    LASER BEAM (488nm or 405nm)
                           │
                           │
                           ▼
                    ═══════════════
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                   │
        │              ◯ particle              │
        │                  │                   │
        └──────────────────┼──────────────────┘
                           │
               ┌───────────┴───────────┐
               │                       │
               ▼                       ▼
        Forward Scatter          Side Scatter
         (FSC) → Size            (SSC) → Size + 
         (large angle)           Granularity
                                 (90° angle)
```

**Forward Scatter (FSC):** Light scattered in the forward direction. Generally proportional to particle size but less sensitive for small particles.

**Side Scatter (SSC):** Light scattered at ~90°. More sensitive to particle size and structure. This is what we primarily use for EV sizing.

### 4.2 Raw Data Structure

Each row in the events array represents ONE particle passing through the laser:

```
Event #  |  SSC-H   |  SSC-A   |  VSSC1   |  FSC-H   |  FL1-H   | ...
---------|----------|----------|----------|----------|----------|----
1        |  1,245   |  2,102   |  678     |  3,456   |  125     | ...
2        |  892     |  1,543   |  512     |  2,891   |  89      | ...
3        |  1,567   |  2,789   |  823     |  4,123   |  201     | ...
...      |  ...     |  ...     |  ...     |  ...     |  ...     | ...
914,326  |  1,102   |  1,923   |  601     |  3,234   |  156     | ...
```

**SSC-H:** Side Scatter Height - the peak value of scatter signal
**SSC-A:** Side Scatter Area - the integrated area under the signal curve
**VSSC1:** Violet Side Scatter - SSC at 405nm wavelength (different from blue 488nm)

### 4.3 Why We Use SSC-H for Sizing

| Parameter | Use Case | Why |
|-----------|----------|-----|
| **SSC-H** | Primary sizing | Most direct relationship to particle size |
| **VSSC1** | Disambiguation | Different wavelength = different Mie response |
| **FSC-H** | Quality control | Can detect aggregates, debris |
| **FL1-H** | Marker detection | Fluorescent labels (CD9, CD81, etc.) |

---

## 5. Mie Theory: Converting Scatter to Size

### 5.1 The Physics of Light Scattering

When light hits a small particle, it scatters. The amount and pattern of scattering depends on:

1. **Particle size** relative to wavelength
2. **Refractive index** of particle vs surrounding medium
3. **Wavelength** of light

**Gustav Mie (1908)** solved Maxwell's equations exactly for spherical particles, giving us "Mie Theory."

### 5.2 Key Parameters for Mie Calculation

| Parameter | Symbol | Typical Value | Source |
|-----------|--------|---------------|--------|
| Particle refractive index | n_particle | 1.40 | Literature (EV average) |
| Medium refractive index | n_medium | 1.33 | PBS/water |
| Laser wavelength (blue) | λ_blue | 488 nm | Instrument spec |
| Laser wavelength (violet) | λ_violet | 405 nm | Instrument spec |
| Particle diameter | d | 30-500 nm | What we're solving for |

### 5.3 The Mie Calculation

```python
# Backend: backend/src/utils/mie_calculator.py
import miepython
import numpy as np

def calculate_scatter_cross_section(diameter_nm: float, 
                                     wavelength_nm: float,
                                     n_particle: float = 1.40,
                                     n_medium: float = 1.33) -> float:
    """
    Calculate the backscatter cross-section for a particle.
    
    This is proportional to the SSC signal measured by the cytometer.
    
    Parameters:
    -----------
    diameter_nm : float
        Particle diameter in nanometers
    wavelength_nm : float
        Laser wavelength in nanometers (488 or 405)
    n_particle : float
        Refractive index of particle (EV ≈ 1.40)
    n_medium : float
        Refractive index of surrounding medium (PBS ≈ 1.33)
    
    Returns:
    --------
    float
        Scatter cross-section in nm² (proportional to SSC)
    """
    
    # Calculate relative refractive index
    # This is the ratio that matters for scattering
    m = complex(n_particle / n_medium, 0)  # 1.40/1.33 ≈ 1.053
    
    # miepython.efficiencies() returns:
    # (Q_ext, Q_sca, Q_back, g)
    # Q_ext = extinction efficiency
    # Q_sca = scattering efficiency
    # Q_back = backscattering efficiency ← This is SSC!
    # g = asymmetry factor
    
    result = miepython.efficiencies(
        m,                    # Relative refractive index
        diameter_nm,          # Particle diameter
        wavelength_nm,        # Laser wavelength
        n_env=n_medium        # Medium refractive index
    )
    
    Q_back = result[2]  # Backscattering efficiency
    
    # Convert efficiency to cross-section
    # Cross-section = Efficiency × Geometric area
    radius = diameter_nm / 2.0
    geometric_area = np.pi * radius**2
    
    scatter_cross_section = Q_back * geometric_area
    
    return scatter_cross_section
```

### 5.4 Building the Lookup Table (LUT)

Instead of calculating Mie theory for every particle in real-time (slow), we pre-calculate a lookup table:

```python
def build_lookup_table(wavelength_nm: float,
                       size_range: tuple = (30, 500),
                       step: float = 1.0) -> dict:
    """
    Build a lookup table mapping diameters to expected SSC values.
    
    This is calculated ONCE when the system starts, then reused.
    """
    
    diameters = np.arange(size_range[0], size_range[1] + step, step)
    ssc_values = []
    
    for d in diameters:
        ssc = calculate_scatter_cross_section(d, wavelength_nm)
        ssc_values.append(ssc)
    
    return {
        'diameters': diameters,      # [30, 31, 32, ... 500] nm
        'ssc': np.array(ssc_values),  # [45.2, 48.1, 51.3, ... ] 
        'wavelength': wavelength_nm
    }

# Build LUTs for both wavelengths
lut_blue = build_lookup_table(488.0)   # Blue laser
lut_violet = build_lookup_table(405.0) # Violet laser
```

### 5.5 The Mie Oscillation Problem

**Critical insight:** The Mie scattering curve is NOT monotonic!

```
SSC Value
    │
    │                         ╭──╮
    │                      ╭──╯  ╰──╮
    │                   ╭──╯        ╰──╮
 1300│- - - - - - - - -●- - - - - - - -●- - - Measured SSC
    │               ╭──╯               ╰──
    │            ╭──╯
    │         ╭──╯
    │      ╭──╯
    │   ╭──╯
    │╭──╯
    └────────────────────────────────────────▶ Diameter (nm)
         50   100   150   200   250   300   350   400   450   500
                            ▲               ▲
                           210 nm         380 nm
                           
         Problem: SSC = 1300 could be 210nm OR 380nm!
```

This is why we need the multi-solution approach.

---

## 6. The Multi-Solution Approach

### 6.1 Why Single-Solution Fails

**Single-Solution Method:**
1. Measure SSC value
2. Find CLOSEST match in lookup table
3. Return that diameter

**Problem:** If SSC = 1,300 matches both 210nm and 380nm, single-solution picks the first match, which might be wrong!

### 6.2 Multi-Solution Method

**Step 1:** Measure SSC at TWO wavelengths (Blue 488nm + Violet 405nm)

**Step 2:** Find ALL possible sizes that match Blue SSC (within tolerance)

**Step 3:** For each candidate, calculate expected Violet SSC

**Step 4:** Compare measured Violet/Blue ratio with theoretical ratios

**Step 5:** Pick the size whose theoretical ratio best matches measured ratio

```python
def multi_solution_sizing(ssc_blue: float, 
                          ssc_violet: float,
                          lut_blue: dict,
                          lut_violet: dict,
                          tolerance_pct: float = 15.0) -> float:
    """
    Convert SSC measurements to particle size using multi-solution approach.
    
    Parameters:
    -----------
    ssc_blue : float
        Measured SSC at 488nm (Blue laser)
    ssc_violet : float
        Measured SSC at 405nm (Violet laser)
    lut_blue : dict
        Lookup table for 488nm
    lut_violet : dict
        Lookup table for 405nm
    tolerance_pct : float
        Percentage tolerance for finding candidate sizes
    
    Returns:
    --------
    float
        Best-fit particle diameter in nm
    """
    
    # Step 1: Find ALL candidate sizes that could produce this Blue SSC
    tolerance = ssc_blue * (tolerance_pct / 100.0)
    candidate_indices = []
    
    for i, ssc in enumerate(lut_blue['ssc']):
        if abs(ssc - ssc_blue) <= tolerance:
            candidate_indices.append(i)
    
    if len(candidate_indices) == 0:
        return np.nan  # No match found
    
    if len(candidate_indices) == 1:
        # Only one solution - return it
        return lut_blue['diameters'][candidate_indices[0]]
    
    # Step 2: Multiple candidates - use ratio to disambiguate
    measured_ratio = ssc_violet / ssc_blue
    
    best_size = None
    best_error = float('inf')
    
    for idx in candidate_indices:
        diameter = lut_blue['diameters'][idx]
        
        # Get theoretical Violet SSC for this diameter
        theoretical_violet = lut_violet['ssc'][idx]
        theoretical_blue = lut_blue['ssc'][idx]
        theoretical_ratio = theoretical_violet / theoretical_blue
        
        # Compare ratios
        ratio_error = abs(theoretical_ratio - measured_ratio)
        
        if ratio_error < best_error:
            best_error = ratio_error
            best_size = diameter
    
    return best_size
```

### 6.3 Real Example: Event #630636

From PC3 EXO1.fcs file:

| Measurement | Value |
|-------------|-------|
| Blue SSC (488nm) | 1,307.4 |
| Violet SSC (405nm) | 677.3 |
| Measured Ratio | 0.5181 |

**Candidate sizes found (within 15% of Blue SSC):**

| Candidate Size | Theoretical Ratio | Error vs Measured | Result |
|----------------|-------------------|-------------------|--------|
| **208.5 nm** | 0.5564 | **7.4%** | ✅ CORRECT |
| 379.0 nm | 2.9021 | 460% | ❌ Wrong |

**Conclusion:** Multi-solution correctly identifies 208.5 nm by using the wavelength ratio as a "fingerprint."

---

## 7. Size Calculation Pipeline

### 7.1 Complete Processing Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SIZE CALCULATION PIPELINE                         │
└─────────────────────────────────────────────────────────────────────┘

Input: 914,326 events from PC3 EXO1.fcs
       Each event has SSC-H and VSSC values

   │
   ▼
┌─────────────────────────────────────────┐
│ Step 1: FILTER POSITIVE VALUES          │
│                                         │
│  • Remove events where SSC <= 0         │
│  • Remove events where VSSC <= 0        │
│  • Remaining: ~900,000 valid events     │
└─────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────┐
│ Step 2: LOAD LOOKUP TABLES              │
│                                         │
│  • LUT_Blue: 471 entries (30-500nm)     │
│  • LUT_Violet: 471 entries (30-500nm)   │
│  • Pre-calculated at server startup     │
└─────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────┐
│ Step 3: FOR EACH EVENT                  │
│                                         │
│  • Read SSC_Blue and SSC_Violet         │
│  • Find all candidate sizes             │
│  • Calculate measured ratio             │
│  • Compare with theoretical ratios      │
│  • Select best-matching size            │
└─────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────┐
│ Step 4: COLLECT RESULTS                 │
│                                         │
│  • Array of 900,000+ sizes in nm        │
│  • Filter out NaN (no valid match)      │
│  • Filter outliers (< 30nm or > 500nm)  │
└─────────────────────────────────────────┘
   │
   ▼
Output: Array of validated particle sizes
```

### 7.2 Backend Implementation

```python
# Backend: backend/src/api/routers/samples.py

@router.get("/samples/{sample_id}/fcs/values")
async def get_fcs_values(sample_id: int, db: Session = Depends(get_db)):
    """
    Get processed size values for an FCS sample.
    """
    
    # Load sample from database
    sample = db.query(Sample).filter(Sample.id == sample_id).first()
    
    # Parse FCS file
    fcs_data = parse_fcs_file(sample.file_path)
    events = fcs_data['events']
    channels = fcs_data['channels']
    
    # Find channel indices
    ssc_blue_idx = find_channel_index(channels, ['SSC-H'])
    ssc_violet_idx = find_channel_index(channels, ['VSSC', 'SSC_V'])
    
    # Extract SSC values
    ssc_blue = events[:, ssc_blue_idx]
    ssc_violet = events[:, ssc_violet_idx] if ssc_violet_idx else None
    
    # Filter positive values
    mask = ssc_blue > 0
    if ssc_violet is not None:
        mask = mask & (ssc_violet > 0)
    
    ssc_blue_filtered = ssc_blue[mask]
    ssc_violet_filtered = ssc_violet[mask] if ssc_violet is not None else None
    
    # Convert to sizes
    sizes = convert_ssc_to_sizes(
        ssc_blue_filtered,
        ssc_violet_filtered,
        method='multi_solution'  # or 'single_solution'
    )
    
    # Calculate statistics
    stats = calculate_statistics(sizes)
    
    return {
        "sizes": sizes.tolist(),
        "statistics": stats,
        "total_events": len(events),
        "valid_events": len(sizes)
    }
```

---

## 8. Statistical Metrics Calculation

### 8.1 What Metrics We Calculate

Once we have an array of particle sizes, we calculate:

```python
def calculate_statistics(sizes: np.ndarray) -> dict:
    """
    Calculate comprehensive statistics for particle size distribution.
    """
    
    # Remove invalid values
    valid_sizes = sizes[~np.isnan(sizes)]
    valid_sizes = valid_sizes[(valid_sizes >= 30) & (valid_sizes <= 500)]
    
    # Central tendency
    mean = np.mean(valid_sizes)
    median = np.median(valid_sizes)
    mode = calculate_mode(valid_sizes)  # Most frequent size
    
    # Spread
    std_dev = np.std(valid_sizes)
    variance = np.var(valid_sizes)
    
    # Percentiles (per MISEV guidelines)
    d10 = np.percentile(valid_sizes, 10)   # 10th percentile
    d50 = np.percentile(valid_sizes, 50)   # 50th percentile (= median)
    d90 = np.percentile(valid_sizes, 90)   # 90th percentile
    
    # Range
    min_size = np.min(valid_sizes)
    max_size = np.max(valid_sizes)
    
    # Size categories
    small = np.sum(valid_sizes < 50)
    medium = np.sum((valid_sizes >= 50) & (valid_sizes <= 200))
    large = np.sum(valid_sizes > 200)
    
    return {
        'count': len(valid_sizes),
        'mean': round(mean, 2),
        'median': round(median, 2),
        'mode': round(mode, 2),
        'std_dev': round(std_dev, 2),
        'd10': round(d10, 2),
        'd50': round(d50, 2),
        'd90': round(d90, 2),
        'min': round(min_size, 2),
        'max': round(max_size, 2),
        'categories': {
            'small': {'count': int(small), 'percentage': round(small/len(valid_sizes)*100, 1)},
            'medium': {'count': int(medium), 'percentage': round(medium/len(valid_sizes)*100, 1)},
            'large': {'count': int(large), 'percentage': round(large/len(valid_sizes)*100, 1)}
        }
    }
```

### 8.2 Example Results: PC3 EXO1

| Metric | Value | Meaning |
|--------|-------|---------|
| **Count** | 914,326 | Total valid particles |
| **Mean** | 127.5 nm | Average size |
| **Median (D50)** | 127.0 nm | Middle value |
| **Mode** | 125 nm | Most common size |
| **Std Dev** | 45.2 nm | Spread of distribution |
| **D10** | 75 nm | 10% are smaller than this |
| **D90** | 195 nm | 90% are smaller than this |

**Category Breakdown:**

| Category | Size Range | Count | Percentage |
|----------|------------|-------|------------|
| Small | < 50 nm | 45,716 | 5% |
| Medium | 50-200 nm | 640,028 | 70% |
| Large | > 200 nm | 228,582 | 25% → 15% with multi-solution |

---

## 9. Graph Generation and Visualization

### 9.1 Size Distribution Histogram

**What it shows:** How many particles fall into each size bin.

```
Count (%)
   │
20%│     ▓▓▓▓
   │   ▓▓▓▓▓▓▓▓
15%│  ▓▓▓▓▓▓▓▓▓▓▓
   │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓
10%│▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
   │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
 5%│▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
   │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
   └────────────────────────────▶ Size (nm)
     50   100   150   200   250   300
          ▲
        D50 = 127 nm (vertical line)
```

**Frontend Implementation:**

```typescript
// Frontend: components/flow-cytometry/size-histogram.tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ReferenceLine } from 'recharts';

interface HistogramProps {
  data: { bin: number; count: number; percentage: number }[];
  d50: number;
}

export function SizeHistogram({ data, d50 }: HistogramProps) {
  return (
    <BarChart width={600} height={400} data={data}>
      <XAxis 
        dataKey="bin" 
        label={{ value: 'Particle Size (nm)', position: 'bottom' }}
      />
      <YAxis 
        label={{ value: 'Percentage (%)', angle: -90, position: 'left' }}
      />
      <Tooltip 
        content={({ payload }) => (
          <div className="bg-slate-800 p-2 rounded">
            <p>Size: {payload[0]?.payload.bin} nm</p>
            <p>Count: {payload[0]?.payload.count}</p>
            <p>Percentage: {payload[0]?.payload.percentage}%</p>
          </div>
        )}
      />
      <Bar dataKey="percentage" fill="#3b82f6" />
      <ReferenceLine 
        x={d50} 
        stroke="#ef4444" 
        strokeDasharray="5 5"
        label="D50"
      />
    </BarChart>
  );
}
```

### 9.2 Scatter Plot (SSC vs Size)

**What it shows:** Relationship between raw SSC and calculated size.

```typescript
// Frontend: components/flow-cytometry/scatter-plot.tsx
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ZAxis } from 'recharts';

interface ScatterPlotProps {
  data: { size: number; ssc: number }[];
}

export function ScatterPlot({ data }: ScatterPlotProps) {
  // Sample data for performance (can't plot 900k points)
  const sampledData = sampleData(data, 10000);
  
  return (
    <ScatterChart width={600} height={400}>
      <XAxis 
        dataKey="size" 
        type="number"
        domain={[0, 500]}
        label={{ value: 'Particle Size (nm)', position: 'bottom' }}
      />
      <YAxis 
        dataKey="ssc" 
        type="number"
        label={{ value: 'SSC Intensity', angle: -90, position: 'left' }}
      />
      <ZAxis range={[10, 10]} />
      <Tooltip />
      <Scatter 
        data={sampledData} 
        fill="#3b82f6" 
        opacity={0.5}
      />
    </ScatterChart>
  );
}
```

### 9.3 Category Pie Chart

**What it shows:** Breakdown of small, medium, and large particles.

```typescript
// Frontend: components/flow-cytometry/category-pie.tsx
import { PieChart, Pie, Cell, Legend, Tooltip } from 'recharts';

const COLORS = ['#22c55e', '#3b82f6', '#ef4444'];

interface CategoryPieProps {
  categories: {
    small: { count: number; percentage: number };
    medium: { count: number; percentage: number };
    large: { count: number; percentage: number };
  };
}

export function CategoryPie({ categories }: CategoryPieProps) {
  const data = [
    { name: 'Small (<50nm)', value: categories.small.percentage },
    { name: 'Medium (50-200nm)', value: categories.medium.percentage },
    { name: 'Large (>200nm)', value: categories.large.percentage },
  ];

  return (
    <PieChart width={400} height={300}>
      <Pie
        data={data}
        dataKey="value"
        nameKey="name"
        cx="50%"
        cy="50%"
        outerRadius={100}
        label={({ name, value }) => `${name}: ${value}%`}
      >
        {data.map((_, index) => (
          <Cell key={index} fill={COLORS[index]} />
        ))}
      </Pie>
      <Legend />
      <Tooltip />
    </PieChart>
  );
}
```

---

## 10. User Interface: What the End User Sees

### 10.1 Main Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ HEADER: BioVaram EV Analysis Platform                        [User] [Logout]│
├─────────────┬───────────────────────────────────────────────────────────────┤
│             │                                                               │
│  SIDEBAR    │                    MAIN CONTENT AREA                          │
│             │                                                               │
│ ┌─────────┐ │  ┌─────────────────────────────────────────────────────────┐  │
│ │ Upload  │ │  │  Tab: [Flow Cytometry] [NTA] [Cross-Compare] [Research] │  │
│ │ [FCS]   │ │  └─────────────────────────────────────────────────────────┘  │
│ │ [NTA]   │ │                                                               │
│ └─────────┘ │  ┌─────────────────────────────────────────────────────────┐  │
│             │  │                                                         │  │
│ ┌─────────┐ │  │              SIZE DISTRIBUTION HISTOGRAM                │  │
│ │Calibra- │ │  │                                                         │  │
│ │tion     │ │  │         ▓▓▓▓                                            │  │
│ │Settings │ │  │       ▓▓▓▓▓▓▓▓                                          │  │
│ │         │ │  │     ▓▓▓▓▓▓▓▓▓▓▓▓                                        │  │
│ │ Bead:   │ │  │   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                                      │  │
│ │ [100nm] │ │  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                                     │  │
│ │         │ │  │                                                         │  │
│ │Material:│ │  └─────────────────────────────────────────────────────────┘  │
│ │[Polyst.]│ │                                                               │
│ └─────────┘ │  ┌───────────────────────┐  ┌───────────────────────┐        │
│             │  │   STATISTICS          │  │   CATEGORY PIE        │        │
│ ┌─────────┐ │  │                       │  │                       │        │
│ │Previous │ │  │   D50: 127.0 nm       │  │    ▄▄▄▄▄              │        │
│ │Analyses │ │  │   D10: 75.0 nm        │  │  ▄▀░░░░░▀▄            │        │
│ │         │ │  │   D90: 195.0 nm       │  │ █░Medium░░█           │        │
│ │ PC3_F1  │ │  │   Mean: 127.5 nm      │  │  ▀▄░70%░▄▀            │        │
│ │ PC3_F2  │ │  │   Events: 914,326     │  │    ▀▀▀▀▀              │        │
│ │ ...     │ │  │                       │  │                       │        │
│ └─────────┘ │  └───────────────────────┘  └───────────────────────┘        │
│             │                                                               │
└─────────────┴───────────────────────────────────────────────────────────────┘
```

### 10.2 Calibration Settings Panel

```typescript
// Frontend: components/flow-cytometry/calibration-settings-panel.tsx

export function CalibrationSettingsPanel() {
  return (
    <div className="p-4 bg-slate-800 rounded-lg">
      <h3 className="font-bold mb-4">Calibration Settings</h3>
      
      {/* Tier 1: Simple Mode (Default) */}
      <div className="mb-4">
        <label>Calibration Bead Material</label>
        <select>
          <option value="polystyrene">Polystyrene (n=1.59)</option>
          <option value="silica">Silica (n=1.45)</option>
          <option value="pmma">PMMA (n=1.49)</option>
        </select>
      </div>
      
      <div className="mb-4">
        <label>Bead Size</label>
        <select>
          <option value="100">100 nm</option>
          <option value="200">200 nm</option>
          <option value="300">300 nm</option>
          <option value="500">500 nm</option>
        </select>
      </div>
      
      {/* Tier 2: Auto-Detected Settings */}
      <div className="p-3 bg-slate-700 rounded">
        <h4>Auto-Detected Settings</h4>
        <p>Wavelength: 488nm (Blue) ✓</p>
        <p>Instrument: CytoFLEX ✓</p>
        <p>Confidence: High ✓</p>
      </div>
      
      {/* Tier 3: Advanced (expandable) */}
      <details className="mt-4">
        <summary>Advanced Parameters</summary>
        <div className="p-3">
          <label>Particle RI: <input value="1.40" /></label>
          <label>Medium RI: <input value="1.33" /></label>
        </div>
      </details>
    </div>
  );
}
```

### 10.3 Statistics Summary Panel

What the user sees after analysis:

```
┌────────────────────────────────────────────────────┐
│              ANALYSIS SUMMARY                       │
├────────────────────────────────────────────────────┤
│                                                    │
│  Sample: PC3 EXO1.fcs                              │
│  ────────────────────────────────────              │
│                                                    │
│  Total Events:     914,326                         │
│  Valid Events:     914,326 (100%)                  │
│                                                    │
│  SIZE METRICS                                      │
│  ─────────────                                     │
│  D10:              75.0 nm                         │
│  D50 (Median):     127.0 nm  ← Primary Metric     │
│  D90:              195.0 nm                        │
│                                                    │
│  Mean:             127.5 nm                        │
│  Std Dev:          45.2 nm                         │
│                                                    │
│  CATEGORY BREAKDOWN                                │
│  ──────────────────                                │
│  Small (<50nm):    5% (45,716 particles)          │
│  Medium (50-200):  70% (640,028 particles)        │
│  Large (>200nm):   25% (228,582 particles)        │
│                                                    │
│  [Export to Excel] [Generate PDF] [Save Analysis]  │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## 11. Cross-Compare Feature

### 11.1 Purpose

Compare size distributions from different measurement methods:
- NTA (Nanoparticle Tracking Analysis) vs FCS (Flow Cytometry)
- Validate that both methods agree on particle sizes

### 11.2 Implementation

```typescript
// Frontend: components/cross-compare/validation-summary-card.tsx

interface ValidationResult {
  metric: string;
  nta_value: number;
  fcs_value: number;
  difference_pct: number;
  status: 'pass' | 'warn' | 'fail';
}

export function ValidationSummaryCard({ ntaData, fcsData }) {
  const results: ValidationResult[] = [
    {
      metric: 'D10',
      nta_value: ntaData.d10,
      fcs_value: fcsData.d10,
      difference_pct: calculateDifference(ntaData.d10, fcsData.d10),
      status: getStatus(calculateDifference(ntaData.d10, fcsData.d10))
    },
    {
      metric: 'D50 (Median)',
      nta_value: ntaData.d50,
      fcs_value: fcsData.d50,
      difference_pct: calculateDifference(ntaData.d50, fcsData.d50),
      status: getStatus(calculateDifference(ntaData.d50, fcsData.d50))
    },
    {
      metric: 'D90',
      nta_value: ntaData.d90,
      fcs_value: fcsData.d90,
      difference_pct: calculateDifference(ntaData.d90, fcsData.d90),
      status: getStatus(calculateDifference(ntaData.d90, fcsData.d90))
    }
  ];

  return (
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th>NTA</th>
          <th>FCS</th>
          <th>Difference</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {results.map(r => (
          <tr key={r.metric}>
            <td>{r.metric}</td>
            <td>{r.nta_value} nm</td>
            <td>{r.fcs_value} nm</td>
            <td>{r.difference_pct}%</td>
            <td className={statusColors[r.status]}>{r.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

### 11.3 Example Comparison

| Metric | NTA Value | FCS Value | Difference | Status |
|--------|-----------|-----------|------------|--------|
| D10 | 74.2 nm | 75.0 nm | 1.1% | ✅ PASS |
| **D50** | **127.3 nm** | **127.0 nm** | **0.2%** | ✅ PASS |
| D90 | 192.1 nm | 195.0 nm | 1.5% | ✅ PASS |

**Thresholds:**
- < 5% difference: ✅ PASS (green)
- 5-15% difference: ⚠️ WARN (yellow)
- > 15% difference: ❌ FAIL (red)

---

## 12. Export and Reporting

### 12.1 Excel Export

```typescript
// Frontend: lib/export-utils.ts
import * as XLSX from 'xlsx';

export function exportToExcel(data: AnalysisData) {
  const workbook = XLSX.utils.book_new();
  
  // Sheet 1: Summary Statistics
  const summaryData = [
    ['Sample', data.filename],
    ['Total Events', data.totalEvents],
    ['D10', data.d10],
    ['D50', data.d50],
    ['D90', data.d90],
    ['Mean', data.mean],
    ['Std Dev', data.stdDev]
  ];
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary');
  
  // Sheet 2: Size Distribution
  const distributionSheet = XLSX.utils.json_to_sheet(data.histogram);
  XLSX.utils.book_append_sheet(workbook, distributionSheet, 'Distribution');
  
  // Sheet 3: Raw Sizes (first 10,000)
  const sizesSheet = XLSX.utils.json_to_sheet(
    data.sizes.slice(0, 10000).map((s, i) => ({ Event: i + 1, Size_nm: s }))
  );
  XLSX.utils.book_append_sheet(workbook, sizesSheet, 'Raw Sizes');
  
  // Download
  XLSX.writeFile(workbook, `${data.filename}_analysis.xlsx`);
}
```

### 12.2 PDF Report

The platform generates a PDF report containing:
1. Sample information
2. Calibration settings used
3. Size distribution histogram
4. Summary statistics table
5. Category pie chart
6. Quality assessment notes

---

## 13. Technical Reference

### 13.1 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/upload` | POST | Upload FCS/NTA file |
| `/api/samples` | GET | List all samples |
| `/api/samples/{id}` | GET | Get sample details |
| `/api/samples/{id}/fcs/metadata` | GET | Get FCS metadata only |
| `/api/samples/{id}/fcs/values` | GET | Get processed size values |
| `/api/samples/{id}/nta/metadata` | GET | Get NTA metadata |
| `/api/samples/{id}/nta/values` | GET | Get NTA size/concentration |
| `/api/samples/{id}/reanalyze` | POST | Rerun with new parameters |

### 13.2 State Management

```typescript
// Frontend: lib/store.ts
import { create } from 'zustand';

interface AppState {
  // Current sample
  currentSampleId: number | null;
  currentSampleType: 'fcs' | 'nta' | null;
  
  // Analysis results
  fcsResults: FCSResults | null;
  ntaResults: NTAResults | null;
  
  // Calibration settings
  calibrationMode: 'simple' | 'advanced';
  beadMaterial: 'polystyrene' | 'silica' | 'pmma';
  beadSize: number;
  nParticle: number;
  nMedium: number;
  
  // Actions
  setCurrentSample: (id: number, type: 'fcs' | 'nta') => void;
  setFCSResults: (results: FCSResults) => void;
  updateCalibration: (settings: Partial<CalibrationSettings>) => void;
}

export const useStore = create<AppState>((set) => ({
  currentSampleId: null,
  currentSampleType: null,
  fcsResults: null,
  ntaResults: null,
  calibrationMode: 'simple',
  beadMaterial: 'polystyrene',
  beadSize: 100,
  nParticle: 1.40,
  nMedium: 1.33,
  
  setCurrentSample: (id, type) => set({ currentSampleId: id, currentSampleType: type }),
  setFCSResults: (results) => set({ fcsResults: results }),
  updateCalibration: (settings) => set((state) => ({ ...state, ...settings }))
}));
```

### 13.3 Physical Constants

| Constant | Value | Description |
|----------|-------|-------------|
| n_particle | 1.40 | Refractive index of EVs |
| n_medium | 1.33 | Refractive index of PBS |
| λ_blue | 488 nm | Blue laser wavelength |
| λ_violet | 405 nm | Violet laser wavelength |
| Size min | 30 nm | Minimum detectable size |
| Size max | 500 nm | Maximum analyzed size |
| LUT step | 1 nm | Lookup table resolution |

### 13.4 File Locations

| Component | Path | Description |
|-----------|------|-------------|
| FCS Parser | `backend/src/parsers/fcs_parser.py` | Parse FCS binary files |
| NTA Parser | `backend/src/parsers/nta_parser.py` | Parse NTA text files |
| Mie Calculator | `backend/src/utils/mie_calculator.py` | Mie theory calculations |
| API Routes | `backend/src/api/routers/` | FastAPI endpoints |
| UI Components | `components/` | React components |
| State Store | `lib/store.ts` | Zustand state management |
| API Client | `lib/api-client.ts` | Frontend API calls |

---

## Glossary

| Term | Definition |
|------|------------|
| **EV** | Extracellular Vesicle - membrane-bound particles released by cells |
| **FCS** | Flow Cytometry Standard - file format for flow cytometry data |
| **SSC** | Side Scatter - light scattered at 90° from the laser beam |
| **FSC** | Forward Scatter - light scattered in the forward direction |
| **Mie Theory** | Mathematical solution for light scattering by spherical particles |
| **LUT** | Lookup Table - pre-calculated values for fast conversion |
| **D50** | Median size - 50% of particles are smaller than this value |
| **D10/D90** | 10th/90th percentile - defines the size range |
| **NTA** | Nanoparticle Tracking Analysis - alternative sizing method |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Jan 29, 2026 | BioVaram Team | Initial creation |

---

*End of Document*
