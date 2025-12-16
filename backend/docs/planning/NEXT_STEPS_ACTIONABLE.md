# CRMIT Project - Next Steps (November 18, 2025)

**Meeting Date:** November 18, 2025  
**Updated:** Post-meeting analysis complete  
**Status:** Phase 2 Complete (75% → 75%), Overall Progress: 40% → 50%

---

## 🎯 **IMMEDIATE ACTIONS (This Week)**

### **Priority 1: UI Integration (Sumit + Mohith)**

**Task:** Integrate Parquet backend with Streamlit UI

**Action Items:**
1. **Connect Parquet Files to UI:**
   ```python
   # Sumit to share with Mohith:
   - Location: data/parquet/nanofacs/events/*.parquet
   - Format: 67 files, ~727 MB total
   - Schema: All FCS channels + sample metadata
   ```

2. **Update UI Data Loading:**
   - Replace CSV reading with Parquet
   - Use: `pd.read_parquet(file_path)`
   - Benefits: 80% smaller files, 10x faster loading

3. **Test Integration:**
   - Load 1 sample file in UI
   - Verify all channels display correctly
   - Test histogram/scatter plot generation
   - Verify Mie scatter particle size calculation works

**Timeline:** Complete by Nov 20, 2025 (2 days)

---

### **Priority 2: Plot Type Update (Critical!)**

**Issue:** Current plots show Area vs Area (not biologically meaningful)  
**Required:** Change to Size vs Intensity

**From Meeting (Parvesh):**
- "Area vs Area doesn't make much biological sense"
- "What they're looking at is ideally height versus an area"
- "Size of particle versus color of scattering"
- "Show which particle sizes scatter which wavelengths"

**Action Items:**
1. **Update Plotting Functions:**
   ```python
   # BEFORE (Area vs Area):
   plot_scatter(data, x='B531-A', y='VFSC-A')  # ❌ Not meaningful
   
   # AFTER (Size vs Intensity):
   plot_scatter(data, x='particle_size_nm', y='B531-H')  # ✅ Meaningful
   ```

2. **Use Mie Scatter Size Calculation:**
   - Mohith has this implemented in UI already
   - Need to ensure output is available for plotting
   - Size should be from FSC/SSC → diameter (nm)

3. **Update All Scatter Plots:**
   - Change X-axis: Area → Particle Size (nm)
   - Keep Y-axis: Intensity (Height values)
   - Look for clustering at specific size + intensity combinations

**Files to Update:**
- `src/visualization/fcs_plots.py` - scatter plot functions
- `scripts/batch_visualize_fcs.py` - batch plotting
- Any demo scripts using Area vs Area

**Timeline:** Complete by Nov 21, 2025 (3 days)

---

### **Priority 3: Metadata Input Popup Design**

**Decision (from meeting):** Use metadata popup, NOT filename parsing

**Why:**
- Different users/labs have different naming conventions
- Realistic expectation: users won't follow our naming rules
- Solution: Ask for metadata when file uploaded

**Design Requirements:**

**Popup Form Fields:**
```
Upload File:
└─ [Choose File: sample.fcs]

Sample Information:
├─ Biological Sample ID*: ___________
├─ Passage Number: ___________
├─ Treatment/Antibody*: [Dropdown: CD81 / CD9 / ISO / Other]
├─ Concentration (µg): ___________
├─ Preparation Method: [Dropdown: SEC / Centrifugation / Filtration]
├─ Date: [Date Picker]
└─ Notes: ___________________________

* Required fields
[Cancel] [Upload & Process]
```

**Backend Processing:**
```python
# User uploads: "random_filename_123.fcs"
# Popup captures: 
# - bio_sample_id: "P5_F10"
# - treatment: "CD81"
# - concentration: "0.25"
# - method: "SEC"
# - date: "2025-11-18"

# System internally renames:
internal_name = f"{bio_sample_id}_{treatment}_{concentration}ug_{method}_{date}.parquet"
# Result: "P5_F10_CD81_0.25ug_SEC_20251118.parquet"

# User downloads report:
# - Can use original filename OR
# - Can export with standardized name
```

**Action Items:**
1. Design popup UI in Streamlit (Mohith)
2. Capture metadata fields
3. Implement backend standardization (Sumit)
4. Store metadata in Parquet schema
5. Test full workflow

**Timeline:** Complete by Nov 22, 2025 (4 days)

---

## 📋 **FOLLOW-UP QUESTIONS (Post to Group Chat)**

**Send these questions to team group for clarification:**

### **High Priority (Need for Development):**

1. **NTA Quality Criteria:**
   - Is camera level 14-16 the correct acceptance range?
   - What are minimum particles per frame?
   - Temperature tolerance: ±2°C acceptable?

2. **Replicate Identification:**
   - How should technical replicates be marked? (_rep1, _rep2?)
   - How to identify biological replicates?
   - What CV% is acceptable between replicates?

3. **Dilution Standards:**
   - What are standard NTA dilution factors?
   - Should we normalize back to stock concentration?
   - Linear back-calculation acceptable?

4. **Size Bins:**
   - Current: 0-50nm, 50-100nm, 100-150nm, 150-200nm
   - Parvesh mentioned: CD9 at ~80nm
   - Should we use finer bins around 80nm? (e.g., 70-90nm bin)

5. **Sample Exclusion Criteria:**
   - Should wash samples be excluded from analysis?
   - Failed QC samples: automatic exclusion or flag for review?
   - Empty/very low event count: minimum threshold?

6. **P1/P2 Meaning:**
   - Confirm: P1 = Passage 1, P2 = Passage 2?
   - Or different meaning?

7. **PDI Threshold:**
   - Is PDI < 0.3 correct for homogeneity?
   - What PDI indicates poor sample quality?

