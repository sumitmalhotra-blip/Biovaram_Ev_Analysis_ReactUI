# Filename Parsing Rules and Patterns

**Version:** 1.0  
**Date:** November 13, 2025  
**Status:** DRAFT - Requires validation  
**Author:** CRMIT Team

---

## Table of Contents
1. [Overview](#overview)
2. [FCS File Naming Patterns](#fcs-file-naming-patterns)
3. [NTA File Naming Pattern](#nta-file-naming-pattern)
4. [Extraction Logic](#extraction-logic)
5. [Baseline Detection Rules](#baseline-detection-rules)
6. [Implementation Examples](#implementation-examples)
7. [Known Issues and Challenges](#known-issues-and-challenges)

---

## Overview

### Purpose
This document defines the rules and patterns for extracting metadata from FCS and NTA filenames. The primary goals are:

1. **Extract `biological_sample_id`** - Groups all measurements from the same biological sample (baseline + test iterations)
2. **Extract `measurement_id`** - Unique identifier for each individual file
3. **Detect baseline vs test** - Identify isotype controls (baseline) vs antibody tests
4. **Extract experimental parameters** - Antibody, concentration, method, etc.
5. **Link NTA to FCS** - Map NTA passage/fraction to FCS lot/fraction

### Critical Requirements
- **Baseline + Iterations Workflow**: Each biological sample has 1 baseline (isotype) + 5 test measurements
- **Consistent Grouping**: All iterations must share the same `biological_sample_id`
- **Unique Identification**: Each file must have a unique `measurement_id`

---

## FCS File Naming Patterns

We have identified **3 distinct naming conventions** across the workspace:

### Group 1: "10000 exo and cd81" Folder

**Folder Path:** `nanoFACS/10000 exo and cd81/`

**Pattern Description:**
- Format: `[Exo +] <concentration>ug <antibody> [method].fcs`
- Examples:
  - `0.25ug ISO SEC.fcs`
  - `Exo + 0.25ug CD81 SEC.fcs`
  - `Exo+ 1ug CD81 NO filter.fcs`
  - `Exo+ 2ug ISO centri.fcs`

**Characteristics:**
- Spaces in filenames (inconsistent)
- Optional "Exo +" prefix
- Concentration always in micrograms (ug)
- Antibody: ISO, CD81, CD8, CD9
- Optional method: SEC, Centri, "NO filter"

**Regex Pattern:**
```regex
(?:Exo\s*\+\s*)?(\d+\.?\d*)\s*ug\s+(\w+)(?:\s+(SEC|Centri|NO\s*filter))?\.fcs
```

**Capture Groups:**
1. `concentration` - e.g., "0.25", "1", "2"
2. `antibody` - e.g., "ISO", "CD81", "CD8"
3. `method` - e.g., "SEC", "Centri", "NO filter" (optional)

**biological_sample_id Strategy:**
- All files in this folder are from the **same biological sample** (10,000 exosome batch)
- Use fixed ID: `EXOSOME_10K`

**Example Extraction:**

| Filename | biological_sample_id | measurement_id | antibody | concentration | method | is_baseline |
|----------|---------------------|----------------|----------|---------------|--------|-------------|
| `0.25ug ISO SEC.fcs` | EXOSOME_10K | EXOSOME_10K_ISO_0.25ug_SEC | ISO | 0.25ug | SEC | True |
| `Exo + 0.25ug CD81 SEC.fcs` | EXOSOME_10K | EXOSOME_10K_CD81_0.25ug_SEC | CD81 | 0.25ug | SEC | False |
| `Exo+ 1ug CD81 Centri.fcs` | EXOSOME_10K | EXOSOME_10K_CD81_1ug_Centri | CD81 | 1ug | Centri | False |

---

### Group 2: "CD9 and exosome lots" Folder

**Folder Path:** `nanoFACS/CD9 and exosome lots/`

**Pattern Description:**
- Format: `L<lot>+F<fraction>+<antibody>.fcs`
- Examples:
  - `L5+F10+CD9.fcs`
  - `L5+F10+ISO.fcs`
  - `L5+F16+CD9.fcs`
  - `L5+F16+ISO.fcs`

**Characteristics:**
- Lot number (L#)
- Fraction number (F#)
- No spaces
- Clean, consistent format
- Antibody: CD9, ISO

**Regex Pattern:**
```regex
L(\d+)\+F(\d+)\+(\w+)\.fcs
```

**Capture Groups:**
1. `lot_number` - e.g., "5", "6"
2. `fraction_number` - e.g., "10", "16"
3. `antibody` - e.g., "CD9", "ISO"

**biological_sample_id Strategy:**
- Group by **lot + fraction**
- Format: `L{lot}_F{fraction}`

**Example Extraction:**

| Filename | biological_sample_id | measurement_id | lot | fraction | antibody | is_baseline |
|----------|---------------------|----------------|-----|----------|----------|-------------|
| `L5+F10+ISO.fcs` | L5_F10 | L5_F10_ISO | 5 | 10 | ISO | True |
| `L5+F10+CD9.fcs` | L5_F10 | L5_F10_CD9 | 5 | 10 | CD9 | False |
| `L5+F16+ISO.fcs` | L5_F16 | L5_F16_ISO | 5 | 16 | ISO | True |
| `L5+F16+CD9.fcs` | L5_F16 | L5_F16_CD9 | 5 | 16 | CD9 | False |

---

### Group 3: "EXP 6-10-2025" Folder

**Folder Path:** `nanoFACS/EXP 6-10-2025/`

**Pattern Description:**
- Format 1: `<type> <value>ug.fcs` (antibody/isotype)
- Format 2: `sample <dilution>.fcs` (dilution series)
- Examples:
  - `ab  1ug.fcs` (note: double space!)
  - `isotype 0.25ug.fcs`
  - `isotype 2ug.fcs`
  - `sample 1-10.fcs`
  - `sample 1-100.fcs`
  - `sample no dil.fcs`

**Characteristics:**
- Inconsistent spacing (some have double spaces)
- Two sub-patterns: antibody concentration vs dilution factor
- Type: "ab" (antibody), "isotype", "sample"
- Dilution factors: 1-10, 1-100, 1-1000, etc.

**Regex Pattern (Antibody/Isotype):**
```regex
(ab|isotype)\s+(\d+\.?\d*)\s*ug\.fcs
```

**Regex Pattern (Dilution Series):**
```regex
sample\s+([\d-]+|no\s+dil)\.fcs
```

**Capture Groups (Antibody):**
1. `type` - "ab" or "isotype"
2. `concentration` - e.g., "0.25", "1", "2"

**Capture Groups (Dilution):**
1. `dilution_factor` - e.g., "1-10", "1-100", "no dil"

**biological_sample_id Strategy:**
- All files in this folder are from the **same experiment**
- Use fixed ID: `EXP_6_10_2025`

**Example Extraction:**

| Filename | biological_sample_id | measurement_id | type | value | is_baseline |
|----------|---------------------|----------------|------|-------|-------------|
| `isotype 0.25ug.fcs` | EXP_6_10_2025 | EXP_6_10_2025_isotype_0.25ug | isotype | 0.25ug | True |
| `ab  1ug.fcs` | EXP_6_10_2025 | EXP_6_10_2025_ab_1ug | ab | 1ug | False |
| `sample 1-10.fcs` | EXP_6_10_2025 | EXP_6_10_2025_sample_1-10 | sample | 1-10 | False |

---

## NTA File Naming Pattern

**Folder Path:** `NTA/EV_IPSC_P#_*_NTA/`

**Pattern Description:**
- Format: `<date>_<sequence>_EV_ip_p<passage>_F<fraction>-<dilution>_size_<laser>_<positions>pos.txt`
- Example: `20250219_0001_EV_ip_p1_F8-1000_size_488_11pos.txt`

**Characteristics:**
- Date: YYYYMMDD format
- Sequence: 4-digit counter
- Passage: P1, P2, etc.
- Fraction: F7, F8, F10, etc.
- Dilution: 1000, 100, etc.
- Laser wavelength: 488nm
- Positions: 11 (multi-position measurement)

**Regex Pattern:**
```regex
(\d{8})_(\d{4})_EV_ip_p(\d+)_F(\d+)-(\d+)_size_(\d+)(?:_(\d+)pos)?\.txt
```

**Capture Groups:**
1. `date` - e.g., "20250219"
2. `sequence` - e.g., "0001"
3. `passage` - e.g., "1" (from "p1")
4. `fraction` - e.g., "8" (from "F8")
5. `dilution` - e.g., "1000"
6. `laser_wavelength` - e.g., "488"
7. `positions` - e.g., "11" (optional)

**biological_sample_id Strategy:**
- Group by **passage + fraction**
- Format: `P{passage}_F{fraction}`

**Example Extraction:**

| Filename | biological_sample_id | measurement_id | passage | fraction | dilution |
|----------|---------------------|----------------|---------|----------|----------|
| `20250219_0001_EV_ip_p1_F8-1000_size_488_11pos.txt` | P1_F8 | P1_F8_20250219_0001 | 1 | 8 | 1000 |
| `20250219_0003_EV_ip_p1_F7-1000_size_488_11pos.txt` | P1_F7 | P1_F7_20250219_0003 | 1 | 7 | 1000 |

---

## Extraction Logic

### Step-by-Step Algorithm

#### For FCS Files:

```python
def parse_fcs_filename(filename: str, folder_path: str) -> Dict:
    """
    Parse FCS filename and extract metadata.
    
    Returns:
        {
            'biological_sample_id': str,
            'measurement_id': str,
            'antibody': str,
            'concentration': str,
            'method': str,
            'is_baseline': bool,
            'iteration_number': int
        }
    """
    
    # Step 1: Determine which pattern group
    if "10000 exo and cd81" in folder_path:
        return parse_group_1(filename)
    elif "CD9 and exosome lots" in folder_path:
        return parse_group_2(filename)
    elif "EXP 6-10-2025" in folder_path:
        return parse_group_3(filename)
    else:
        raise ValueError(f"Unknown folder pattern: {folder_path}")
    
    # Step 2: Apply regex pattern (see specific functions)
    
    # Step 3: Extract biological_sample_id
    
    # Step 4: Detect baseline
    
    # Step 5: Generate measurement_id
    
    # Step 6: Assign iteration_number (1 for baseline, 2+ for tests)
```

#### For NTA Files:

```python
def parse_nta_filename(filename: str) -> Dict:
    """
    Parse NTA filename and extract metadata.
    
    Returns:
        {
            'biological_sample_id': str,
            'measurement_id': str,
            'passage': int,
            'fraction': int,
            'dilution': int,
            'date': str
        }
    """
    
    # Step 1: Apply NTA regex pattern
    
    # Step 2: Extract biological_sample_id = P{passage}_F{fraction}
    
    # Step 3: Generate measurement_id = P{passage}_F{fraction}_{date}_{sequence}
    
    # Step 4: Extract other metadata
```

---

## Baseline Detection Rules

### Keywords for Baseline Identification:

The following keywords indicate an **isotype control (baseline measurement)**:

- `ISO` (case-insensitive)
- `iso`
- `Isotype`
- `isotype`

### Detection Logic:

```python
def is_baseline_measurement(antibody: str) -> bool:
    """
    Determine if measurement is a baseline (isotype control).
    
    Args:
        antibody: Antibody name from filename
    
    Returns:
        True if baseline, False if test
    """
    baseline_keywords = ['iso', 'isotype']
    return antibody.lower() in baseline_keywords
```

### Special Cases:

1. **"ISO SEC" vs "ISO Centri"** - Both are baselines, method differs
2. **"iso" vs "ISO"** - Treat as equivalent (case-insensitive)
3. **No baseline found** - Flag as data quality issue

---

## Implementation Examples

### Example 1: Parse Group 2 (L5+F10)

```python
import re

def parse_group_2(filename: str) -> Dict:
    """Parse Group 2: L5+F10+CD9.fcs pattern."""
    
    pattern = r'L(\d+)\+F(\d+)\+(\w+)\.fcs'
    match = re.match(pattern, filename)
    
    if not match:
        raise ValueError(f"Filename doesn't match Group 2 pattern: {filename}")
    
    lot = match.group(1)
    fraction = match.group(2)
    antibody = match.group(3)
    
    biological_sample_id = f"L{lot}_F{fraction}"
    is_baseline = antibody.lower() in ['iso', 'isotype']
    measurement_id = f"{biological_sample_id}_{antibody}"
    
    return {
        'biological_sample_id': biological_sample_id,
        'measurement_id': measurement_id,
        'lot': int(lot),
        'fraction': int(fraction),
        'antibody': antibody,
        'is_baseline': is_baseline,
        'iteration_number': 1 if is_baseline else None  # Assign later after grouping
    }
```

### Example 2: Link NTA to FCS

```python
# Manual mapping (requires client input)
PASSAGE_TO_LOT_MAPPING = {
    'P1': 'L5',
    'P2': 'L6',
    # TODO: Get complete mapping
}

def link_nta_to_fcs(nta_biological_sample_id: str) -> str:
    """
    Link NTA biological_sample_id to FCS.
    
    Args:
        nta_biological_sample_id: e.g., "P1_F8"
    
    Returns:
        FCS biological_sample_id: e.g., "L5_F8"
    """
    passage, fraction = nta_biological_sample_id.split('_')
    lot = PASSAGE_TO_LOT_MAPPING.get(passage)
    
    if not lot:
        raise ValueError(f"Unknown passage: {passage}")
    
    return f"{lot}_{fraction}"
```

---

## Known Issues and Challenges

### Issue 1: Inconsistent Naming Conventions ⚠️

**Problem:** 3 different naming patterns across folders  
**Impact:** Cannot use a single regex for all files  
**Solution:** Folder-based pattern detection (implemented above)

### Issue 2: NTA-FCS Linking ⚠️

**Problem:** NTA uses "P1_F8", FCS uses "L5_F10" - different naming  
**Impact:** Cannot automatically link NTA size data to FCS marker data  
**Solution:** Requires manual passage-to-lot mapping from client

**Action Required:**
- Get complete P# to L# mapping from client
- Verify fraction numbers match between NTA and FCS

### Issue 3: Inconsistent Spacing and Capitalization ⚠️

**Problem:** Examples:
- `ab  1ug.fcs` (double space)
- `Exo + 0.25ug` vs `Exo+ 1ug` (space before +)
- `ISO` vs `iso` vs `Isotype`

**Solution:** 
- Use `\s+` in regex to handle variable spacing
- Case-insensitive baseline detection
- Normalize antibody names during parsing

### Issue 4: Missing Baseline for Some Groups ⚠️

**Problem:** Not all biological_sample_id groups have a clear baseline file  
**Impact:** Cannot calculate baseline comparisons  
**Solution:**
- Flag samples with missing baseline
- Request clarification from client
- Consider using closest baseline if appropriate

### Issue 5: Iteration Number Assignment ⚠️

**Problem:** Files don't have explicit iteration numbers (1, 2, 3, etc.)  
**Solution:**
- Assign iteration_number = 1 to baseline
- Assign iteration_number = 2, 3, 4... to tests (sorted by concentration or filename)

---

## Validation Checklist

Before implementation, verify:

- [ ] All 3 FCS patterns correctly identified
- [ ] Regex patterns tested on sample filenames
- [ ] Baseline detection tested (ISO, iso, Isotype, isotype)
- [ ] biological_sample_id grouping produces correct groups
- [ ] measurement_id is unique for all files
- [ ] NTA-FCS linking mapping obtained from client
- [ ] Edge cases handled (missing baseline, unknown patterns)
- [ ] Configuration file (`parser_rules.json`) updated with final patterns

---

## Next Steps

1. **Validate patterns** - Test regex on all actual filenames
2. **Get client input** - Obtain P# to L# mapping
3. **Implement parser** - Code the extraction logic in `parse_fcs.py`
4. **Test on sample data** - Verify correct extraction
5. **Update documentation** - Add any new patterns discovered

---

**Document Status:** DRAFT  
**Requires:** Client validation of passage-to-lot mapping  
**Implementation:** See `scripts/parse_fcs.py` and `scripts/parse_nta.py`  
**Configuration:** See `config/parser_rules.json`

