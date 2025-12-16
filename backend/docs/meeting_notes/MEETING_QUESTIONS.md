# Team Meeting Questions - Data Processing & Normalization Clarifications

**Date:** November 18, 2025  
**Meeting Date:** November 18, 2025 (Meeting Completed)  
**Last Updated:** November 28, 2025 (Added Nov 27 meeting notes)  
**Purpose:** Clarify data processing standards, normalization procedures, and cross-instrument sample linking  
**Context:** Currently developing ML pipeline for integrated FCS + NTA analysis

**Status:** ✅ MEETING COMPLETED - Answers recorded below  
**Next Steps:** Send remaining unanswered questions to team for clarification

---

## 📝 **MEETING UPDATE - November 27, 2025 (Weekly Customer Connect)**

### **Attendees:**
Sumit, Parvesh, Surya, Jaganmohan Reddy, Abhishek, Charmi

### **Demo Outcome:**
- ✅ Backend + UI integration demonstrated successfully
- ✅ NTA tab added to UI, graph pinning feature planned
- ✅ Client satisfied with analysis speed and functionality

### **NEW REQUIREMENT: User-Defined Size Ranges (from Jaganmohan)**

**Key Decision:** DO NOT hardcode size categories. Let users choose dynamically.

**Jaganmohan's Guidance:**
- "Give them the choice to select what range they want"
- "They will have the freedom to operate - we will not be the persons who judge"
- Different scientific applications need different segmentation

**Size Categories Mentioned:**
| Category | Range | Use Case |
|----------|-------|----------|
| Small vesicles | 30-100 nm | One categorization |
| Alternative | 30-150 nm | Another categorization |
| Custom | User-defined | Scientific flexibility |

**Implementation Required:**
- Add UI controls: Start range, End range
- Display: "Particles in {start}-{end}nm: {count}"
- Allow multiple segments: 30-100, 100-150, etc.

### **Anomaly Detection Vision (Future AI Feature)**

**Jaganmohan's Request:**
- System should proactively find anomalies across parameter combinations
- Not just manual parameter selection
- Alert: "You're getting some anomaly here - look into this"

**Status:** Blocked - waiting for AI/Data Cloud credentials

### **Pending Items from Jaganmohan:**
- [ ] List of specific graphs/parameters to check for anomalies
- [ ] Which parameter combinations AI should analyze
- "I'll sit down and write those points"

### **New Data Timeline:**
- BioVaram establishing new protocols
- New experimental data expected in ~2 weeks
- Surya analyzing recent data internally first

### **Meeting Schedule Changed:**
- **OLD:** Thursdays 7:50 PM
- **NEW:** Wednesdays 4:00-5:00 PM (recurring)

---

## 📝 **KEY INSIGHTS FROM MEETING (November 18, 2025)**

### **Complete Process Flow (As Explained by Parvesh):**

**STEP 1: NTA Analysis (Size Measurement)**
- Sample goes to NTA machine first (when size information is needed)
- Provides concentration at different particle sizes (e.g., particles at 40nm, 50nm, etc. per cm³)
- Gives baseline understanding of size distribution

**STEP 2: NanoFACS Analysis (Marker Detection + Size)**
- Same sample goes to NanoFACS machine
- Fluorescent markers added to identify specific proteins (CD9, CD81, etc.)
- Team already knows which proteins scatter which wavelengths
- Example: CD9 expected at ~80nm scattering blue light (B531)
- **Key Decision Point:** If expected marker not found at expected size → discard sample
- If marker found at correct size → proceed to next step

**STEP 3: TEM Analysis (Viability Check)**
- Sample sent out for TEM (Transmission Electron Microscopy)
- Manual visual inspection of electron microscope images
- Check if 80nm particles have intact cell membranes
- Broken membranes → sample useless
- Viable particles → proceed to final step

**STEP 4: Western Blot (Protein Confirmation)**
- Final validation step
- Provides atomic mass of proteins
- Can calculate chemical formula backwards from atomic mass
- Confirms protein identity definitively

**STEP 5 & 6: Future Steps (Not Yet Implemented)**
- Additional chemical composition analysis
- Currently out of scope for Phase 1

**NOTE:** Sometimes NTA is skipped if exact size measurement not needed for that experiment.

---

## 🔬 **1. Sample Identification & Cross-Instrument Linking**

### **Critical Questions:**

