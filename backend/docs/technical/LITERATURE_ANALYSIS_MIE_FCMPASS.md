# Literature Analysis: Mie Scattering & FCMPASS Implementation Gap

**Date:** November 18, 2025  
**Purpose:** Analyze PDF documents in Literature/ folder and identify implementation gaps  
**Status:** 🚨 CRITICAL - Mie scatter theory NOT properly implemented

---

## 📚 Literature Files Review

### Files in `Literature/` Folder:
1. **FCMPASS_Software-Aids-EVs-Light-Scatter-Stand.pdf**
2. **Mie functions_scattering_Abs-V1.pdf**
3. **Mie functions_scattering_Abs-V2.pdf**

---

## 🔍 Current Implementation Analysis

### ✅ What We HAVE Implemented:

1. **Simplified Particle Size Calculation** (`src/visualization/fcs_plots.py`):
   ```python
   def calculate_particle_size(data, fsc_channel='VFSC-H'):
       fsc_norm = (fsc_values - min) / (max - min)  # Normalize 0-1
       particle_size_nm = 30 + (sqrt(fsc_norm) * 120)  # Map to 30-150nm
   ```
   
   **Issues:**
   - ❌ Not using actual Mie scattering theory
   - ❌ No wavelength-dependent calculations
   - ❌ No refractive index considerations
   - ❌ Simple linear/sqrt mapping (not physically accurate)
   - ⚠️ Labeled as "simplified approximation - integrate Mie scatter for accuracy"

2. **Size vs Intensity Plotting** (`src/visualization/size_intensity_plots.py`):
   - ✅ Uses particle_size_nm (but from simplified calculation above)
   - ✅ Plots Size vs Fluorescence Intensity
   - ✅ Identifies clustering at specific sizes
   - ❌ Size values not physically accurate (no Mie theory)

---

## 🚨 CRITICAL GAPS - What's MISSING:

### 1. **Mie Scattering Theory Implementation**

**What Mie Theory Should Provide:**
- Relationship between:
  - Particle size (diameter in nm)
  - Light wavelength (λ: 405nm, 488nm, 561nm, 633nm, etc.)
  - Refractive index (n) of particles and medium
  - Scatter intensity (FSC/SSC values)

**Mie Theory Calculations:**
```python
# MISSING: Proper Mie scatter calculation
def calculate_mie_scatter(diameter_nm, wavelength_nm, refractive_index_particle, refractive_index_medium):
    """
    Calculate scattering efficiency using Mie theory.
    
    Returns:
        Q_scatter: Scattering efficiency
        Q_absorption: Absorption efficiency
        intensity_forward: Forward scatter intensity
        intensity_side: Side scatter intensity
    """
    # Size parameter
    x = (π * diameter_nm) / wavelength_nm
    
    # Relative refractive index
    m = refractive_index_particle / refractive_index_medium
    
    # Mie coefficients (requires series expansion)
    a_n, b_n = calculate_mie_coefficients(x, m)
    
    # Scattering cross-section
    Q_scatter = calculate_scattering_efficiency(a_n, b_n, x)
    
    return Q_scatter, intensity_forward, intensity_side
```

**Currently:** We use `sqrt(normalized_FSC)` which has NO physical basis!

### 2. **FCMPASS Software Integration**

**What FCMPASS Provides:**
- Light scatter standardization for EVs
- Calibration using reference beads (known sizes + refractive indices)
- Wavelength-specific scatter patterns
- Conversion: Scatter Intensity → Physical Diameter

**Missing from Our Codebase:**
```python
# MISSING: FCMPASS-style calibration
class FCMPASSCalibrator:
    """
    Calibrate FSC/SSC to particle size using reference beads.
    
    Reference beads: 100nm, 200nm, 300nm polystyrene (n=1.59)
    Sample medium: PBS or similar (n=1.33)
    Wavelengths: 405nm (violet), 488nm (blue), 561nm (yellow)
    """
    
    def __init__(self, bead_data, wavelengths):
        self.bead_sizes = [100, 200, 300]  # nm
        self.bead_refractive_index = 1.59  # Polystyrene
        self.medium_refractive_index = 1.33  # PBS
        self.wavelengths = wavelengths
    
    def calibrate(self, fsc_values, ssc_values):
        """
        Use bead measurements to create calibration curve:
        Known Size → Measured FSC/SSC → Create lookup/interpolation
        """
        # Fit Mie theory curve to bead data
        # Apply to unknown particles
        pass
    
    def fsc_to_diameter(self, fsc_value, wavelength):
        """
        Convert FSC reading to physical diameter using Mie theory.
        """
        pass
```

### 3. **Wavelength-Specific Analysis**

