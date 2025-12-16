# 🔄 Standardized Data Format Strategy: Multi-Machine Integration

**Date:** November 13, 2025  
**Topic:** Should we standardize data from nanoFACS and NTA, or use different formats?

---

## 🎯 **Short Answer: YES - Create ONE Unified Format**

**You MUST create a standardized format that combines both machines' data!**

---

## 🤔 **Why This Question is Critical**

### **Your Current Situation:**

```
Machine 1: nanoFACS (CytoFLEX nano)
├── Output: FCS files (binary)
├── Data: 339K events × 26 parameters
├── Measures: Size, complexity, fluorescence markers
└── Purpose: Marker expression (CD81, CD9, CD63)

Machine 2: NTA (ZetaView)
├── Output: TXT files (text)
├── Data: Size distributions, concentrations
├── Measures: Particle size (nm), count (particles/mL)
└── Purpose: Size distribution, purity assessment
```

**Problem:** Two completely different data structures measuring the SAME samples!

---

## ❌ **Option 1: Keep Them Separate (BAD IDEA)**

### **If you DON'T standardize:**

```
Project Structure (Separate):
├── nanoFACS_data/
│   ├── events/*.parquet          # 26 parameters per event
│   ├── statistics/*.parquet      # nanoFACS-specific stats
│   └── metadata/*.csv            # nanoFACS metadata
│
└── NTA_data/
    ├── distributions/*.parquet   # Size distribution data
    ├── concentrations/*.parquet  # Particle counts
    └── metadata/*.csv            # NTA metadata
    
# Two parallel systems, no connection! ❌
```

### **Problems with Separate Approach:**

❌ **Cannot correlate results**
```python
# How do you compare these?
nanoFACS: "Sample L5+F10 has 85% CD81+ events"
NTA:      "Sample L5+F10 has mean size 120nm"

# They're the same sample but stored separately!
# You'd need to manually match them every time
```

❌ **Duplicate metadata**
```python
# Store same info twice:
nanoFACS metadata: sample_name, passage, fraction, date
NTA metadata:      sample_name, passage, fraction, date
# Same data, two places → inconsistencies!
```

❌ **Complex analysis**
```python
# To analyze one sample, load from TWO places:
fcs_data = load_nanofacs_data('L5+F10')
nta_data = load_nta_data('L5+F10')

# Then manually merge:
combined = merge_somehow(fcs_data, nta_data)  # How?!
```

❌ **ML nightmare**
```python
# Training ML model on BOTH measurements:
features_fcs = extract_features_nanofacs(fcs_data)  # 300 features
features_nta = extract_features_nta(nta_data)       # 50 features

# How to combine for training?
# Different sample IDs? Different timestamps?
# Matching nightmare! 😱
```

❌ **Duplicate work**
- Write two parsers
- Two storage systems
- Two APIs
- Two dashboards
- Two sets of documentation

---

## ✅ **Option 2: Unified Standardized Format (BEST APPROACH)**

### **Create ONE master format that combines both:**

```
Project Structure (Unified):
├── unified_data/
│   ├── samples/
│   │   ├── sample_metadata.parquet        # ← Master sample registry
│   │   └── experimental_conditions.parquet
│   │
│   ├── measurements/
│   │   ├── nanofacs/
│   │   │   ├── events/*.parquet           # Raw nanoFACS events
│   │   │   └── statistics/*.parquet       # Pre-calculated stats
│   │   │
│   │   └── nta/
│   │       ├── distributions/*.parquet    # Size distributions
│   │       └── summary/*.parquet          # Concentration, D50, etc.
│   │
│   └── integrated/
│       ├── combined_features.parquet      # ← Both machines, one file!
│       └── ml_ready_dataset.parquet       # ← Ready for ML training
│
# Everything linked by unique sample_id! ✅
```

---

## 🏗️ **Recommended Unified Data Model**

### **Core Concept: Three-Layer Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│              LAYER 1: SAMPLE REGISTRY (Master)              │
│                                                             │
│  sample_metadata.parquet                                    │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ sample_id | name      | passage | fraction | lot | ... │ │
│  │ S001      | L5+F10    | P2      | F10      | L5  | ... │ │
│  │ S002      | L5+F16    | P2      | F16      | L5  | ... │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ↓ Links to both machines via sample_id                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│         LAYER 2: MACHINE-SPECIFIC MEASUREMENTS              │
│                                                             │
│  nanoFACS Statistics:                                       │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ sample_id | mean_FSC | mean_SSC | pct_CD81+ | ...     │ │
│  │ S001      | 1250.5   | 890.3    | 85.2%     | ...     │ │
│  │ S002      | 1180.2   | 920.1    | 78.5%     | ...     │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  NTA Statistics:                                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ sample_id | D50_nm | conc_particles_ml | CV%  | ...   │ │
│  │ S001      | 120.5  | 2.5e11            | 12.3 | ...   │ │
│  │ S002      | 115.8  | 3.1e11            | 10.5 | ...   │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│            LAYER 3: INTEGRATED ANALYSIS                     │
│                                                             │
│  combined_features.parquet (ML-ready):                      │
│  ┌────────────────────────────────────────────────────────┐│
│  │ sample_id | mean_FSC | pct_CD81+ | D50_nm | conc | ... ││
│  │ S001      | 1250.5   | 85.2%     | 120.5  | 2.5e11| ...││
│  │ S002      | 1180.2   | 78.5%     | 115.8  | 3.1e11| ...││
│  └────────────────────────────────────────────────────────┘│
│                                                             │
│  ↑ All features from BOTH machines in ONE row per sample!  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 **Detailed Schema Design**