**Q1.1:** How should samples be linked between FCS and NTA instruments?
- **Current Issue:** Sample IDs don't match between instruments (e.g., FCS: "Exo Control", NTA: "EV_IPSC_P1")
- **Impact:** Cannot perform cross-validation or integrated analysis
- **Need:** Standard sample naming convention or mapping table

**✅ ANSWER (Parvesh - Nov 18, 2025):**
- **Current Status:** NO single sample used across all four machines in existing data
- **Data Provided So Far:** For testing/understanding only, not for ML training
- **Solution Planned:** Team will provide NEW data with same samples across instruments
- **Timeline:** After UI completion, team will run 2-3 experiments with proper cross-instrument samples
- **Action Item:** Wait for clean experimental data before implementing cross-validation

**Q1.2:** Is there a master sample tracking spreadsheet that maps biological samples across instruments?
- Example: "Biological Sample 001" → FCS file "Exo Control.fcs" + NTA folder "EV_IPSC_P1_19_2_25_NTA"
- If yes, where is it located?
- If no, should we create one?

**✅ ANSWER (Parvesh - Nov 18, 2025):**
- **Current Status:** Does NOT exist
- **Reason:** Existing data is for exploration/understanding, not production
- **Future Approach:** Team will provide properly tracked samples after UI demonstration
- **Action Item:** Wait for properly structured experimental data

**Q1.3:** What do the sample name components mean?
- FCS samples: "Exo + 0.25ug CD81 SEC.fcs" → What is "SEC"? (Size Exclusion Chromatography?)
- NTA samples: "EV_IPSC_P1_19_2_25_NTA" → What does "P1" mean? (Passage 1?)
- Are there other abbreviations we should standardize?

**✅ PARTIAL ANSWER (Parvesh - Nov 18, 2025):**
- **SEC:** Size Exclusion Chromatography ✅ CONFIRMED
- **Centri:** Centrifugation method
- **CD81, CD9:** Protein marker names (not abbreviations)
- **ISO:** Isotype control
- **P1, P2:** ❓ Still unclear (likely Passage number, needs confirmation)
- **Action Item:** Add to remaining questions list

**Q1.4:** How should replicates be identified and grouped?
- Technical replicates (same sample, multiple measurements)
- Biological replicates (different samples, same condition)
- Current assumption: "_rep1", "_rep2" suffix indicates technical replicates

**❓ NOT ANSWERED - Needs clarification**

---

## 📊 **2. Normalization Standards & Procedures**

### **FCS Data Normalization:**

**Q2.1:** What is the standard normalization method for FCS flow cytometry data?
- Are we using:
  - Biexponential transformation?
  - Logicle transformation?
  - Linear scaling to percentiles?
  - Channel-specific normalization?
- **Current Status:** Using raw data with log scale visualization only

**❓ NOT ANSWERED - Still needs clarification from Surya (best practices document pending)**

**Q2.2:** Should FCS intensities be normalized to:
- Total event count?
- Specific control samples (blanks/beads)?
- Instrument-specific calibration beads?
- None (raw values are sufficient)?

**❓ NOT ANSWERED - Pending Surya's best practices document**

**Q2.3:** How do we handle instrument drift across batches?
- Are there daily calibration standards?
- Should we normalize by acquisition date?
- Compensation matrix application procedure?

**❓ NOT ANSWERED - Pending Surya's best practices document**

**Q2.4:** What are the QC thresholds for FCS data acceptance?
- Minimum event count per sample? (Current default: 1000)
- Maximum event rate (to avoid coincidence)?
- Signal-to-noise ratio requirements?
- FSC/SSC gating standards?

**❓ NOT ANSWERED - Pending Surya's best practices document**

**⚠️ ACTION ITEM:** Parvesh will remind Surya to provide best practices document (mentioned working on it)

### **NTA Data Normalization:**

**Q2.5:** What is the standard normalization for NTA concentration measurements?
- Should concentrations be normalized to:
  - Dilution factor? (Currently: yes, stored in metadata)
  - Protein concentration?
  - Sample volume?
  - Cell count in source material?

**❓ NOT ANSWERED - Needs clarification**

**Q2.6:** How should size distributions be normalized?
- By total particle count (percentage)?
- By peak height?
- By area under curve?
- **Current Status:** Using raw percentages from instrument

**❓ NOT ANSWERED - Needs clarification**

**Q2.7:** What are acceptable NTA measurement quality criteria?
- Camera level range? (Currently checking 14-16)
- Minimum particles per frame?
- Temperature stability requirements? (±1°C?)
- Dilution factor validation?

