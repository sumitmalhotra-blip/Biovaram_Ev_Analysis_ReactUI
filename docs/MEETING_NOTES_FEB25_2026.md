# Biovaram Weekly Customer Connect — Meeting Notes

**Date:** February 25, 2026  
**Participants:** Sumit Malhotra, Parvesh Reddy, Abhishek Reddy, Surya Pratap Singh, Dinesh Chandran (DH), Charmi Dholakia  
**Duration:** ~56 minutes

---

## Summary of Discussions

### 1. NanoFACS / FCS Sizing Pipeline (Presented by Sumit)

**What was shown:**
- The bead calibration system using nanoViS beads (Low + High) and the data sheet (Certificate of Analysis PDF)
- How the **k-factor** (instrument constant = 969.5) is derived from bead data to convert AU signals into physical nanometer sizes
- The **3.9% error margin** (k CV) on the 405 nm violet laser calibration
- Cross-comparison of FCS vs NTA results for PC3 EXO1 sample

**Current results:**
- FCS (Mie-calculated) median size: **~80–90 nm**
- NTA data for equivalent samples: **127–172 nm** median across all available NTA files
- Difference is expected because NTA samples are purified/fractionated (100 kDa ultrafiltration + SEC fractions) while FCS file is the bulk crude sample
- FCS captures more small particles, pushing the median lower

**Surya's response on bead data sheet:**
- Confirmed the Certificate of Analysis is the correct reference
- Asked important question: the nominal sizes (40, 105, 144 nm) have mean sizes of 44, 108, 142 nm respectively — **these are pools of particles with a distribution, not single sizes**
- Sumit confirmed this variability is accounted for in the code

---

### 2. Refractive Index Discussion

**Key exchange:**
- Surya confirmed: **biological EVs with lipid membranes have RI between 1.37 and 1.44**
- Surya said: "1.37 to 1.44 is acceptable number" and suggested **1.40 as the middle** of the range
- Sumit confirmed currently using **1.37** as default
- Surya approved 1.37 as acceptable: "then it should be good"

**Important for us:** Surya confirmed our RI range. This validates our sensitivity analysis. He's comfortable with 1.37–1.44 and suggested 1.40 as a midpoint alternative.

---

### 3. Q_sca vs Q_back / Collection Angles (Critical Technical Discussion)

**What Sumit explained:**
- Previously the code used **Q_back (180° backscatter only)** → was giving inflated sizes
- Changed to **Q_sca (total scatter — full circle)** → now getting better results, especially for small particles
- For small particles, light scatters evenly in all directions, so full circle is appropriate
- For bigger particles, the scatter pattern becomes directional (forward-peaked)

**Surya's response:**
- Suggested the common practice is **FWHM (Full Width at Half Maximum)** approach — not the full circle, not just backscatter, but the area under the curve at half the peak intensity
- Expressed concern that full circle "won't it be making things more tedious" and "if you specify a region that will be okay"
- **Ultimately asked Sumit to write the question formally in a document** so he can think about it and respond properly: *"Maybe you can write your question properly... I'll try to read and think and I'll come back to you"*

**Parvesh's question:** Can we reverse-engineer the collection angle from the bead calibration data?
- Surya: "I think it's a reverse engineering side, like I'm not sure"
- Surya has a **meeting with the instrument supplier (Beckman Coulter engineer) on March 2, 9:00 AM** — will raise the collection angle question there
- Also said he'll talk to **Dr. Jagan** (possibly today evening or tomorrow) to get the laser specifications and other instrument parameters

---

### 4. NTA Sample Strategy Change (Important Context from Surya)

**Surya revealed the lab has changed their strategy:**
- They are no longer studying crude/bulk samples via NTA
- Now using **molecular weight cutoff (MWCO) ultrafiltration cassettes/membranes** to purify first
- Terms in filenames: **"retentate" and "permeate"** at specific cutoffs (50 kDa, 100 kDa, 300 kDa)
- Goal: create formulations with specific EV size populations (e.g., 80 nm pool, 60 nm pool) and then characterize those specific fractions
- NTA detection range: **30–150 nm** (but nanoFACS/CytoFLEX starts from ~40 nm, so 30–40 nm is an NTA-only zone)
- **Future FCS files we receive will also be from purified fractions**, not just crude

**Impact on our cross-validation:** This means future FCS + NTA comparisons should be apples-to-apples (same purified fraction measured on both instruments), which will produce much better D50 agreement than our current comparison.

---

### 5. TEM Image Analysis (Presented by DH/Dinesh, explained by Parvesh)