### **Schema 1: Sample Metadata (Master Registry)**

**UPDATED: Nov 13, 2025 - Baseline + Iterations Workflow**

**File:** `unified_data/samples/sample_metadata.parquet`

**Key Change:** System now supports **1 biological sample = 5-6 FCS files** (baseline + iterations)

```python
import pandas as pd

sample_metadata = pd.DataFrame({
    # === PRIMARY IDENTIFIERS (ENHANCED) ===
    'biological_sample_id': ['P5_F10', 'P5_F10', 'P5_F10', 'P5_F16', ...],  # NEW: Groups iterations
    'measurement_id': ['P5_F10_ISO', 'P5_F10_CD81_0.25ug', 'P5_F10_CD81_1ug', 'P5_F16_ISO', ...],  # NEW: Unique per file (PRIMARY KEY)
    'sample_name': ['Exo+ ISO', 'Exo+ 0.25ug CD81', 'Exo+ 1ug CD81', ...],  # Original filename
    
    # === BIOLOGICAL SAMPLE INFO ===
    'passage': ['P5', 'P5', 'P5', 'P5', ...],
    'fraction': ['F10', 'F10', 'F10', 'F16', ...],
    'lot_number': ['L5', 'L5', 'L5', 'L5', ...],
    'purification_method': ['SEC', 'SEC', 'SEC', 'Centrifugation', ...],
    'experiment_date': ['2025-10-09', '2025-10-09', '2025-10-09', ...],
    
    # === MEASUREMENT-SPECIFIC INFO (NEW) ===
    'antibody': ['ISO', 'CD81', 'CD81', 'ISO', ...],  # Target antibody
    'antibody_concentration_ug': [0, 0.25, 1.0, 0, ...],  # NEW: Numeric concentration
    'is_baseline': [True, False, False, True, ...],  # NEW: Baseline/control flag
    'baseline_measurement_id': ['P5_F10_ISO', 'P5_F10_ISO', 'P5_F10_ISO', 'P5_F16_ISO', ...],  # NEW: Links to baseline
    'iteration_number': [1, 2, 3, 1, ...],  # NEW: Sequence (1=baseline, 2-6=tests)
    'measurement_type': ['baseline', 'antibody_test', 'antibody_test', 'baseline', ...],  # NEW
    
    # === FILE PATHS (UPDATED FOR S3) ===
    'nanofacs_s3_path': ['s3://bucket/raw/P5_F10_ISO.fcs', 's3://bucket/raw/P5_F10_CD81_0.25ug.fcs', ...],  # NEW
    'nanofacs_local_path': ['/cache/P5_F10_ISO.fcs', None, ...],  # Local cache if exists
    'nta_s3_path': ['s3://bucket/nta/P5_F10.txt', None, ...],  # One NTA per biological sample
    'nta_local_path': ['/cache/P5_F10_nta.txt', None, ...],
    
    # === INSTRUMENT & ACQUISITION ===
    'instrument': ['CytoFLEX nano BH46064', 'CytoFLEX nano BH46064', ...],
    'acquisition_software': ['CytExpert 2.4', 'CytExpert 2.4', ...],
    'total_events': [339392, 285103, ...],
    'acquisition_time_sec': [30.0, 28.5, ...],
    'dilution_factor': [1000, 1000, 1, ...],
    'operator': ['URAT', 'URAT', ...],
    
    # === MACHINE AVAILABILITY ===
    'has_nanofacs_data': [True, True, True, True, ...],
    'has_nta_data': [True, False, False, True, ...],  # Typically one NTA per biological sample
    
    # === QUALITY FLAGS ===
    'quality_status': ['Pass', 'Pass', 'Pass', 'Warn', ...],
    'is_control': [True, False, False, True, ...],  # Baseline = control
    'control_type': ['isotype', None, None, 'isotype', ...],  # 'isotype', 'blank', 'water'
    'notes': ['Baseline run', 'Test CD81 low dose', 'Test CD81 high dose', ...]
})
```

**Why this is critical:**
- ✅ **Single source of truth** for sample information
- ✅ **Unique sample_id** links all data
- ✅ **Flags** indicate which machines have data
- ✅ **Quality tracking** in one place

---

### **Schema 2: nanoFACS Statistics**

**UPDATED: Nov 13, 2025 - Added Baseline Comparison Fields**

**File:** `unified_data/measurements/nanofacs/statistics/event_statistics.parquet`