**❓ NOT ANSWERED - Needs clarification**

**Q2.8:** How do we handle measurements at different dilutions?
- Linear back-calculation to stock concentration?
- Dilution series validation approach?
- Which dilution factor should be considered "standard"?

**❓ NOT ANSWERED - Needs clarification**

---

## 🔗 **3. Baseline & Control Sample Definition**

**Q3.1:** What defines a "baseline" or "control" sample?
- **Current Assumptions:**
  - Samples with "control", "blank", "water", "media" in name
  - Isotype controls (ISO)
  - No treatment samples
- Are these correct?

**✅ PARTIAL ANSWER (Parvesh - Nov 18, 2025):**
- **Water samples:** Substrate/medium used (water-based gel) - particles suspended in this
- **Water is baseline material:** All exosomes are placed in this medium for measurement
- **Blank/Water files:** Used to establish background/noise levels
- **ISO (Isotype controls):** ✅ CONFIRMED as controls
- **Control samples:** Baseline for comparison (exosomes without treatment)
- **Action Item:** Confirm if water/blank should be subtracted as background or used as normalization reference

**Q3.2:** Should baseline comparisons be:
- Per-experiment batch?
- Per-passage (for cell-derived EVs)?
- Per-preparation method (SEC, centrifugation, etc.)?
- Across all experiments (global baseline)?

**✅ ANSWER (Parvesh - Nov 18, 2025):**
- **Recommendation:** Use GLOBAL AVERAGED BASELINE
- **Reasoning:** If specific control sample used, users with different controls will get incorrect results
- **Approach:** Calculate average baseline from all data, allow users to edit/adjust values
- **Benefit:** Users can adapt baseline to their specific setup while having standard reference
- **Implementation:** Provide relative comparisons that users can calibrate to their controls

**Q3.3:** Which samples should be excluded from analysis?
- Wash samples?
- Calibration beads only?
- Failed QC samples?
- **Current Status:** Including all samples with valid data

**❓ NOT ANSWERED - Needs clarification on specific exclusion criteria**

**Q3.4:** How should fold-change calculations be performed?
- Ratio to single baseline sample?
- Ratio to mean of baseline group?
- Log2 fold change or linear?
- **Current Implementation:** Ratio to mean baseline per metric

**✅ ANSWER (Implied from Q3.2):**
- Use ratio to mean of baseline group (global average)
- Linear or log scale TBD based on best practices document

---

## 🧪 **4. Experimental Metadata & Context**

**Q4.1:** What experimental variables should be tracked?
- **Currently Extracted:**
  - Passage number (from filename when available)
  - Treatment condition (CD81, CD9, ISO)
  - Preparation method (SEC, Centrifugation)
  - Measurement date
- **Missing/Unclear:**
  - Cell line/source information?
  - Culture conditions?
  - Isolation protocol batch?
  - Storage time before measurement?

**✅ PARTIAL ANSWER (Parvesh - Nov 18, 2025):**
- **Approach:** USER INPUT during upload, not filename parsing
- **Reason:** Different users/universities will have different naming conventions
- **Solution:** Popup when file uploaded asking for sample details
- **Backend Processing:** System will rename/standardize files internally for model processing
- **User Side:** Users can keep their original names for reports/exports
- **Benefit:** Model won't get confused by inconsistent naming
- **Action Item:** Need to design metadata input form in UI

**Q4.2:** Are there different EV isolation protocols being compared?
- SEC (Size Exclusion Chromatography)
- Ultracentrifugation
- Filtration (0.2 µm, 0.22 µm)
- Commercial kits?
- Should these be analyzed separately or compared?

**✅ CONFIRMED (From transcript and previous data):**
- **SEC:** Size Exclusion Chromatography - ✅ Used
- **Centri:** Centrifugation method - ✅ Used
- **Filtration:** 0.2µm filters mentioned in data - ✅ Used
- **Action Item:** Confirm if these should be analyzed separately or as comparison groups

**Q4.3:** What is the experimental timeline and batching?
- Were all samples processed together?
- Batch effects to consider?
- Historical vs. recent data quality differences?

**✅ ANSWER (Parvesh - Nov 18, 2025):**
- **Current Data:** All exploratory/historical - for understanding system only
- **Not for ML training:** Data quality and completeness varies
- **Future Approach:** Clean experimental data will be provided after UI demonstration
- **Timeline:** 2-3 sample experiments with cross-instrument tracking
- **Action Item:** Wait for new controlled experimental data