### **Medium Priority (For ML Development):**

8. **Ground Truth Labels:**
   - Can we get historical proceed/discard decisions?
   - Western Blot results to use as labels?
   - TEM viability assessments?

9. **ML Accuracy Requirements:**
   - What prediction accuracy needed for acceptance?
   - Cost of false positive vs false negative?
   - Should model err on side of caution?

10. **Batch Organization:**
    - Future data: organized by experiment date?
    - Or by passage/biological sample?

---

## 📄 **DOCUMENTS TO REQUEST**

**Send formal requests for:**

1. **From Surya:**
   - ✅ Normalization best practices (IN PROGRESS - he's working on it)
   - Lab SOPs for EV isolation
   - FCS analysis protocols
   - Instrument specifications

2. **From Chari:**
   - Metadata field requirements
   - Standard operating procedures
   - Quality control criteria documents

3. **From Parvesh:**
   - ✅ Written process flow (AGREED - will document)
   - Decision tree for when to skip NTA
   - Standard gating procedures for NanoFACS
   - Examples of "good" vs "bad" samples

---

## 🗓️ **TIMELINE & MILESTONES**

### **This Week (Nov 18-22, 2025):**
- ✅ Nov 18: Meeting questions documented
- 🔄 Nov 19: **UI DEMO TO CLIENT** (Tomorrow!)
- 🔄 Nov 20: Parquet integration complete
- 🔄 Nov 21: Plot type updates complete
- 🔄 Nov 22: Metadata popup design complete

### **Next Week (Nov 25-29, 2025):**
- Get responses to posted questions
- Receive Surya's best practices document
- Receive Chari's metadata requirements
- Client runs 2-3 properly structured experiments
- Begin Task 1.3 enhancements based on feedback

### **Week After (Dec 2-6, 2025):**
- Process new cross-instrument experimental data
- Validate sample linking strategy
- Implement normalization standards (from Surya)
- Test ML-ready dataset creation
- Baseline comparison implementation

---

## 🎯 **SUCCESS CRITERIA**

**For This Week:**
- ✅ UI demonstration successful
- ✅ Parquet files loading in UI correctly
- ✅ Plots show Size vs Intensity (not Area vs Area)
- ✅ Metadata popup designed and functional
- ✅ Questions posted to team group
- ✅ All action items assigned and tracked

**For Next Two Weeks:**
- ✅ New experimental data received
- ✅ Sample linking validated
- ✅ Normalization standards implemented
- ✅ ML-ready dataset created
- ✅ Baseline comparison working

---

## 📞 **COMMUNICATION PLAN**

### **Daily Updates:**
- Sumit ↔ Mohith: Direct communication on integration
- Update team group: Progress on action items
- Flag blockers immediately

### **Weekly Check-ins:**
- Friday EOD: Progress summary
- What completed this week?
- Any blockers?
- On track for milestones?

### **Escalation:**
- >1 day stuck on issue → Ask for help in group
- Technical blocker → Tag Parvesh
- Requirements clarification → Tag Chari/Surya
- Urgent issues → Abhishek

---

## 🚀 **KEY REMINDERS**

1. **Tomorrow = UI Demo Day** 🎉
   - Make sure Streamlit is running
   - Test all features before demo
   - Prepare to show particle size analysis
   - Have sample files ready

2. **Current Data = Exploratory Only**
   - Don't spend too much time on perfect analysis
   - Wait for clean experimental data
   - Focus on infrastructure and UI

3. **Metadata Popup = Critical**
   - This solves sample naming chaos
   - Essential for proper data tracking
   - Allows model standardization

4. **Plot Type Update = High Priority**
   - Parvesh specifically called this out
   - Area vs Area not useful scientifically
   - Size vs Intensity shows clustering

5. **Team Communication = Essential**
   - Post questions to group promptly
   - Don't wait for perfect wording
   - Better to ask early than guess wrong

---

## 📝 **WHO DOES WHAT**

| Person | Tasks | Timeline |
|--------|-------|----------|
| **Sumit** | - Share Parquet files with Mohith<br>- Help integrate into UI<br>- Update plot functions (Size vs Intensity)<br>- Design backend metadata standardization<br>- Post questions to group | Nov 18-22 |
| **Mohith** | - Integrate Parquet loading in UI<br>- Test with sample files<br>- Design metadata popup form<br>- Prepare for UI demo tomorrow<br>- Add Select scatter type (SSC1/SSC2) | Nov 18-22 |
| **Parvesh** | - Review tomorrow's UI demo<br>- Provide process flow document<br>- Answer technical questions<br>- Remind Surya about best practices doc | Nov 19+ |
| **Surya** | - Complete best practices document<br>- Provide normalization standards<br>- Answer FCS-specific questions | This week |
| **Chari** | - Provide metadata requirements<br>- Answer NTA-specific questions<br>- Plan 2-3 new experiments | Next week |
| **Abhishek** | - Review progress<br>- Post questions in group<br>- Coordinate team responses | Ongoing |

---

## ✅ **COMPLETION CHECKLIST**

**This Week (Nov 18-22):**
- [ ] Parquet integration in UI working
- [ ] Size vs Intensity plots implemented
- [ ] Metadata popup designed
- [ ] Questions posted to group chat
- [ ] UI demo completed successfully
- [ ] New experiment plan confirmed

**Next Two Weeks (Nov 25 - Dec 6):**
- [ ] Surya's document received
- [ ] Chari's requirements received
- [ ] Parvesh's process flow received
- [ ] New experimental data received
- [ ] Normalization implemented
- [ ] Sample linking validated
- [ ] ML-ready dataset created

---

**Last Updated:** November 18, 2025 (Post-Meeting)  
**Next Update:** November 22, 2025 (End of Week)  
**Status:** ✅ Action plan complete, ready to execute