```python
nanofacs_stats = pd.DataFrame({
    # === IDENTIFIERS (ENHANCED) ===
    'biological_sample_id': ['P5_F10', 'P5_F10', 'P5_F10', ...],  # NEW: Groups iterations
    'measurement_id': ['P5_F10_ISO', 'P5_F10_CD81_0.25ug', 'P5_F10_CD81_1ug', ...],  # FOREIGN KEY (PRIMARY KEY)
    'baseline_measurement_id': ['P5_F10_ISO', 'P5_F10_ISO', 'P5_F10_ISO', ...],  # NEW: Links to baseline
    'is_baseline': [True, False, False, ...],  # NEW
    'measurement_date': ['2025-10-09 15:37:23', ...],
    'instrument': ['CytoFLEX nano BH46064', ...],
    
    # Event counts
    'total_events': [339392, 285103, ...],
    'acquisition_time_sec': [30.0, 28.5, ...],
    'events_per_second': [11313, 10004, ...],
    
    # FSC/SSC statistics
    'mean_FSC_H': [1250.5, 1180.2, ...],
    'median_FSC_H': [1100.3, 1050.8, ...],
    'std_FSC_H': [850.2, 790.5, ...],
    'mean_SSC_H': [890.3, 920.1, ...],
    'median_SSC_H': [750.5, 780.2, ...],
    
    # Fluorescence markers (all 6 channels)
    'mean_V447_H': [85.2, 78.5, ...],  # FL1
    'mean_B531_H': [65.3, 70.1, ...],  # FL2
    'mean_Y595_H': [78.9, 82.3, ...],  # FL3
    'mean_R670_H': [55.2, 60.8, ...],  # FL4
    'mean_R710_H': [45.8, 50.2, ...],  # FL5
    'mean_R792_H': [38.5, 42.1, ...],  # FL6
    
    # Gating results (calculated during parsing)
    'pct_debris': [15.2, 18.5, ...],
    'pct_ev_gate': [72.3, 68.9, ...],
    'pct_marker_positive': [85.2, 78.5, ...],  # CD81+ or CD9+
    'mean_fluorescence_intensity': [1250.5, 2150.8, ...],  # MFI
    
    # === BASELINE COMPARISON (NEW - Nov 13, 2025) ===
    # NULL for baseline measurements, populated for test measurements
    'delta_pct_marker_positive': [None, 40.0, 55.3, ...],  # % change from baseline
    'delta_mean_fluorescence': [None, 900.3, 1400.5, ...],  # Absolute MFI change
    'fold_change_marker': [None, 2.5, 3.8, ...],  # Fold increase vs baseline
    'fold_change_mfi': [None, 1.7, 2.1, ...],  # MFI fold change
    'is_significant_increase': [None, True, True, ...],  # TRUE if delta > threshold
    'baseline_comparison_quality': ['N/A', 'reliable', 'reliable', ...],  # Quality of comparison
    
    # Data quality metrics
    'cv_FSC': [0.68, 0.67, ...],  # Coefficient of variation
    'cv_SSC': [0.52, 0.55, ...],
    'has_anomalies': [False, False, ...],
    'qc_flags': ['', 'Low event count', ...]
})
```

---

### **Schema 3: NTA Statistics**

**UPDATED: Nov 13, 2025 - biological_sample_id linking**

**File:** `unified_data/measurements/nta/summary/nta_statistics.parquet`

**Note:** Typically ONE NTA measurement per biological sample (not per FCS file)

```python
nta_stats = pd.DataFrame({
    # === IDENTIFIERS (UPDATED) ===
    'biological_sample_id': ['P5_F10', 'P5_F16', ...],  # NEW: Links to all FCS iterations
    'nta_measurement_id': ['P5_F10_NTA', 'P5_F16_NTA', ...],  # Unique NTA ID (PRIMARY KEY)
    'measurement_date': ['2025-02-19', ...],
    'instrument': ['ZetaView 24-1152', ...],
    
    # Size measurements
    'D10_nm': [85.5, 82.3, ...],   # 10th percentile
    'D50_nm': [120.5, 115.8, ...],  # Median (MOST IMPORTANT)
    'D90_nm': [185.2, 178.5, ...],  # 90th percentile
    'mean_size_nm': [125.3, 120.8, ...],
    'mode_size_nm': [110.2, 105.5, ...],
    'std_size_nm': [35.8, 32.5, ...],
    
    # Concentration measurements
    'concentration_particles_ml': [2.5e11, 3.1e11, ...],
    'concentration_std': [2.3e10, 2.8e10, ...],
    'cv_concentration': [0.092, 0.090, ...],
    
    # 11-position uniformity
    'position_count': [11, 11, ...],
    'position_cv': [0.12, 0.10, ...],  # Lower = more uniform
    'uniformity_score': [88.5, 90.2, ...],  # % (higher = better)
    
    # Data quality
    'temperature_C': [25.2, 25.1, ...],
    'pH': [7.4, 7.4, ...],
    'conductivity': [12.5, 12.3, ...],
    'qc_status': ['Pass', 'Pass', ...],
    'qc_flags': ['', '', ...]
})
```

---

### **Schema 4: Baseline Comparison Table** ⭐ **NEW - Nov 13, 2025**

**File:** `unified_data/integrated/baseline_comparison.parquet`

**Purpose:** Pre-calculated comparison of test measurements vs their baseline

**Usage:** Quick lookup for "How much did marker expression increase?"