**What We Need:**
```python
# MISSING: Multi-wavelength scatter analysis
class MultiWavelengthAnalyzer:
    """
    Analyze scatter at different wavelengths.
    
    ZE5 Flow Cytometer Lasers:
    - 405nm (violet): V-SSC, VFSC
    - 488nm (blue): B531 fluorescence
    - 561nm (yellow): Y595 fluorescence
    - 633nm (red): R613 fluorescence
    """
    
    def analyze_scatter_pattern(self, particle_size, particle_refractive_index):
        """
        Calculate expected scatter at each wavelength.
        Compare with measured values.
        """
        scatter_405nm = mie_scatter(particle_size, 405, refractive_index)
        scatter_488nm = mie_scatter(particle_size, 488, refractive_index)
        scatter_561nm = mie_scatter(particle_size, 561, refractive_index)
        
        # Which wavelength scatters strongest for this size?
        # Example: 80nm particles scatter blue (488nm) strongly
        return scatter_pattern
```

**Why This Matters:**
- From meeting: "CD9 at ~80nm scattering blue light (B531)"
- Different sizes scatter different wavelengths preferentially
- This is the biological meaning Parvesh mentioned!

---

## 📊 Implementation Priority

### 🔥 HIGH PRIORITY (Immediate - This Week):

1. **Create Mie Scattering Module** (`src/physics/mie_scatter.py`):
   ```python
   class MieScatterCalculator:
       """
       Implements Mie scattering theory for particle size determination.
       
       References:
       - Literature/Mie functions_scattering_Abs-V1.pdf
       - Literature/Mie functions_scattering_Abs-V2.pdf
       """
       
       def __init__(self, wavelength_nm, n_particle, n_medium):
           self.wavelength = wavelength_nm
           self.n_particle = n_particle
           self.n_medium = n_medium
       
       def calculate_scatter_efficiency(self, diameter_nm):
           """Calculate Q_scatter using Mie theory."""
           pass
       
       def diameter_from_scatter(self, scatter_intensity):
           """Inverse problem: scatter → diameter."""
           pass
   ```

2. **Create FCMPASS Calibration Module** (`src/calibration/fcmpass_calibrator.py`):
   ```python
   class FCMPASSCalibrator:
       """
       Implement FCMPASS-style calibration workflow.
       
       Reference:
       - Literature/FCMPASS_Software-Aids-EVs-Light-Scatter-Stand.pdf
       """
       
       def load_bead_data(self, bead_file):
           """Load reference bead measurements."""
           pass
       
       def create_calibration_curve(self):
           """Fit Mie theory to bead data."""
           pass
       
       def calibrate_sample(self, fcs_data):
           """Apply calibration to convert FSC → diameter."""
           pass
   ```

3. **Update Existing Functions**:
   - Replace `calculate_particle_size()` with Mie-based calculation
   - Add calibration step before size calculation
   - Update warnings about "simplified approximation"

### 🔄 MEDIUM PRIORITY (Next Week):

4. **Multi-Wavelength Analysis**:
   - Calculate expected scatter for 405nm, 488nm, 561nm, 633nm
   - Compare measured vs expected for each particle size
   - Identify size ranges with wavelength-specific scatter peaks

5. **Validation Against NTA**:
   - NTA provides true size distribution (camera-based measurement)
   - Compare Mie-calculated sizes with NTA sizes
   - Tune refractive index assumptions if needed

### ⏳ LOW PRIORITY (Future):

6. **Advanced Calibration**:
   - Temperature correction
   - Viscosity effects
   - Non-spherical particle corrections

---

## 🧪 Validation Strategy

### Step 1: Reference Bead Validation
```python
# Test with polystyrene beads (known size + refractive index)
bead_100nm = load_bead_data("100nm_polystyrene.fcs")
calculated_size = mie_scatter_analysis(bead_100nm)

assert abs(calculated_size - 100) < 10  # Within 10nm
```

### Step 2: Cross-Validation with NTA
```python
# Compare FCS (Mie-based) vs NTA (camera-based) size distributions
fcs_sizes = mie_calibrated_sizes(fcs_data)
nta_sizes = load_nta_sizes(nta_data)

correlation = correlate(fcs_sizes, nta_sizes)
assert correlation > 0.8  # Strong agreement
```

### Step 3: Biological Validation
```python
# Known: CD9 expected at ~80nm
cd9_sample = load_fcs_data("CD9_marker.fcs")
cd9_sizes = mie_calibrated_sizes(cd9_sample)

# Should see peak around 80nm
peak_size = find_peak(cd9_sizes)
assert 70 < peak_size < 90  # CD9 range
```

---

## 📋 Action Items

### For Backend Team (Sumit):

**This Week (Nov 18-22):**
- [ ] **Day 1:** Review Mie theory PDFs in Literature/ folder
- [ ] **Day 1-2:** Implement basic Mie scatter calculator (`src/physics/mie_scatter.py`)
- [ ] **Day 3:** Create FCMPASS-style calibration module
- [ ] **Day 4:** Integrate with existing `calculate_particle_size()`
- [ ] **Day 5:** Test with reference data and validate

**Required Python Libraries:**
```bash
pip install miepython  # Mie scattering calculations
pip install scipy     # Optimization for inverse calculations
```