**Features shown:**
- **Scale bar** — fully implemented
- **Intensity line profile tool** — draw a line from one point to another, get a graph of pixel intensities along that line. Use case: check membrane integrity by drawing from center to edge
- **Particle detection** — multiple methods available (Voronoiation and others), researcher can pick whichever suits their image best
- **Classification table** — shows count of each type (intact, not intact, needs review), clickable to navigate to that particle
- **CNN model** — implemented for classifying particles as intact vs not-intact (nomenclature changed from "viable/nonviable" per Parvesh's suggestion)

**Surya's feedback on TEM:**
- The intensity line profile is useful — this was originally his idea for detecting membrane breaks: *"Something like... the idea of implementing intensity was like this only"*
- Acknowledged some "needs review" particles are clearly not intact — e.g., particles 14 and 116 he flagged as obviously broken
- **CNN will give best results** but the training data is far too small
- Current dataset: **only 20 positive + 20 negative images** — CNN models typically train on thousands to millions
- Surya said: *"2020 is very small data set... you can expect that bad behavior"*
- Charmi mentioned also trying VIT (Vision Transformers) — Surya was not sure about VIT but said CNN itself will work if data is sufficient
- Surya agreed RNN is NOT suitable for image analytics
- For initial versions, showing the tools to users is fine; future versions can hide them once AI is good enough

**On training data:**
- Surya will ask the lab team to help create properly labeled datasets (cropped circles, expert-classified into intact/not-intact folders)
- He doesn't want to do the classification himself: *"I'm not trained biologist... I have very limited knowledge of biology"* — wants the wet lab experts to decide
- He already asked once, team agreed but hasn't delivered yet — will ask again

---

### 6. Western Blot Analysis (Presented by TJ/Dinesh)

**Features shown:**
- Heat map of band intensities
- 3D area graph (rotatable) showing intensity peaks at different positions

**Surya's detailed explanation of western blot reading:**

1. **Band location = protein size:** Heavy proteins migrate slowly (stay near top), light proteins migrate faster (move to bottom). The ruler/ladder (leftmost and rightmost columns are the same ladder) defines the molecular weight scale
2. **Band intensity = protein quantity:** The intensity percentage reflects the relative fraction of protein at that band
3. **Quantification formula:** `Relative intensity × control quantity = actual protein amount`
   - Example: If ruler band has 50 picograms at a given molecular weight, and sample intensity is 14.3% vs ruler's 9.7%, then: `(14.3 / 9.7) × 50 pg = actual protein content`
4. **Gel orientation:** Need a marker/cut mark to know which side was loaded (top vs bottom) — this is crucial and currently not determinable from the image alone
5. **Loading volume matters:** Users must provide how much volume they loaded per well (e.g., 5 µL), because overloading (e.g., 100 µL) creates artificially thick bands that don't reflect reality

**What the user needs to provide:**
- Which column is the **ruler/ladder**
- **Ruler specification** — the molecular weight range (e.g., 100 kDa → 10 kDa, or 250 kDa → 50 kDa, or 1000 kDa → 500 kDa)
- **Loading volume** per well
- **Control sample concentration** (e.g., 50 pg in 5 µL)

---

### 7. Module Packaging / EXE Delivery

- Sumit is restructuring the application from a monolithic tool into **separate modules**
- Will package as **EXE files** using **PyInstaller**
- **Target: ~2 weeks** to deliver individual module EXEs to Surya for lab testing
- NTA module is done feature-wise
- Surya confirmed he also uses PyInstaller, was curious about the approach

---

## Action Items

### Sumit (Dev Team)

| # | Action | Priority | Deadline | Status |
|---|--------|----------|----------|--------|
| S1 | **Write formal questions document** for Surya about: collection angles, Q_sca vs FWHM, instrument parameters needed | 🔴 High | This week | Not started |
| S2 | **Package NTA module as EXE** for Surya to test in lab | 🟡 Medium | ~2 weeks (by Mar 11) | In progress |
| S3 | **Update size categories** in the UI (mentioned new categories vs previous 3) | 🟡 Medium | Ongoing | In progress |
| S4 | Consider switching default RI to **1.40** (Surya's suggestion as midpoint) or at minimum offer it as an option | 🟢 Low | Next sprint | Not started |

### Surya

| # | Action | Priority | Deadline | Status |
|---|--------|----------|----------|--------|
| SU1 | **Get laser specifications** and machine parameters — talk to Dr. Jagan (today evening / tomorrow) | 🔴 High | By Feb 27 | Pending |
| SU2 | **Raise collection angle question** at instrument supplier meeting | 🔴 High | March 2, 9 AM | Scheduled |
| SU3 | **Provide all 4 laser specs** (violet, blue/green, yellow, red) and other CytoFLEX nano parameters | 🔴 High | After Mar 2 meeting | Pending |
| SU4 | **Review Sumit's formal questions document** and respond with technical guidance | 🟡 Medium | After receiving doc | Pending |
| SU5 | **Get labeled TEM training images** from wet lab team (intact/not-intact folders, expert-classified) | 🟡 Medium | Ongoing | Asked before, will ask again |
| SU6 | **Provide western blot specifications** — ruler info, loading volumes, molecular weights, example annotated image | 🟢 Low | When available | Pending |

### DH / Charmi (TEM Team)

| # | Action | Priority | Deadline | Status |
|---|--------|----------|----------|--------|
| D1 | **Change nomenclature** from "viable/nonviable" to **"intact/not intact"** | 🔴 High | Immediate | Not started |
| D2 | **Continue CNN training** with whatever data is available; be ready to retrain when Surya provides more images | 🟡 Medium | Ongoing | In progress |
| D3 | **Try VIT (Vision Transformers)** as Charmi suggested — compare with CNN results | 🟢 Low | Exploratory | Not started |

### TJ (Western Blot Team)

| # | Action | Priority | Deadline | Status |
|---|--------|----------|----------|--------|
| T1 | **Implement user input form** for: ruler column selection, ruler specification (kDa range), loading volume, control concentration | 🟡 Medium | Next sprint | Not started |
| T2 | **Add gel orientation detection/input** — user needs to specify which end is heavy vs light | 🟡 Medium | Next sprint | Not started |
| T3 | **Implement quantification formula** — relative intensity × control quantity = actual protein content | 🟡 Medium | After T1 | Not started |

---

## Key Decisions Made

1. **RI range confirmed:** 1.37–1.44 for biological EVs. Current default of 1.37 approved. 1.40 suggested as alternative midpoint.
2. **3.9% calibration error margin** acknowledged as acceptable by Surya: *"3.5% is not a bad number"*
3. **Collection angle question deferred** — Surya will raise with Beckman Coulter engineer on March 2
4. **TEM nomenclature:** "Viable/Nonviable" → **"Intact/Not Intact"**
5. **Future samples will be purified** (MWCO fractions) — both FCS and NTA will be on same purified fraction, enabling proper cross-validation
6. **Module delivery plan:** Individual EXE files via PyInstaller within ~2 weeks

---

## Key Quotes

> **Surya on RI:** *"For exosomes or any biological origin material which are having the lipid membrane... refractive index varies between 1.37 to 1.44."*

> **Surya on error margin:** *"3.5% is not a bad number."*

> **Surya on collection angles:** *"Collection angle we cannot provide, that's the... I think it's a reverse engineering side."* — Will ask instrument supplier on March 2.

> **Surya on Q_sca approach:** *"Most commonly used practice is half angle... FWHM... if you go for the whole circle, won't it be making things more tedious?"*

> **Surya on CNN data:** *"2020 is very small data set... models are trained on some thousand, 10,000, even some cases million... CNN has played a very nice role for low resolution radiology, here also you can expect something nice."*

> **Surya on writing questions:** *"Sumit I request maybe you can write your question properly... I'll try to read and think and I'll come back to you."*

---

## Upcoming Milestones

| Date | Event |
|------|-------|
| Feb 26–27 | Surya talks to Dr. Jagan about laser/instrument specs |
| This week | Sumit sends formal questions document to Surya |
| **March 2, 9 AM** | **Surya's meeting with instrument supplier engineer — collection angles** |
| ~March 11 | EXE module delivery to Surya for lab testing |
| Ongoing | Surya getting labeled TEM images from wet lab team |

---

## Open Questions (For Surya's Document)

**Subject: Technical Questions — Mie Scattering Model & CytoFLEX nano Parameters**

Hi Surya,

As discussed in yesterday's meeting, here are the questions written out properly. Please take your time reviewing — any input will help us improve the sizing accuracy significantly.

---

### Question 1: SSC Detector Collection Angles

Currently our Mie scattering model computes **Q_sca** — the total scattering efficiency integrated over all angles (full 4π sphere, i.e., the "full circle" I mentioned in the call). This works well for small particles (<100 nm) because their scattering is nearly isotropic (light goes in all directions equally). However, the actual SSC detector on the CytoFLEX nano only collects light within a specific angular window.

**What we need:**
- What is the SSC collection angle range on the CytoFLEX nano? (e.g., 15°–150°? or some other range?)
- Is it different for the Violet SSC (VSSC, 405 nm laser) vs the Blue SSC (BSSC, 488 nm laser)?
- Can this be obtained from Beckman Coulter in the March 2 meeting?

If we know the angle range, we can integrate the Mie scattering function only within those angles rather than over the full sphere, which would make the model more physically accurate — especially for particles above 100 nm where scattering becomes directional.

---

### Question 2: Q_sca (Full Sphere) vs FWHM vs Specific Angle Integration

You mentioned that the common practice is **FWHM (Full Width at Half Maximum)** — taking the area under the curve at half the peak intensity. Currently we have three possible approaches:

| Approach | How It Works | Current Status |
|----------|-------------|----------------|
| **Q_sca (full sphere)** | Integrate scattering over all 360° | ✅ What we're using now |
| **FWHM** | Use half-maximum of the scattering lobe | ❌ Not implemented |
| **Specific angle range** | Integrate only within detector's real angular window | ❌ Needs angle specs from Beckman |

**Our question:** Which approach should we prioritize?
- **Option A:** Keep Q_sca for now (works well for small EVs, our bead validation shows <1% error)
- **Option B:** Implement FWHM as you suggested
- **Option C:** Wait for the real angle specs from Beckman and implement exact angular integration

Our bead calibration currently recovers 80 nm → 79.4 nm, 108 nm → 109.0 nm, 142 nm → 141.7 nm using Q_sca, which is very accurate. So the full-sphere approach may be fine for the EV size range (30–150 nm) even if it's not technically perfect. Your guidance on whether FWHM would be more appropriate for biological samples would be very helpful.

---

### Question 3: Complete Laser Specifications for All Four Lasers

You mentioned the CytoFLEX nano has four lasers (violet, blue, yellow/green, red). We currently use:
- **Violet (405 nm)** — as primary for small EV sizing (VSSC1-H channel)
- **Blue (488 nm)** — as secondary for dual-wavelength disambiguation (BSSC-H channel)

**What we need for each laser:**
- Exact wavelength (nm)
- Power level (mW)
- Beam geometry / spot size (if available)
- Which channels/detectors are associated with each laser
- Any other optical parameters the instrument supplier can provide

This will help us set up the correct wavelength parameters in our Mie lookup tables and potentially expand the analysis to use additional wavelengths for better accuracy.

---

### Question 4: Can We Reverse-Engineer the Collection Angle from Bead Calibration?

Parvesh raised this idea in the meeting. The logic would be:

1. We know the bead sizes exactly (80, 108, 142 nm)
2. We know the bead refractive index (1.591 at 590 nm, ~1.634 at 405 nm via Cauchy dispersion)
3. We measure the AU signal for each bead on the instrument
4. Using Mie theory, we can compute the **angle-resolved** scattering pattern for each bead
5. By finding which angular range produces a k-factor that is **consistent across all bead sizes**, we could reverse-engineer the detector's collection angle

**Is this a valid approach scientifically?** We already see that k varies slightly across bead sizes (929–1019, CV = 3.9%), which could partly be because the angular collection fraction varies with particle size. If we find the angle range that minimizes k variation, that might be the real detector geometry.

Would this kind of reverse-engineering be accepted in the research community, or should we rely on manufacturer specifications?

---

### Question 5: Upcoming Sample Format & Cross-Validation Strategy

You mentioned the lab has changed strategy — now purifying samples using MWCO cassettes (50 kDa, 100 kDa, 300 kDa) before NTA characterization. Filenames will include "retentate" and "permeate" terms.

**Our questions:**
- Will future **FCS/nanoFACS runs also be on these purified fractions** (not just NTA)?
- If yes, this would let us do proper FCS vs NTA cross-validation on the **exact same preparation** — which would be much more meaningful than our current comparison (bulk FCS vs fractionated NTA)
- What size range should we expect per fraction? You mentioned 30–150 nm detection range for NTA and 40 nm+ for nanoFACS
- Should we adjust our default analysis range (currently 20–500 nm) to match the expected EV range (30–150 nm)?

---

Looking forward to your inputs. No rush — whenever you get a chance to review. The March 2 meeting with Beckman Coulter should help answer Questions 1, 3, and possibly 4.

Best regards,
Sumit

---

*Notes compiled from meeting transcript. Some technical terms may be slightly paraphrased from spoken language.*