```python
baseline_comparison = pd.DataFrame({
    # === IDENTIFIERS ===
    'biological_sample_id': ['P5_F10', 'P5_F10', 'P5_F16', ...],  # Groups iterations
    'baseline_measurement_id': ['P5_F10_ISO', 'P5_F10_ISO', 'P5_F16_ISO', ...],  # Reference
    'test_measurement_id': ['P5_F10_CD81_0.25ug', 'P5_F10_CD81_1ug', 'P5_F16_CD81', ...],  # Test run
    
    # === TEST DETAILS ===
    'antibody_tested': ['CD81', 'CD81', 'CD81', ...],
    'antibody_concentration_ug': [0.25, 1.0, 1.0, ...],
    'iteration_number': [2, 3, 2, ...],  # Test run sequence
    
    # === BASELINE VALUES ===
    'baseline_pct_positive': [5.2, 5.2, 4.8, ...],  # Background/isotype %
    'baseline_mfi': [350.5, 350.5, 340.2, ...],  # Baseline MFI
    'baseline_pct_ev_gate': [72.3, 72.3, 70.5, ...],  # EV gate %
    
    # === TEST VALUES ===
    'test_pct_positive': [45.2, 60.5, 38.9, ...],  # Specific signal %
    'test_mfi': [1250.8, 1750.3, 920.5, ...],  # Test MFI
    'test_pct_ev_gate': [71.8, 70.9, 69.8, ...],  # Should be similar to baseline
    
    # === CHANGES/DELTAS (MOST IMPORTANT) ===
    'delta_pct_positive': [40.0, 55.3, 34.1, ...],  # Absolute % increase
    'delta_mfi': [900.3, 1399.8, 580.3, ...],  # Absolute MFI increase
    'fold_change_positive': [8.7, 11.6, 8.1, ...],  # Fold increase (test/baseline)
    'fold_change_mfi': [3.6, 5.0, 2.7, ...],  # MFI fold change
    
    # === STATISTICAL SIGNIFICANCE ===
    'is_significant': [True, True, True, ...],  # TRUE if passes threshold
    'significance_threshold': [10.0, 10.0, 10.0, ...],  # % threshold used
    'p_value': [0.001, 0.0001, 0.005, ...],  # If statistical test performed
    
    # === INTERPRETATION (AUTO-GENERATED) ===
    'response_magnitude': ['Strong', 'Very Strong', 'Strong', ...],  # "Weak", "Moderate", "Strong", "Very Strong"
    'interpretation': ['Positive', 'Positive', 'Positive', ...],  # "Negative", "Weak", "Positive", "Strong Positive"
    'dose_response': [None, 'Increasing', None, ...],  # "Increasing", "Decreasing", "Saturated" (for conc. series)
    
    # === QUALITY FLAGS ===
    'baseline_quality': ['Pass', 'Pass', 'Pass', ...],  # Quality of baseline run
    'test_quality': ['Pass', 'Pass', 'Warn', ...],  # Quality of test run
    'comparison_reliability': ['High', 'High', 'Medium', ...],  # "High", "Medium", "Low"
    'warnings': ['', '', 'Low event count in test', ...],  # Any issues
})
```

**Example Query:**
```python
# "Show me all samples with strong CD81 response"
strong_cd81 = baseline_comparison[
    (baseline_comparison['antibody_tested'] == 'CD81') &
    (baseline_comparison['response_magnitude'] == 'Strong')
]
```

---

### **Schema 5: Integrated Dataset (ML-Ready)**

**UPDATED: Nov 13, 2025 - Baseline-Aware Features**

**File:** `unified_data/integrated/combined_features.parquet`

**This is the GOLD STANDARD file for ML training!**