**Reference Implementation:**
```python
import miepython

def calculate_mie_size(fsc_intensity, wavelength=405, n_particle=1.45, n_medium=1.33):
    """
    Use miepython library to calculate particle size from scatter.
    
    Args:
        fsc_intensity: Measured forward scatter intensity
        wavelength: Laser wavelength (nm)
        n_particle: Refractive index of EV (~1.37-1.45)
        n_medium: Refractive index of medium (PBS ~1.33)
    """
    # Convert FSC to scattering efficiency
    m = n_particle / n_medium  # Relative refractive index
    
    # Iterate to find diameter that matches measured scatter
    for diameter in range(30, 200):  # Search 30-200nm
        x = np.pi * diameter / wavelength
        qext, qsca, qback, g = miepython.mie(m, x)
        
        if qsca matches fsc_intensity:
            return diameter
    
    return None
```

### For UI Team (Mohith):
- [ ] Provide calibration bead data interface
- [ ] Add refractive index input fields (particle + medium)
- [ ] Display Mie-calculated sizes in UI
- [ ] Show wavelength-specific scatter patterns

### For Scientific Team (Parvesh):
- [ ] Provide calibration bead measurements (if available)
- [ ] Confirm refractive index values for EVs
- [ ] Validate Mie-calculated sizes against expected values

---

## 🎯 Expected Improvements

### Current State (Simplified):
```
FSC Value: 12,453 → particle_size_nm = 87.3
```
**Problem:** 87.3nm has NO physical basis, just normalized mapping

### After Mie Implementation:
```
FSC Value: 12,453
Wavelength: 405nm
Refractive Index (EV): 1.40
Refractive Index (PBS): 1.33
→ Mie Calculation → particle_size_nm = 82.1 ± 3.4
```
**Benefit:** Physically accurate, accounts for wavelength + material properties

### Scientific Impact:
- ✅ Accurate particle size measurements
- ✅ Wavelength-dependent scatter patterns
- ✅ Can explain WHY CD9 scatters blue light at 80nm
- ✅ Calibration against known standards
- ✅ Cross-validation with NTA possible

---

## 📖 Reading Priority

### Must Read (This Week):
1. **FCMPASS_Software-Aids-EVs-Light-Scatter-Stand.pdf**
   - Focus: Calibration workflow
   - Focus: Reference bead usage
   - Focus: Light scatter standardization

2. **Mie functions_scattering_Abs-V2.pdf** (start here)
   - Focus: Mie theory equations
   - Focus: Size parameter calculations
   - Focus: Scattering efficiency

### Reference (As Needed):
3. **Mie functions_scattering_Abs-V1.pdf**
   - Focus: Original Mie formulations
   - Focus: Series expansion details

---

## 🚨 CRITICAL REALIZATION

**From Meeting Context:**
> "Show which particle sizes scatter which wavelengths"
> "CD9 expected at ~80nm scattering blue light (B531)"

**This requires Mie theory!** Our current sqrt(normalized_FSC) cannot explain:
- WHY 80nm scatters blue (488nm) preferentially
- HOW to predict scatter intensity for a given size
- WHICH wavelength to expect for different particle sizes

**Without Mie implementation:**
- ❌ Size calculations are arbitrary
- ❌ Cannot validate against physics
- ❌ Cannot explain biological observations
- ❌ Cannot cross-validate with NTA properly

**With Mie implementation:**
- ✅ Sizes have physical meaning
- ✅ Can predict scatter patterns
- ✅ Can explain CD9 at 80nm + blue scatter
- ✅ Can validate against known standards

---

## 📊 Comparison Table

| Feature | Current (Simplified) | With Mie Theory |
|---------|---------------------|-----------------|
| **Size Calculation** | `sqrt(normalized_FSC) * 120 + 30` | Mie inversion with wavelength |
| **Physical Accuracy** | None (arbitrary mapping) | Physically accurate |
| **Wavelength Dependence** | Ignored | Explicitly calculated |
| **Refractive Index** | Not used | Required input |
| **Calibration** | Min/max normalization | Reference bead calibration |
| **Cross-Validation** | Not possible | Can compare with NTA |
| **Scientific Validity** | ❌ Not publishable | ✅ Scientifically sound |
| **Explains Biology** | ❌ Cannot explain scatter patterns | ✅ Explains size-wavelength relationship |

---

## 🎓 Summary

### Current Status: 🔴 **INCOMPLETE**
- We have basic plotting framework
- Particle size calculation is placeholder only
- No Mie scattering theory implemented
- Cannot explain biological observations

### What Literature Provides: 📚
- **Mie Theory PDFs:** Mathematical foundation for light scattering
- **FCMPASS Paper:** Standardization workflow for EVs
- Both are ESSENTIAL for proper implementation

### Required Action: ⚡ **URGENT**
1. Implement Mie scattering calculator (this week)
2. Create FCMPASS-style calibration (this week)
3. Replace simplified size calculation (this week)
4. Validate with reference data (this week)

### Impact: 🎯
- **Scientific:** Physically accurate measurements
- **Biological:** Can explain marker-size-wavelength relationships
- **Validation:** Cross-check with NTA becomes meaningful
- **Publication:** Results become scientifically defensible

---

**Status:** 📋 DOCUMENTED - Ready for implementation  
**Next Step:** Review PDFs and implement Mie scatter module  
**Timeline:** Complete by November 22, 2025 (4 days)
