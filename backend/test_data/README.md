# Test Data Files

**Purpose:** Sample files for testing parsers during development

**Date:** November 13, 2025

---

## FCS Test Files (nanoFACS)

Copied from: `nanoFACS/CD9 and exosome lots/`

1. **L5+F10+ISO.fcs** - Baseline (isotype control) for biological sample L5_F10
2. **L5+F10+CD9.fcs** - Test measurement with CD9 antibody
3. **L5+F10+ONLY EXO.fcs** - Exosome-only control (no antibody)

**Use Case:**
- Test baseline detection (`ISO` keyword)
- Test biological_sample_id extraction (should all be `L5_F10`)
- Test measurement_id generation
- Test baseline comparison calculations (CD9 vs ISO delta)

---

## NTA Test Files

Copied from: `NTA/EV_IPSC_P1_19_2_25_NTA/`

1. **20250219_0001_EV_ip_p1_F8-1000_size_488_11pos.txt** - 11-position measurement
2. **20250219_0001_EV_ip_p1_F8-1000_size_488.txt** - Summary file

**Use Case:**
- Test NTA filename parsing (passage, fraction extraction)
- Test biological_sample_id extraction (should be `P1_F8`)
- Test 11-position data handling
- Test NTA-FCS linking (P1_F8 → L5_F8 mapping)

---

## Expected Parsing Results

### FCS Files:

| Filename | biological_sample_id | measurement_id | antibody | is_baseline |
|----------|---------------------|----------------|----------|-------------|
| L5+F10+ISO.fcs | L5_F10 | L5_F10_ISO | ISO | True |
| L5+F10+CD9.fcs | L5_F10 | L5_F10_CD9 | CD9 | False |
| L5+F10+ONLY EXO.fcs | L5_F10 | L5_F10_ONLY_EXO | - | False |

### NTA Files:

| Filename | biological_sample_id | passage | fraction | dilution |
|----------|---------------------|---------|----------|----------|
| 20250219_0001_EV_ip_p1_F8-1000_size_488_11pos.txt | P1_F8 | 1 | 8 | 1000 |

---

## Notes

- **Do NOT commit these files to Git** - They are in `.gitignore`
- Replace with your own test files if needed
- FCS files are ~100-200 KB each
- NTA files are ~10-50 KB each