```python
combined_features = pd.DataFrame({
    # === IDENTIFIERS (UPDATED) ===
    'biological_sample_id': ['P5_F10', 'P5_F10', 'P5_F16', ...],  # NEW: Groups iterations
    'measurement_id': ['P5_F10_ISO', 'P5_F10_CD81_0.25ug', 'P5_F16_ISO', ...],  # PRIMARY KEY
    'baseline_measurement_id': ['P5_F10_ISO', 'P5_F10_ISO', 'P5_F16_ISO', ...],  # NEW
    'is_baseline': [True, False, True, ...],  # NEW
    
    # Sample metadata
    'sample_name': ['Exo+ ISO', 'Exo+ 0.25ug CD81', ...],
    'passage': ['P5', 'P5', 'P5', ...],
    'antibody': ['ISO', 'CD81', 'ISO', ...],
    'antibody_concentration_ug': [0, 0.25, 0, ...],  # NEW
    'purification_method': ['SEC', 'SEC', 'SEC', ...],
    'iteration_number': [1, 2, 1, ...],  # NEW
    
    # === nanoFACS Features (300+ features) ===
    # Size/complexity
    'facs_mean_FSC': [1250.5, 1180.2, ...],
    'facs_median_FSC': [1100.3, 1050.8, ...],
    'facs_std_FSC': [850.2, 790.5, ...],
    'facs_mean_SSC': [890.3, 920.1, ...],
    
    # Fluorescence markers
    'facs_mean_V447': [85.2, 78.5, ...],
    'facs_mean_B531': [65.3, 70.1, ...],
    # ... (all 26 parameters × statistics)
    
    # Gating results
    'facs_pct_marker_positive': [5.2, 45.2, 4.8, ...],  # Raw values
    'facs_pct_ev_gate': [72.3, 71.8, 70.5, ...],
    'facs_mean_fluorescence_intensity': [350.5, 1250.8, 340.2, ...],
    
    # === BASELINE DELTAS (NEW) - NULL for baseline measurements ===
    'facs_delta_pct_marker': [None, 40.0, None, ...],  # Change from baseline
    'facs_fold_change_marker': [None, 8.7, None, ...],  # Fold increase
    'facs_delta_mfi': [None, 900.3, None, ...],  # MFI change
    'facs_baseline_normalized_mfi': [1.0, 3.6, 1.0, ...],  # MFI / baseline_MFI
    
    # === NTA Features (50+ features) ===
    # Size distribution (one per biological sample)
    'nta_D50_nm': [120.5, 120.5, 115.8, ...],  # Same for all iterations of bio sample
    'nta_mean_size': [125.3, 125.3, 120.8, ...],
    'nta_std_size': [35.8, 35.8, 32.5, ...],
    
    # Concentration
    'nta_concentration': [2.5e11, 2.5e11, 3.1e11, ...],
    'nta_uniformity_score': [88.5, 88.5, 90.2, ...],
    
    # === Derived/Computed Features ===
    # Cross-machine correlations
    'size_correlation': [0.85, 0.78, ...],  # FSC vs D50 correlation
    'purity_score': [0.92, 0.88, ...],      # Combined metric
    
    # === Response Features (NEW) ===
    'response_magnitude': [None, 'Strong', None, ...],  # NULL for baseline
    'response_direction': [None, 'increase', None, ...],  # "increase", "decrease", "no_change"
    'dose_response_slope': [None, 0.55, None, ...],  # For concentration series
    
    # === Labels (for ML) ===
    'quality_label': ['Good', 'Good', 'Good', ...],  # Classification target
    'quality_score': [0.95, 0.88, 0.92, ...],       # Regression target
    'baseline_quality': ['Pass', 'Pass', 'Pass', ...],  # NEW: Quality of linked baseline
})
```

**THIS is what you feed to ML models!** ✅

---

## 💡 **Benefits of Unified Approach**

### **1. Easy Correlation Analysis**

```python
import pandas as pd

# Load integrated dataset
df = pd.read_parquet('unified_data/integrated/combined_features.parquet')

# Correlate nanoFACS and NTA measurements
import seaborn as sns

sns.scatterplot(
    data=df, 
    x='facs_mean_FSC',      # nanoFACS size indicator
    y='nta_D50_nm'          # NTA median size
)
plt.title('Do nanoFACS and NTA agree on particle size?')

# Easy! Both in same DataFrame ✅
```

### **2. Simplified ML Training**

```python
from sklearn.ensemble import RandomForestClassifier

# Load integrated dataset
df = pd.read_parquet('unified_data/integrated/combined_features.parquet')

# Select features from BOTH machines
feature_cols = [col for col in df.columns 
                if col.startswith('facs_') or col.startswith('nta_')]

X = df[feature_cols].values  # All features from both machines!
y = df['quality_label'].values

# Train model on combined data
model = RandomForestClassifier()
model.fit(X, y)

# ONE simple workflow! ✅
```

### **3. Comprehensive Quality Control**

```python
# Check which samples have data from BOTH machines
metadata = pd.read_parquet('unified_data/samples/sample_metadata.parquet')

complete_samples = metadata[
    (metadata['has_nanofacs_data'] == True) & 
    (metadata['has_nta_data'] == True)
]

print(f"Complete samples: {len(complete_samples)}")
print(f"Missing NTA: {(~metadata['has_nta_data']).sum()}")
print(f"Missing nanoFACS: {(~metadata['has_nanofacs_data']).sum()}")

# Easy tracking! ✅
```

### **4. Single API Endpoint**

```python
# FastAPI example
@app.get("/api/sample/{sample_id}")
async def get_sample(sample_id: str):
    # Load from ONE integrated dataset
    df = pd.read_parquet('unified_data/integrated/combined_features.parquet')
    sample = df[df['sample_id'] == sample_id].iloc[0]
    
    return {
        "sample_id": sample_id,
        "sample_name": sample['sample_name'],
        
        # nanoFACS data
        "nanofacs": {
            "mean_FSC": sample['facs_mean_FSC'],
            "pct_marker_positive": sample['facs_pct_marker_positive']
        },
        
        # NTA data
        "nta": {
            "median_size_nm": sample['nta_D50_nm'],
            "concentration": sample['nta_concentration']
        },
        
        # Integrated analysis
        "quality": {
            "label": sample['quality_label'],
            "score": sample['quality_score']
        }
    }
    
# Everything from ONE place! ✅
```

---

## 🔧 **Implementation Strategy**

### **Phase 1: Parse Both Machines Separately (Task 1.1 & 1.2)**

