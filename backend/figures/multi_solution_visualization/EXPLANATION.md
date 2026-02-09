# Multi-Solution Mie Theory - Visual Explanation

## 📖 What is the Multi-Solution Problem?

When measuring extracellular vesicles (EVs) with flow cytometry, we use **side scatter (SSC)** intensity to estimate particle size. However, there's a fundamental problem:

**The Mie scattering curve oscillates** - it goes up and down multiple times as particle size increases!

This means **one SSC measurement can correspond to multiple different particle sizes**.

---

## 🔬 How We Solve It: Two-Wavelength Approach

### Step 1: Find ALL Possible Solutions (Graph 1)

We measure SSC at **two wavelengths**:
- **Blue (488 nm)**: Main SSC channel
- **Violet (405 nm)**: Second SSC channel (VSSC)

**Graph 1 shows:**
- The Mie theory curve oscillates with peaks and valleys
- A horizontal line at the measured SSC value
- **Where the line crosses the curve = possible particle sizes**

### Step 2: Use Ratio to Pick the Correct Solution (Graph 2)

Since Mie theory predicts different scattering at different wavelengths, each particle size has a unique "fingerprint":

**Wavelength Ratio** = VSSC (405nm) / BSSC (488nm)

**Graph 2 shows:**
- Theoretical ratio curve for each particle size
- Which solution's ratio matches our measured ratio
- The solution with the smallest ratio error is the **correct size**

---

## 📊 Examples from PC3 EXO1 Dataset

### Example 1: Event #630636 (2 Solutions)

**Measured Values:**
- Blue SSC (488nm): 1,307.4
- Violet SSC (405nm): 677.3
- Measured Ratio: 0.5181

**Possible Solutions Found:**

| Solution | Size (nm) | Theoretical Ratio | Ratio Error | Verdict |
|----------|-----------|-------------------|-------------|---------|
| 1 | 208.5 | 0.5564 | **7.4%** | ✅ **CORRECT** |
| 2 | 379.0 | 2.9021 | 460.2% | ❌ Wrong |

**Why 208.5 nm is correct:**
- The measured ratio (0.5181) is very close to the theoretical ratio for 208.5 nm (0.5564)
- Only 7.4% error vs 460% error for the 379 nm solution
- The ratio acts like a "fingerprint" to uniquely identify the particle size

---

### Example 2: Event #311014 (2 Solutions)

**Measured Values:**
- Blue SSC (488nm): 1,248.0
- Violet SSC (405nm): 721.2
- Measured Ratio: 0.5779

**Possible Solutions Found:**

| Solution | Size (nm) | Theoretical Ratio | Ratio Error | Verdict |
|----------|-----------|-------------------|-------------|---------|
| 1 | 209.0 | 0.5533 | **4.3%** | ✅ **CORRECT** |
| 2 | 377.5 | 3.0168 | 422.0% | ❌ Wrong |

**Why 209.0 nm is correct:**
- Even better match! Only 4.3% ratio error
- Shows consistency: both examples correctly identify ~210 nm particles
- Wrong solution (377.5 nm) is clearly ruled out by ratio

---

## 🎯 Key Insights

### Why This Matters:

1. **Single-wavelength is ambiguous**: Looking at just 488nm SSC, we can't tell if particle is 210nm or 380nm
   
2. **Dual-wavelength resolves ambiguity**: The ratio between two wavelengths uniquely identifies the correct size

3. **Scientifically rigorous**: Based on Mie theory, not empirical fitting

4. **Robust**: Works even with 10-15% measurement noise tolerance

### The Physics:

- **Mie scattering** depends on:
  - Particle diameter (d)
  - Wavelength (λ)
  - Refractive indices (n_particle, n_medium)

- Different wavelengths see **different relative scattering** from same particle
  
- This wavelength-dependent ratio is **unique for each size**

---

## 💡 Simplified Summary

**The Problem:**  
"One scatter measurement → multiple possible sizes"

**The Solution:**  
"Two scatter measurements → unique size via ratio matching"

**The Analogy:**  
Like identifying a person:
- Height alone? Many people match!
- Height + weight ratio? Unique identification!

---

## 📈 Graph Interpretation Guide

### Graph 1: "All Possible Solutions"

**Left Panel (488nm):**
- Blue curve = Mie theory prediction
- Red line = our measurement
- Red dots = where they intersect (possible sizes)

**Right Panel (405nm):**
- Purple curve = Mie theory at different wavelength
- Orange squares = where our solutions would be at 405nm
- Shows that solutions have different violet scatter

### Graph 2: "Ratio Disambiguation"

**Left Panel (Ratio Curve):**
- Green curve = theoretical VSSC/BSSC ratio vs size
- Red line = our measured ratio
- Stars/circles = which solution matches our ratio

**Right Panel (Bar Chart):**
- Height = how far off each solution's ratio is
- Green bar = best match (correct answer)
- Orange bars = poor matches (wrong answers)

---

## 🔧 Technical Parameters

- **Particle refractive index**: 1.40 (typical for EVs)
- **Medium refractive index**: 1.33 (PBS buffer)
- **Wavelengths**: 405 nm (violet), 488 nm (blue)
- **Size range**: 30-500 nm
- **Tolerance**: 15% (accounts for measurement noise)

---

## 📚 References

- **Mie theory**: Classical electromagnetic scattering theory (Gustav Mie, 1908)
- **miepython library**: Numerical implementation of Mie solutions
- **Multi-wavelength approach**: Standard technique in optical particle sizing

---

*Generated: January 28, 2026*  
*Dataset: PC3 EXO1.fcs (914,326 events)*  
*BioVaram EV Analysis Platform*