**Q4.4:** What biological context is important for ML features?
- iPSC differentiation stage?
- Cell passage number effects?
- Medium composition (FBS vs. serum-free)?
- Time of EV collection (24h, 48h conditioned media)?

**❓ NOT ANSWERED - Should be included in metadata input form (see Q4.1)**

---

## 📈 **5. Data Quality & Validation Standards**

**Q5.1:** What are the gold standard QC metrics for the lab?
- Published protocols being followed?
- MISEV guidelines (Minimal Information for Studies of EVs)?
- Internal lab SOPs?
- Can I get copies of these documents?

**Q5.2:** How should outliers be handled?
- Statistical thresholds (Z-score > 3)?
- Manual review process?
- Biological vs. technical outliers?
- **Current Status:** Flagging but not removing outliers

**Q5.3:** What is acceptable coefficient of variation (CV) for:
- Technical replicates? (Typically <15-20%?)
- Biological replicates? (Typically <30%?)
- Between-instrument measurements?

**Q5.4:** Are there known technical issues or artifacts to filter?
- Aggregation artifacts in NTA?
- Bubble interference?
- Instrument-specific noise patterns?
- Dead volume effects?

---

## 🤖 **6. Machine Learning Objectives & Ground Truth**

**Q6.1:** What is the primary ML classification/prediction target?
- **Potential Options:**
  - EV purity (high vs. low quality)
  - Marker expression level (CD81+, CD9+)
  - Isolation method effectiveness
  - Cell source/passage prediction
  - Biological function prediction
- Which one(s) are priority?

**✅ ANSWER (From Process Flow - Parvesh Nov 18, 2025):**
- **PRIMARY GOAL:** Predict if marker protein exists at expected size
- **Example Use Case:** "Will CD9 be found at 80nm scattering blue light?"
- **Current Manual Process:** Run NanoFACS → if no marker at expected size → discard → try new sample
- **ML Benefit:** Predict viability before expensive TEM/Western Blot steps
- **Decision Support:** Should sample proceed to next analysis step?
- **Quality Gate:** Automated QC before manual validation

**Q6.2:** Do we have ground truth labels for training?
- Western blot confirmation of markers?
- Electron microscopy validation?
- Functional assays?
- Expert annotations?

**✅ ANSWER (From Process Flow):**
- **Ground Truth Available:** Western Blot results (atomic mass → protein confirmation)
- **Validation Data:** TEM images showing membrane viability
- **Current Status:** Team uses intuition and experience for interpretation
- **Future Approach:** Historical decisions can be used as labels
- **Action Item:** Need to collect outcome labels (proceed/discard) for past samples

**Q6.3:** What would constitute a "successful" ML model?
- Prediction accuracy threshold?
- Specific use case (QC automation, method optimization, phenotype prediction)?
- Real-time vs. batch analysis requirements?

**✅ PARTIAL ANSWER (Implied from process):**
- **Primary Use Case:** Early QC automation (predict before TEM/Western Blot)
- **Success Metric:** Reduce wasted samples going to expensive validation steps
- **Timeline:** Predictions needed after NanoFACS, before TEM
- **Action Item:** Define specific accuracy requirements with team

**Q6.4:** Which features are most biologically meaningful?
- Specific size ranges (30-200 nm)?
- Marker ratios (CD81/CD9)?
- Concentration metrics?
- Should we prioritize interpretability over accuracy?

**✅ PARTIAL ANSWER (From Process Explanation):**
- **Critical Features:**
  - Particle size at specific ranges (e.g., 80nm for CD9)
  - Light scattering wavelength/intensity (B531 for blue, etc.)
  - Size-to-intensity correlation (clustering patterns)
- **Expected Relationships:** Known protein → expected size → expected wavelength
- **Interpretability:** HIGH priority (scientists need to understand why prediction made)
- **Action Item:** Create feature importance analysis aligned with biological expectations

---

## 🔄 **7. Current Data Processing Pipeline Validation**

**Q7.1:** Can we review the current data processing outputs together?
- **Generated Files to Review:**
  - `data/processed/combined_features.parquet` (88 samples, 46 features)
  - `data/processed/baseline_comparison.parquet` (fold changes)
  - Statistics summaries for FCS (67 samples) and NTA (108 measurements)
- Do the extracted features make biological sense?