```python
# Task 1.1: nanoFACS Parser
def parse_nanofacs_batch():
    for fcs_file in fcs_files:
        # Parse FCS file
        meta, events = fcsparser.parse(fcs_file)
        
        # Extract sample_id from filename/metadata
        sample_id = generate_sample_id(fcs_file, meta)
        
        # Save raw events
        events.to_parquet(f'measurements/nanofacs/events/{sample_id}.parquet')
        
        # Calculate statistics
        stats = calculate_statistics(events)
        stats['sample_id'] = sample_id
        
        # Append to statistics file
        append_to_parquet(stats, 'measurements/nanofacs/statistics/event_statistics.parquet')

# Task 1.2: NTA Parser
def parse_nta_batch():
    for nta_file in nta_files:
        # Parse NTA text file
        data = parse_nta_file(nta_file)
        
        # Extract sample_id
        sample_id = generate_sample_id(nta_file, data)
        
        # Save distribution
        data.to_parquet(f'measurements/nta/distributions/{sample_id}.parquet')
        
        # Calculate statistics
        stats = calculate_nta_statistics(data)
        stats['sample_id'] = sample_id
        
        # Append to statistics file
        append_to_parquet(stats, 'measurements/nta/summary/nta_statistics.parquet')
```

### **Phase 2: Create Unified Registry (Task 1.3)**

```python
# Task 1.3: Data Integration
def create_sample_registry():
    # Scan all processed files
    nanofacs_samples = get_nanofacs_sample_ids()
    nta_samples = get_nta_sample_ids()
    
    # Create master sample list
    all_samples = set(nanofacs_samples + nta_samples)
    
    metadata = []
    for sample_id in all_samples:
        # Extract metadata from filenames/original files
        meta = extract_sample_metadata(sample_id)
        
        # Add flags
        meta['has_nanofacs_data'] = sample_id in nanofacs_samples
        meta['has_nta_data'] = sample_id in nta_samples
        
        metadata.append(meta)
    
    # Save master registry
    df = pd.DataFrame(metadata)
    df.to_parquet('unified_data/samples/sample_metadata.parquet')
```

### **Phase 3: Merge for ML (Task 1.3 continued)**

```python
def create_integrated_dataset():
    # Load all statistics
    metadata = pd.read_parquet('samples/sample_metadata.parquet')
    nanofacs = pd.read_parquet('measurements/nanofacs/statistics/event_statistics.parquet')
    nta = pd.read_parquet('measurements/nta/summary/nta_statistics.parquet')
    
    # Merge on sample_id
    combined = metadata.merge(nanofacs, on='sample_id', how='left', suffixes=('', '_facs'))
    combined = combined.merge(nta, on='sample_id', how='left', suffixes=('', '_nta'))
    
    # Rename columns for clarity
    combined = combined.rename(columns={
        'mean_FSC_H': 'facs_mean_FSC',
        'D50_nm': 'nta_D50_nm',
        # ... rename all columns
    })
    
    # Calculate derived features
    combined['size_correlation'] = calculate_correlation(
        combined['facs_mean_FSC'], 
        combined['nta_D50_nm']
    )
    
    # Add quality labels
    combined['quality_label'] = assign_quality_labels(combined)
    
    # Save ML-ready dataset
    combined.to_parquet('unified_data/integrated/combined_features.parquet')
```

---

## 📊 **File Organization Summary**

### **Complete Directory Structure:**

```
unified_data/
├── samples/
│   ├── sample_metadata.parquet          ← Master registry
│   └── experimental_conditions.parquet
│
├── measurements/
│   ├── nanofacs/
│   │   ├── events/
│   │   │   ├── S001.parquet             ← 339K events each
│   │   │   ├── S002.parquet
│   │   │   └── ...
│   │   └── statistics/
│   │       └── event_statistics.parquet  ← Summary stats
│   │
│   └── nta/
│       ├── distributions/
│       │   ├── S001.parquet             ← Size distribution curves
│       │   ├── S002.parquet
│       │   └── ...
│       └── summary/
│           └── nta_statistics.parquet    ← Summary stats
│
└── integrated/
    ├── combined_features.parquet        ← ML-ready (BOTH machines)
    ├── quality_labels.parquet
    └── correlation_analysis.parquet
```

---

## ✅ **Final Recommendation**

### **DO THIS (Standardized Unified Format):**

1. ✅ **Create master sample registry** with unique `sample_id`
2. ✅ **Parse both machines** to separate folders (machine-specific formats OK initially)
3. ✅ **Extract statistics** from both into standardized Parquet files
4. ✅ **Merge into integrated dataset** using `sample_id` as key
5. ✅ **Use integrated dataset** for ML, dashboards, reports

### **Format Summary:**

| Data Type | Format | Why |
|-----------|--------|-----|
| **Sample metadata** | Parquet | Small, shared across all machines |
| **nanoFACS events** | Parquet | Large (339K rows), machine-specific |
| **nanoFACS statistics** | Parquet | Standardized schema |
| **NTA distributions** | Parquet | Machine-specific format |
| **NTA statistics** | Parquet | Standardized schema |
| **Integrated ML data** | Parquet | **BOTH machines, ONE file** ✅ |

---

## 🎯 **Key Principle:**

> **"Parse machine-specific, Store standardized, Integrate for analysis"**

- Parse each machine in its native format
- Convert to standardized Parquet with common schema
- Link everything via `sample_id`
- Create integrated datasets for ML/analysis

**This gives you flexibility + consistency + power!** 🚀

---

## 🌐 **AWS S3 Storage Integration** ⭐ **NEW - Nov 13, 2025**