**✅ ANSWER (Meeting Discussion):**
- **Current Status:** Sumit has converted data to Parquet format
- **Visualization Created:** Histogram graphs showing intensity distributions (B531-A, etc.)
- **Validation Needed:** Parvesh will review graphs and feature extraction
- **Action Item:** Connect Sumit with Mohith to integrate Parquet conversion into UI
- **Next Step:** Ensure calculated values are correct before proceeding

**Q7.2:** Are there missing measurements we should track?
- **Currently Extracted from FCS:**
  - Event counts, channel statistics, compression ratio
- **Currently Extracted from NTA:**
  - D-values (D10/D50/D90), concentration, size bins, PDI
- What else is important?

**✅ ANSWER (Parvesh - Nov 18, 2025):**
- **Critical Plot Type:** Height vs Area (not just Area vs Area)
- **Current Issue:** Area-only plots don't make much biological sense
- **Recommended Visualization:** Particle SIZE vs COLOR intensity
- **Example:** "Size of particle vs B531 (blue light scattering)"
- **Purpose:** Show which particle sizes scatter which wavelengths/intensities
- **Clustering:** Look for clustered groups at specific size+intensity combinations
- **Action Item:** Update plotting functions to use size (from Mie scatter calculation) vs intensity

**Q7.3:** How should multi-timepoint or time-series data be handled?
- Are there samples measured at multiple timepoints?
- Kinetic analysis requirements?

**❓ NOT ANSWERED - Needs clarification**

**Q7.4:** Visualization preferences for team review?
- Which plots are most informative for QC?
- Standard reporting format needed?
- Interactive dashboards vs. static reports?

**✅ PARTIAL ANSWER (Parvesh - Nov 18, 2025):**
- **Preferred Plot:** Size vs Intensity scatter plots (with clustering)
- **Current UI:** Streamlit dashboard by Mohith
- **Status:** UI almost complete, needs Parquet integration
- **Action Item:** Sumit to work with Mohith on connecting backend to UI

---

## 📋 **8. Immediate Action Items & Decisions Needed**

**Q8.1:** Can we establish a standardized sample naming convention going forward?
- Proposed format: `[Source]_[Passage]_[Treatment]_[Method]_[Date]_[Rep]`
- Example: `IPSC_P2_CD81_SEC_20251118_rep1`

**✅ DECISION MADE (Parvesh - Nov 18, 2025):**
- **Approach:** Do NOT rely on user filenames for metadata
- **Reason:** Different users/labs will use different conventions
- **Solution:** Metadata input popup when file uploaded
- **Backend:** System renames files internally using standardized format
- **User Experience:** Users keep original names for their records/reports
- **Model Protection:** Prevents confusion from inconsistent naming
- **Implementation:** Sumit's suggested annotation approach approved

**Q8.2:** Should we create a sample metadata spreadsheet template?
- Columns: Sample_ID, Biological_ID, FCS_File, NTA_Folder, Treatment, Date, Notes
- Owner/maintainer?

**✅ DECISION MADE (Implied from Q8.1):**
- **Approach:** Metadata captured via UI popup, not spreadsheet
- **Storage:** Backend database/structured format
- **Export:** Users can export reports with their preferred formats
- **Action Item:** Design metadata input form in Streamlit UI

**Q8.3:** What is the timeline for:
- Finalizing normalization standards?
- Collecting additional metadata?
- Completing retrospective sample mapping?
- Running first ML experiments?

**✅ TIMELINE (From Meeting - Nov 18, 2025):**
- **UI Completion:** Nearly done (Mohith working on final features)
- **UI Demonstration:** Tomorrow's meeting with client
- **New Experimental Data:** After UI demo, client will run 2-3 proper experiments
- **Normalization Standards:** Waiting for Surya's best practices document (in progress)
- **Parquet Integration:** Immediate - Sumit to connect with Mohith
- **ML Experiments:** After receiving clean cross-instrument data
- **Current Data Usage:** Exploration and testing only, not for ML training

**Q8.4:** Who are the domain experts to consult for:
- FCS analysis protocols? (flow cytometry specialist)
- NTA interpretation? (nanoparticle tracking expert)
- EV biology validation? (PI or senior researcher)

**✅ IDENTIFIED:**
- **FCS/NanoFACS Expertise:** Parvesh (explained complete process)
- **Best Practices:** Surya (working on normalization document)
- **Client Contact:** Chari (metadata details pending)
- **Development Team:** Sumit (backend), Mohith (UI), Abhishek (oversight)
- **Action Item:** Await Chari's details and Surya's best practices