### **Decision:** All file storage will use AWS S3 (not local/on-premise)

**Background:** During Nov 13, 2025 meeting with CRMIT + BioVaram:
- CRMIT tech lead demonstrated AWS S3 to client
- Client approved S3 for all data storage
- All raw files (FCS, NTA text) will be stored in S3
- Processed Parquet files will also be stored in S3

### **S3 Bucket Structure:**

```
s3://exosome-analysis-bucket/
├── raw_data/
│   ├── nanofacs/
│   │   ├── P5_F10_ISO.fcs
│   │   ├── P5_F10_CD81_0.25ug.fcs
│   │   ├── P5_F10_CD81_1ug.fcs
│   │   └── ... (70 FCS files)
│   │
│   └── nta/
│       ├── P5_F10_NTA.txt
│       ├── P5_F16_NTA.txt
│       └── ... (~70 text files)
│
├── processed_data/
│   ├── nanofacs/
│   │   └── event_statistics.parquet  (all 70 samples)
│   │
│   └── nta/
│       └── nta_statistics.parquet  (all samples)
│
└── integrated/
    ├── sample_metadata.parquet
    ├── baseline_comparison.parquet
    └── combined_features.parquet
```

### **Implementation with boto3:**

```python
import boto3
import pandas as pd
from io import BytesIO

# Initialize S3 client
s3_client = boto3.client('s3', 
                         region_name='us-east-1',
                         aws_access_key_id='YOUR_KEY',
                         aws_secret_access_key='YOUR_SECRET')

BUCKET_NAME = 'exosome-analysis-bucket'

# === READ FCS FILE FROM S3 ===
def read_fcs_from_s3(s3_path):
    """Download FCS file from S3 and parse"""
    # Parse S3 path
    # s3://bucket/raw_data/nanofacs/P5_F10_ISO.fcs
    key = s3_path.replace(f's3://{BUCKET_NAME}/', '')
    
    # Download to local temp file
    local_temp = f'/tmp/{key.split("/")[-1]}'
    s3_client.download_file(BUCKET_NAME, key, local_temp)
    
    # Parse FCS
    meta, events = fcsparser.parse(local_temp)
    
    # Clean up temp file
    os.remove(local_temp)
    
    return meta, events

# === WRITE PARQUET TO S3 ===
def write_parquet_to_s3(df, s3_path):
    """Write Parquet file directly to S3"""
    # Write to in-memory buffer
    buffer = BytesIO()
    df.to_parquet(buffer, engine='pyarrow', compression='snappy')
    
    # Upload to S3
    key = s3_path.replace(f's3://{BUCKET_NAME}/', '')
    buffer.seek(0)
    s3_client.upload_fileobj(buffer, BUCKET_NAME, key)
    
    print(f"✅ Uploaded to {s3_path}")

# === READ PARQUET FROM S3 ===
def read_parquet_from_s3(s3_path):
    """Read Parquet file directly from S3"""
    key = s3_path.replace(f's3://{BUCKET_NAME}/', '')
    
    # Download to buffer
    buffer = BytesIO()
    s3_client.download_fileobj(BUCKET_NAME, key, buffer)
    
    # Read Parquet
    buffer.seek(0)
    df = pd.read_parquet(buffer)
    
    return df

# === LIST FILES IN S3 ===
def list_s3_files(prefix):
    """List all files in S3 with given prefix"""
    response = s3_client.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=prefix
    )
    
    files = [obj['Key'] for obj in response.get('Contents', [])]
    return [f's3://{BUCKET_NAME}/{f}' for f in files]

# === EXAMPLE USAGE ===
# List all FCS files
fcs_files = list_s3_files('raw_data/nanofacs/')
# ['s3://.../P5_F10_ISO.fcs', 's3://.../P5_F10_CD81_0.25ug.fcs', ...]

# Process each file
for fcs_s3_path in fcs_files:
    meta, events = read_fcs_from_s3(fcs_s3_path)
    stats = calculate_statistics(events)
    # ... continue processing
```

### **Benefits of S3 Storage:**

1. **Centralized Storage:** All team members access same data
2. **Versioning:** Can enable S3 versioning for data history
3. **Scalability:** No local storage limits
4. **Security:** IAM roles, encryption at rest
5. **Backup:** Automatic replication, disaster recovery
6. **Cost:** Pay only for what you use (~$0.023/GB/month)

### **Performance Considerations:**

- **Download Time:** ~2-3 seconds per 12MB FCS file (from US servers)
- **Upload Time:** ~1-2 seconds per Parquet file (<1MB)
- **Caching Strategy:** Download to `/tmp/` during processing, delete after
- **Parallel Processing:** Can download multiple files concurrently with threading

---

## 🔬 **Baseline + Iterations Workflow** ⭐ **NEW - Nov 13, 2025**

### **Discovery:** How Scientists Actually Use the System

During meeting, learned the **ACTUAL experimental workflow**:

```
EXPERIMENT DESIGN:
1. Take ONE biological sample (e.g., Passage 5, Fraction 10 exosomes)
2. Run it FIRST with isotype control (ISO) → BASELINE
3. Run SAME sample multiple times with different antibodies → ITERATIONS
4. Compare each test run to the baseline

RESULT: 5-6 FCS files for ONE biological sample
```