---

## 🔍 **9. Data Assumptions Made (Please Validate)**

### **Current Code Assumptions - Are These Correct?**

**Assumption 9.1:** FCS channels containing "FSC" are forward scatter, "SSC" are side scatter
- ✅ **VALIDATED** (Parvesh - Nov 18, 2025)

**Assumption 9.2:** NTA measurements with camera_level 14-16 are acceptable quality
- ❓ **NOT VALIDATED** - Needs confirmation

**Assumption 9.3:** Samples without "_rep" suffix are unique biological samples
- ❓ **NOT VALIDATED** - Needs confirmation

**Assumption 9.4:** All FCS files in same folder belong to same experiment batch
- ⚠️ **PARTIALLY ADDRESSED**
- Current data is exploratory, not organized by batch
- Future data will be properly structured
- Action Item: Confirm batch organization strategy

**Assumption 9.5:** NTA dilution factors stored in text files are accurate and applied correctly
- ❓ **NOT VALIDATED** - Needs confirmation

**Assumption 9.6:** Size bins should be: 0-50nm, 50-100nm, 100-150nm, 150-200nm, 200-300nm, 300+nm
- ⚠️ **NEEDS REVIEW**
- Specific sizes matter (e.g., CD9 expected at 80nm)
- May need more granular bins around biologically relevant sizes
- Action Item: Confirm appropriate bin ranges

**Assumption 9.7:** Passage number can be extracted from filenames containing "P1", "P2", etc.
- ⚠️ **APPROACH CHANGED**
- Do NOT extract from filenames
- Collect via metadata input popup instead
- Action Item: Include in metadata form

**Assumption 9.8:** Lower polydispersity index (PDI < 0.3) indicates higher sample homogeneity
- ❓ **NOT VALIDATED** - Needs confirmation