### **Example Workflow:**

```
BIOLOGICAL SAMPLE: Passage 5, Fraction 10 exosomes (purified via SEC)

RUN 1 (Baseline):
├─ Sample: P5_F10 + Isotype antibody (negative control)
├─ File: "Exo+ ISO SEC.fcs"
├─ measurement_id: "P5_F10_ISO"
├─ Purpose: Establish background fluorescence
└─ Result: 5% positive (background noise)

RUN 2 (Test - Low Dose):
├─ Sample: SAME P5_F10 + CD81 antibody (0.25 µg)
├─ File: "Exo+ 0.25ug CD81 SEC.fcs"
├─ measurement_id: "P5_F10_CD81_0.25ug"
├─ Purpose: Test specific CD81 marker expression
└─ Result: 25% positive → +20% vs baseline

RUN 3 (Test - Medium Dose):
├─ Sample: SAME P5_F10 + CD81 antibody (1.0 µg)
├─ File: "Exo+ 1ug CD81 SEC.fcs"
├─ measurement_id: "P5_F10_CD81_1ug"
├─ Purpose: Test dose response
└─ Result: 45% positive → +40% vs baseline

RUN 4 (Test - High Dose):
├─ Sample: SAME P5_F10 + CD81 antibody (2.0 µg)
├─ File: "Exo+ 2ug CD81 SEC.fcs"
├─ measurement_id: "P5_F10_CD81_2ug"
├─ Purpose: Test saturation
└─ Result: 60% positive → +55% vs baseline

RUN 5-6 (Other Markers):
├─ Sample: SAME P5_F10 + CD9 antibody
├─ Sample: SAME P5_F10 + CD63 antibody
└─ Purpose: Test multiple markers on same sample

ALL LINKED BY: biological_sample_id = "P5_F10"
```

### **Data Model to Support This:**

**1. Two-Level Identification System:**

```python
# LEVEL 1: Biological Sample (groups all iterations)
biological_sample_id = "P5_F10"  # Passage 5, Fraction 10

# LEVEL 2: Individual Measurement (one per FCS file)
measurement_id = "P5_F10_CD81_0.25ug"  # Specific run
```

**2. Baseline Linking:**

```python
# Every test measurement links to its baseline
baseline_measurement_id = "P5_F10_ISO"  # Reference for comparison
```

**3. Iteration Tracking:**

```python
iteration_number = 2  # 1=baseline, 2-6=tests
```

### **Comparison Calculations:**

```python
def calculate_baseline_delta(test_measurement_id, baseline_measurement_id):
    # Load test and baseline statistics
    test = event_stats[event_stats['measurement_id'] == test_measurement_id].iloc[0]
    baseline = event_stats[event_stats['measurement_id'] == baseline_measurement_id].iloc[0]
    
    # Calculate deltas
    delta_pct_positive = test['pct_marker_positive'] - baseline['pct_marker_positive']
    # 45% - 5% = +40%
    
    fold_change = test['pct_marker_positive'] / baseline['pct_marker_positive']
    # 45 / 5 = 9x increase
    
    delta_mfi = test['mean_fluorescence_intensity'] - baseline['mean_fluorescence_intensity']
    # 1250 - 350 = +900
    
    return {
        'delta_pct_positive': delta_pct_positive,
        'fold_change_positive': fold_change,
        'delta_mfi': delta_mfi,
        'is_significant': delta_pct_positive > 10.0  # Threshold
    }
```

### **Queries Scientists Need:**

**Q1:** "Show me all CD81 test runs for Passage 5 samples"
```python
cd81_tests = sample_metadata[
    (sample_metadata['antibody'] == 'CD81') &
    (sample_metadata['passage'] == 'P5') &
    (sample_metadata['is_baseline'] == False)
]
```

**Q2:** "Which samples showed strong response to CD81?"
```python
strong_response = baseline_comparison[
    (baseline_comparison['antibody_tested'] == 'CD81') &
    (baseline_comparison['delta_pct_positive'] > 30)
]
```

**Q3:** "Compare all iterations of biological sample P5_F10"
```python
p5_f10_iterations = sample_metadata[
    sample_metadata['biological_sample_id'] == 'P5_F10'
].sort_values('iteration_number')

# Show progression: baseline → test1 → test2 → ...
```

**Q4:** "Is there a dose-response relationship for CD81?"
```python
dose_response = baseline_comparison[
    (baseline_comparison['biological_sample_id'] == 'P5_F10') &
    (baseline_comparison['antibody_tested'] == 'CD81')
].sort_values('antibody_concentration_ug')

# Plot: concentration vs delta_pct_positive
# Expected: Increasing curve, then saturation
```

### **Implementation Impact:**

**Task 1.1 (FCS Parser) - ENHANCED:**
- Parse biological_sample_id from filename
- Detect baseline vs test (check for "ISO", "Isotype")
- Generate measurement_id with antibody + concentration
- Link test runs to baseline

**Task 1.3 (Data Integration) - NEW MODULE:**
- Group by biological_sample_id
- Identify baseline (is_baseline=True)
- Calculate deltas for all test measurements
- Generate baseline_comparison.parquet

**Timeline Impact:** +3-5 days for baseline comparison logic

---