**Assumption 9.9:** Fluorescence intensity in FCS should be log-transformed for visualization
- ✅ **STANDARD PRACTICE** (but waiting for Surya's best practices document)

**Assumption 9.10:** Baseline samples are appropriate for ALL comparisons (global baseline approach)
- ✅ **VALIDATED** (Parvesh - Nov 18, 2025)
- Use global averaged baseline
- Allow users to adjust for their specific setup
- Provide relative comparisons

---

## 📝 **10. Documentation & Knowledge Transfer**

**Q10.1:** Are there existing analysis pipelines or scripts I should review?
- Previous Python/R scripts?
- Excel templates with formulas?
- Published papers from the lab?

**✅ ANSWER (Meeting Context):**
- **Current Process:** Manual/intuition-based (no automated scripts)
- **UI Development:** Mohith's Streamlit dashboard (particle size analysis tab)
- **Backend Development:** Sumit's Parquet conversion and batch processing
- **Mie Scatter Implementation:** Python code for size calculation in UI
- **Action Item:** Review Mohith's UI code and Sumit's backend scripts

**Q10.2:** What software tools does the team currently use?
- FCS analysis: FlowJo? FCS Express? Custom scripts?
- NTA analysis: NTA software version? Post-processing tools?
- Statistics: Prism? SPSS? Python/R?

**✅ PARTIAL ANSWER (From Transcript):**
- **NanoFACS Analysis:** Manual interpretation of scatter plots
- **NTA Analysis:** Raw instrument output (CSV/text files)
- **New System:** Streamlit UI by Mohith (Python-based)
- **Backend:** Python scripts (Sumit's Parquet processing)
- **Visualization:** Matplotlib for graphs
- **Action Item:** Confirm current analysis software used by scientists

**Q10.3:** Can I get access to:
- Lab protocols (SOPs for EV isolation and characterization)?
- Instrument manuals and specifications?
- Previous reports or presentations?
- Existing data dictionaries or metadata schemas?

**✅ ACTION ITEMS IDENTIFIED:**
- **Waiting for Chari:** Detailed metadata specifications
- **Waiting for Surya:** Best practices and normalization standards document
- **Process Documentation:** Parvesh will write down complete process flow
- **Meeting Recording:** Transcript available (this document updated from it)
- **Tomorrow's Meeting:** UI demonstration to client

**Q10.4:** Who should review and approve:
- Data processing pipeline changes?
- Normalization method implementations?
- ML model design and validation?
- Final analysis reports?

**✅ TEAM STRUCTURE IDENTIFIED:**
- **Technical Lead:** Parvesh Reddy (approves approach, explains biology)
- **Best Practices:** Surya (normalization standards)
- **Client Liaison:** Chari (metadata requirements)
- **Backend Developer:** Sumit Malhotra (data processing, ML pipeline)
- **UI Developer:** Mohith M (Streamlit interface, Mie scatter)
- **Project Oversight:** Abhishek Reddy (suggested posting questions in group)
- **Approval Process:** Questions posted in group chat for discussion

---

## ✅ **Meeting Preparation Checklist**

**Before the meeting, please prepare:**
- [x] ~~Sample naming convention documentation (if exists)~~ → **DECISION:** Use metadata popup, not filenames
- [x] ~~List of control/baseline samples for each experiment~~ → **ANSWER:** Global baseline approach confirmed
- [ ] **PENDING:** Standard dilution factors used for NTA (from Chari)
- [ ] **PENDING:** QC acceptance criteria documents (from Surya - best practices)
- [ ] **PENDING:** Any existing sample metadata spreadsheets (from Chari)
- [ ] **PENDING:** Lab SOPs for EV characterization (from Surya)
- [x] ~~Timeline and priorities for ML development~~ → **ANSWER:** After UI demo, new experimental data

**After the meeting, I will:**
- [x] ~~Update all code to reflect correct normalization procedures~~ → **WAITING:** Surya's best practices document
- [x] ~~Implement proper sample ID mapping system~~ → **SOLUTION:** Metadata popup in UI
- [ ] **IN PROGRESS:** Revise QC thresholds based on lab standards (pending Surya's doc)
- [x] ~~Create standardized metadata collection template~~ → **SOLUTION:** UI popup form (Mohith + Sumit)
- [x] **COMPLETED:** Document all decisions in project README → This file updated
- [ ] **PENDING:** Reprocess data with validated parameters (after receiving standards)

**NEW ACTION ITEMS FROM MEETING:**
- [x] **COMPLETED:** Update MEETING_QUESTIONS.md with answers from transcript
- [ ] **IMMEDIATE:** Sumit to connect with Mohith for Parquet integration into UI
- [ ] **IMMEDIATE:** Update plotting to show Size vs Intensity (not Area vs Area)
- [ ] **IMMEDIATE:** Implement metadata input popup in Streamlit UI
- [ ] **PENDING:** Parvesh to write down complete process flow document
- [ ] **PENDING:** Post remaining unanswered questions in team group chat
- [ ] **TOMORROW:** UI demonstration to client
- [ ] **AFTER DEMO:** Client to provide 2-3 properly structured cross-instrument experiments
- [ ] **WAITING:** Surya's normalization best practices document
- [ ] **WAITING:** Chari's detailed metadata requirements
- [ ] **FUTURE:** Create GitHub enterprise repo for collaborative development

---

## 📧 **Follow-up Items to Send After Meeting**

**QUESTIONS REMAINING FOR TEAM (to post in group chat):**

### **High Priority - Needed for Development:**
1. **NTA Quality Criteria:** Camera level range validation (is 14-16 correct?)
2. **Replicate Identification:** How to identify technical vs biological replicates?
3. **Dilution Standards:** What are standard NTA dilution factors to use?
4. **Size Bins:** Confirm appropriate size ranges (especially around 80nm for CD9)
5. **Sample Exclusion:** Which samples should be filtered out (wash, failed QC)?
6. **P1/P2 Meaning:** Confirm if this means Passage number
7. **PDI Interpretation:** Is PDI < 0.3 the correct threshold for homogeneity?

### **Medium Priority - For Future ML Development:**
8. **Ground Truth Labels:** Can we get outcome data (proceed/discard decisions) for historical samples?
9. **Accuracy Requirements:** What prediction accuracy is needed for ML model acceptance?
10. **Multi-timepoint Data:** Are there time-series experiments to handle?
11. **Batch Organization:** How will future data be organized (per experiment, per date, etc.)?

### **Documents to Request:**
- [x] **WAITING:** Surya's normalization best practices document (in progress)
- [x] **WAITING:** Chari's metadata specifications
- [ ] **REQUEST:** Lab SOPs for EV isolation and characterization
- [ ] **REQUEST:** Instrument manuals (NanoFACS, NTA specifications)
- [ ] **REQUEST:** Examples of "good" vs "bad" quality samples
- [ ] **REQUEST:** Any relevant publications from the lab

### **Process Documentation Needed:**
- [x] **PENDING:** Parvesh to document complete analysis workflow (NTA → NanoFACS → TEM → Western Blot)
- [ ] **REQUEST:** Decision tree for when to skip NTA step
- [ ] **REQUEST:** Standard gating/thresholding procedures for NanoFACS
- [ ] **REQUEST:** TEM image interpretation criteria
- [ ] **REQUEST:** Western Blot validation thresholds

---

**ANSWERED IN MEETING - No Further Action:**
- ✅ Sample linking strategy (wait for new cross-instrument data)
- ✅ Baseline comparison approach (global averaged baseline)
- ✅ Sample naming convention (metadata popup, not filename parsing)
- ✅ Process flow understanding (NTA → NanoFACS → TEM → Western Blot)
- ✅ ML objective (predict marker presence at expected size)
- ✅ Ground truth availability (Western Blot confirmation exists)
- ✅ Visualization preferences (Size vs Intensity scatter plots)
- ✅ Team structure and approval process
- ✅ Project timeline (UI demo → new experiments → ML development)

---

**TECHNICAL IMPROVEMENTS TO IMPLEMENT:**
1. **Parquet Integration:** Connect Sumit's conversion pipeline to Mohith's UI
2. **Plotting Update:** Change from Area-Area to Size-Intensity plots
3. **Metadata Form:** Design and implement popup for sample details
4. **Backend Standardization:** Automatic file renaming for model consistency
5. **Feature Extraction:** Focus on size-wavelength correlations
6. **Baseline Calculation:** Implement global averaging with user adjustment
7. **GitHub Setup:** Create enterprise repo for team collaboration (when approved)

---

## 🎯 **SUMMARY: CRITICAL TAKEAWAYS FROM MEETING**

### **What We Learned:**

1. **Current Data is for EXPLORATION ONLY**
   - Not for ML training
   - No cross-instrument sample matching exists yet
   - Quality and completeness varies
   - **Wait for clean experimental data after UI demo**

2. **Complete Analysis Workflow:**
   - **Step 1:** NTA (optional) - size distribution
   - **Step 2:** NanoFACS - marker + size correlation
   - **Step 3:** TEM - viability check
   - **Step 4:** Western Blot - protein confirmation
   - **Decision Point:** After NanoFACS (discard if marker not at expected size)

3. **Sample Naming Strategy:**
   - **DO NOT** parse filenames for metadata
   - **USE** metadata input popup when uploading
   - **Backend** standardizes names internally
   - **Users** keep original names for reports

4. **Baseline Approach:**
   - Global averaged baseline across all experiments
   - Users can adjust for their specific setup
   - Prevents issues with different control samples

5. **Visualization Priority:**
   - **NOT:** Area vs Area plots (not biologically meaningful)
   - **YES:** Size vs Intensity scatter plots
   - Shows which particle sizes scatter which wavelengths
   - Look for clustering patterns

6. **ML Goal:**
   - Predict if marker exists at expected size
   - Early QC to avoid wasting expensive TEM/Western Blot
   - High interpretability required
   - Ground truth: Western Blot confirmations

### **Immediate Next Steps:**

**1. DEVELOPMENT TASKS:**
- [ ] Sumit + Mohith: Integrate Parquet processing into UI
- [ ] Update plotting: Size vs Intensity (not Area vs Area)
- [ ] Design metadata input form for UI
- [ ] Implement backend file standardization

**2. WAITING FOR:**
- [ ] Surya: Normalization best practices document
- [ ] Chari: Detailed metadata requirements
- [ ] Parvesh: Written process flow document
- [ ] Client: New cross-instrument experimental data (after UI demo)

**3. CLARIFICATION NEEDED:**
- [ ] Post remaining questions in team group chat
- [ ] Get QC thresholds and acceptance criteria
- [ ] Confirm NTA quality parameters
- [ ] Validate size bin ranges

**4. TOMORROW:**
- [ ] UI demonstration to client
- [ ] Present current capabilities
- [ ] Plan for new structured experiments

---

**Thank you for taking time to clarify these points!** Getting these fundamentals right now will ensure the ML pipeline produces scientifically valid and reproducible results.

**Document Updated:** November 18, 2025 (Post-Meeting)  
**Prepared by:** Sumit Malhotra (AI Assistant)  
**Meeting Attendees:** Parvesh Reddy, Mohith M, Sumit Malhotra, Abhishek Reddy  
**Version:** 2.0 (Updated with meeting answers)
