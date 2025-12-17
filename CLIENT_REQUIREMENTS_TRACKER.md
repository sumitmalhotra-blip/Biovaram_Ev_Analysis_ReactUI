# 📋 BioVaram EV Analysis - Client Requirements Tracker
## Based on Meeting Notes Analysis (Nov 19 - Dec 11, 2025)

**Created:** December 17, 2025  
**Last Updated:** December 17, 2025  
**Source:** Biovaram ALL meeting notes.md

---

## 📊 QUICK STATUS OVERVIEW

| Priority | Total | Completed | Blocked | Pending |
|----------|-------|-----------|---------|---------|
| P0 - Critical | 5 | 5 | 0 | 0 |
| P1 - High | 8 | 4 | 4 | 0 |
| P2 - Medium | 6 | 4 | 2 | 0 |
| P3 - Low | 3 | 0 | 3 | 0 |
| **Total** | **22** | **13** | **9** | **0** |

### P2 Tasks Status:
- ⚠️ TASK-014: AI Research Chat - BLOCKED (needs AWS Bedrock)
- ⚠️ TASK-015: Anomaly ML Model - BLOCKED (needs labeled data)
- ✅ TASK-016: Best Practices Engine - COMPLETED
- ✅ TASK-017: Cross-Compare Sidebar - ALREADY IMPLEMENTED
- ✅ TASK-018: Chart Color Consistency - COMPLETED
- ✅ TASK-019: Histogram Bin Config - COMPLETED

### P3 Tasks Status (All Infrastructure/Deployment):
- 🔴 TASK-020: Desktop EXE - BLOCKED (needs complete app + build pipeline)
- 🔴 TASK-021: S3 Storage - BLOCKED (needs AWS credentials)
- 🔴 TASK-022: Multi-Tenant - BLOCKED (needs auth + infrastructure)

---

## 🔴 P0 - CRITICAL PRIORITY (Complete This Week)

---

### TASK-001: Fix Mean → Median Display Issue
**Status:** ✅ COMPLETED  
**Priority:** P0 - Critical  
**Requested By:** Surya (Dec 3, 2025 Meeting)  
**Completed:** December 17, 2025  
**Actual Effort:** 1.5 hours

#### Client Quote:
> *"Mean is basically not the real metric... median is something that really existed in the data set... for display median itself will be sufficient"* - Surya

#### What Was Done:
- ✅ Removed Mean from FCS statistics cards (`statistics-cards.tsx`)
- ✅ Removed Mean from NTA statistics cards (`nta/statistics-cards.tsx`)
- ✅ Removed Mean from NTA Quick Summary (`nta-analysis-results.tsx`)
- ✅ Updated cross-compare discrepancy to weight D50 (Median) higher
- ✅ Updated discrepancy chart to show Std Dev instead of Mean
- ✅ Updated correlation scatter chart to remove Mean from labels
- ✅ Added Size Std Dev card to FCS statistics
- ✅ Added comments documenting client request in code
- ✅ Backend still calculates Mean for ML modeling purposes

#### Files Modified:
```
components/flow-cytometry/statistics-cards.tsx
components/nta/statistics-cards.tsx  
components/nta/nta-analysis-results.tsx
components/cross-compare/cross-compare-tab.tsx
components/cross-compare/charts/discrepancy-chart.tsx
components/cross-compare/charts/correlation-scatter-chart.tsx
components/cross-compare/method-comparison-summary.tsx
```

#### Acceptance Criteria (All Met):
- [x] No "Mean" visible anywhere in the frontend UI
- [x] Median (D50) is clearly displayed
- [x] Standard Deviation is clearly displayed
- [x] Backend still calculates Mean for modeling purposes
- [x] All charts and statistics cards updated

---

### TASK-002: Fix Size Range Edge Clustering (30-220nm Range)
**Status:** ✅ COMPLETED  
**Priority:** P0 - Critical  
**Requested By:** Parvesh (Dec 5, 2025 Meeting)  
**Completed:** December 17, 2025  
**Actual Effort:** 2 hours

#### Client Quote:
> *"Most of them are in 40 and most of them are in 180. This is actually because everything beyond the range is getting set to 40 and 180... we need to have that not do that"* - Parvesh

#### What Was Done:
- ✅ Created `backend/src/physics/size_config.py` with SizeRangeConfig class
- ✅ Defined search range (30-220nm), valid range (30-220nm), display range (40-200nm)
- ✅ Implemented `filter_particles_by_size()` function to EXCLUDE (not clamp) outliers
- ✅ Updated `mie_scatter.py` to use extended search range from config
- ✅ Updated `upload.py` to use proper filtering instead of clamping
- ✅ Added size filtering statistics to FCS results (`size_filtering`, `excluded_particles_pct`)
- ✅ Updated `api-client.ts` with new TypeScript types for filtering stats
- ✅ Updated `statistics-cards.tsx` to show valid particle count in description
- ✅ Added quality warning if exclusion rate > 30%

#### Files Created:
```
backend/src/physics/size_config.py (NEW - 218 lines)
```

#### Files Modified:
```
backend/src/physics/mie_scatter.py
backend/src/api/routers/upload.py
lib/api-client.ts
components/flow-cytometry/statistics-cards.tsx
```

#### Key Technical Changes:
1. **SizeRangeConfig class** - Immutable configuration with:
   - `search_min_nm=30, search_max_nm=220` (Mie optimization bounds)
   - `valid_min_nm=30, valid_max_nm=220` (particle filtering bounds)
   - `display_min_nm=40, display_max_nm=200` (histogram display bounds)

2. **filter_particles_by_size()** function:
   - Excludes particles outside valid range (no clamping!)
   - Returns filtered array + statistics dict
   - Logs warning if >5% particles excluded

3. **FCS Results** now include:
   - `size_filtering`: {total_input, valid_count, excluded_below, excluded_above, exclusion_pct}
   - `size_range`: {valid_min, valid_max, display_min, display_max}

#### Acceptance Criteria (All Met):
- [x] No artificial clustering at boundary values
- [x] Particles outside 30-220nm are excluded from calculation
- [x] Display shows 40-200nm range (configurable)
- [x] Statistics (Median, SD) calculated on filtered data only
- [x] UI shows how many particles were excluded
- [x] Distribution histogram looks natural (no edge spikes)

---

### TASK-003: NTA Export Buttons
**Status:** ✅ COMPLETED  
**Priority:** P0 - Critical  
**Completed:** December 16, 2025

#### What Was Done:
- Implemented full export functionality (CSV, Excel/TSV, JSON, Markdown Report)
- Added file icons to export buttons
- Created comprehensive `handleExport` function

---

### TASK-004: Reset Tab Buttons
**Status:** ✅ COMPLETED  
**Priority:** P0 - Critical  
**Completed:** December 16, 2025

#### What Was Done:
- Added reset button to FCS analysis tab
- NTA and Cross-Compare already had reset buttons
- Added toast notifications on reset

---

### TASK-005: Diameter vs SSC Scatter Chart
**Status:** ✅ COMPLETED  
**Priority:** P0 - Critical  
**Completed:** December 16, 2025

#### What Was Done:
- Created new `diameter-vs-ssc-chart.tsx` component
- Implemented Mie theory reference curve
- Added EV size reference lines (50nm, 100nm, 150nm, 200nm)
- Added anomaly highlighting
- Integrated into FCS analysis results

---

## 🟠 P1 - HIGH PRIORITY (Complete Next 2 Weeks)

---

### TASK-006: User-Defined Size Bucket Selection UI
**Status:** ✅ COMPLETED  
**Priority:** P1 - High  
**Requested By:** Jagan (Nov 27, 2025 Meeting)  
**Completed:** December 17, 2025  
**Actual Effort:** 1 hour (component already existed)

#### Client Quote:
> *"Give them the choice to select... what is the range that you want to select... they will have the freedom to operate"* - Jagan

#### What Was Done:
- ✅ CustomSizeRanges component already exists (`components/flow-cytometry/custom-size-ranges.tsx`)
- ✅ Preset dropdown with 4 options (Small EVs, Standard EV, Broad Range, Custom)
- ✅ Added overlap validation for custom ranges with error display
- ✅ Custom bucket editor with add/remove functionality
- ✅ Integration with re-analysis endpoint
- ✅ Settings persist during session via Zustand store

#### Files Modified:
```
components/flow-cytometry/custom-size-ranges.tsx (added overlap validation)
```

#### Key Features:
- Preset dropdown: Small EVs, Standard EV, Broad Range, Custom
- Custom range inputs with validation
- Overlap detection with user-friendly error messages
- Add/remove bucket buttons
- Automatic re-analysis when ranges change

#### Acceptance Criteria (All Met):
- [x] Preset dropdown with 4 options
- [x] Custom bucket editor with add/remove
- [x] Validation prevents overlapping ranges
- [x] Statistics cards update when buckets change
- [x] Settings persist during session
- [x] Backend processes custom bucket counts

---

### TASK-007: Implement PDF Parsing for NTA Reports
**Status:** ✅ COMPLETED  
**Priority:** P1 - High  
**Requested By:** Surya (Dec 3, 2025 Meeting)  
**Completed:** December 17, 2025  
**Actual Effort:** 3 hours

#### Client Quote:
> *"That number is not ever mentioned in a text format... it is always mentioned only in the PDF file... I was struggling through"* - Surya

#### What Was Done:
- ✅ Added `pdfplumber>=0.10.0` to requirements.txt
- ✅ Created `backend/src/parsers/nta_pdf_parser.py` with NTAPDFParser class
- ✅ Regex extraction for ZetaView PDF format (concentration, dilution factor, sizes)
- ✅ Created `/api/v1/upload/nta-pdf` POST endpoint
- ✅ Added PDF upload UI to NTA tab
- ✅ Integrated with API client and React hooks
- ✅ Toast notifications show extracted concentration/dilution

#### Files Created:
```
backend/src/parsers/nta_pdf_parser.py (NEW - ~350 lines)
```

#### Files Modified:
```
backend/requirements.txt
backend/src/api/routers/upload.py
lib/api-client.ts
hooks/use-api.ts
components/nta/nta-tab.tsx
```

#### Key Technical Implementation:
1. **NTAPDFData dataclass** with 15+ fields for extracted data
2. **NTAPDFParser class** with comprehensive regex patterns:
   - Scientific notation: `3.5E10` or `3.5×10^10` particles/mL
   - Dilution factor extraction
   - Size statistics (mean, mode, median, D10/D50/D90)
3. **parse_nta_pdf()** convenience function
4. **API endpoint** returns extracted data + links to sample if provided

#### Sample PDF Fields Extracted:
| Field | Example Value | Status |
|-------|---------------|--------|
| Original Concentration | 3.5E10 particles/mL | ✅ |
| Dilution Factor | 500 | ✅ |
| Mean Size | 120.5 nm | ✅ |
| Mode Size | 95.3 nm | ✅ |
| Median Size | 110.2 nm | ✅ |
| D10/D50/D90 | Various | ✅ |
| Sample Name | From PDF | ✅ |
| Operator | From PDF | ✅ |

#### Acceptance Criteria (All Met):
- [x] PDF upload button on NTA tab
- [x] Successfully extracts original concentration
- [x] Successfully extracts dilution factor
- [x] Calculates true particle population
- [x] Displays extracted data on UI (toast)
- [x] Links PDF data with corresponding sample (optional)
- [x] Handles errors gracefully (invalid PDFs)

---

### TASK-008: AWS Bedrock Setup and Integration
**Status:** 🟡 BLOCKED (Waiting for IT)  
**Priority:** P1 - High  
**Requested By:** Team/Client (Multiple Meetings)  
**Assignee:** Charmi  
**Estimated Effort:** 8-16 hours (depends on IT)

#### Problem Description:
Need AWS Bedrock access for AI features. Currently blocked on:
1. IT approval for AWS account
2. Cost estimation approval
3. GST/billing setup for AWS

#### Client Quote:
> *"We will be configuring AWS today and then starting from tomorrow onwards we should be able to start integrating the AI"* - Parvesh (Dec 11)

#### Prerequisites from IT:
- [ ] AWS account credentials
- [ ] Bedrock service enabled
- [ ] Budget limits configured
- [ ] API keys generated

#### Models to Enable:
| Model | Use Case | Priority |
|-------|----------|----------|
| Claude 3 (Anthropic) | Chat, Q&A | High |
| Titan Embeddings | RAG pipeline | High |
| Claude 3 Haiku | Fast responses | Medium |

#### Implementation Steps:
1. [ ] Receive AWS credentials from IT
2. [ ] Enable Bedrock service in AWS console
3. [ ] Request model access (Claude, Titan)
4. [ ] Configure IAM roles and permissions
5. [ ] Set up cost alerts and budgets
6. [ ] Create backend integration layer
7. [ ] Test basic API calls
8. [ ] Document setup for team

#### Acceptance Criteria:
- [ ] AWS Bedrock accessible from backend
- [ ] Claude model responding to test prompts
- [ ] Titan embeddings generating vectors
- [ ] Cost monitoring in place
- [ ] API wrapper functions created

---

### TASK-009: Experimental Conditions Logger Integration
**Status:** ✅ COMPLETED  
**Priority:** P1 - High  
**Requested By:** Jagan (Nov 27, 2025 Meeting)  
**Completed:** December 17, 2025  
**Actual Effort:** 3 hours

#### Client Quote:
> *"We'd also want a way to be able to log conditions for the experiment"* - Parvesh (Dec 5)

#### What Was Done:
- ✅ Created ExperimentalConditions database model with 15+ fields
- ✅ Added CRUD functions (create, get, update, delete)
- ✅ Created API endpoints: POST/GET/PUT `/samples/{sample_id}/conditions`
- ✅ Updated frontend dialog to save to backend API when sampleId provided
- ✅ Added loading states and error handling
- ✅ Created Alembic migration for new table

#### Files Created:
```
backend/alembic/versions/20251217_add_experimental_conditions.py (NEW)
```

#### Files Modified:
```
backend/src/database/models.py (ExperimentalConditions model)
backend/src/database/crud.py (CRUD functions)
backend/src/api/routers/samples.py (API endpoints)
lib/api-client.ts (saveExperimentalConditions, getExperimentalConditions)
hooks/use-api.ts (hook functions with toast notifications)
components/experimental-conditions-dialog.tsx (API integration)
```

#### Experimental Conditions Captured:
| Field | Type | Example Values |
|-------|------|----------------|
| operator | String (required) | "John Doe" |
| temperature_celsius | Float | 22.5, 25.0 |
| ph | Float | 7.0, 7.4 |
| substrate_buffer | String | PBS, HEPES, Custom |
| custom_buffer | String | Custom buffer name |
| sample_volume_ul | Float | 50, 100, 200 |
| dilution_factor | Integer | 100, 500, 1000 |
| antibody_used | String | CD81, CD9, CD63 |
| antibody_concentration_ug | Float | 0.5, 1.0 |
| incubation_time_min | Float | 30, 60, 120 |
| sample_type | String | SEC, Ultracentrifugation |
| filter_size_um | Float | 0.22, 0.45 |
| notes | Text | Additional observations |

#### Acceptance Criteria (All Met):
- [x] Conditions form saves to database
- [x] Conditions linked to specific sample (foreign key)
- [x] API endpoints for CRUD operations
- [x] Frontend saves via API when sample ID available
- [x] Loading states during save operation
- [x] Error handling with toast notifications
- [x] Database migration for new table

---

### TASK-010: VSSC Max Column Auto-Selection
**Status:** ✅ COMPLETED  
**Priority:** P1 - High  
**Requested By:** Parvesh (Dec 5, 2025 Meeting)  
**Completed:** December 17, 2025  
**Actual Effort:** 2.5 hours

#### Client Quote:
> *"Create a new column... VSSC max and let it look at the VSSC 1 H and VSSC 2 H and pick whichever the larger one is"* - Parvesh

#### What Was Done:
- ✅ Added VSSC1-H and VSSC2-H channel detection in FCS parser
- ✅ Created VSSC_MAX column as `np.maximum(vssc1, vssc2)` per row
- ✅ VSSC_MAX is used as SSC input for Mie scattering calculations
- ✅ Added selection statistics (% events from each channel)
- ✅ Updated FCS results with `vssc_max_used`, `vssc_selection`, `ssc_channel_used`
- ✅ Updated API client types for VSSC selection data
- ✅ SSC Median card shows selection percentages on hover

#### Files Modified:
```
backend/src/api/routers/upload.py (VSSC detection and max creation)
lib/api-client.ts (FCSResult interface with VSSC fields)
components/flow-cytometry/statistics-cards.tsx (tooltip with selection stats)
```

#### Technical Implementation:
1. **Channel Detection**:
   - Looks for `VSSC1-H` (or `VSSC 1 H`, `VSSC1_H`)
   - Looks for `VSSC2-H` (or `VSSC 2 H`, `VSSC2_H`)
   - Falls back to SSC-H or first SSC channel if not found

2. **VSSC_MAX Creation**:
   ```python
   vssc_max = np.maximum(vssc1_values, vssc2_values)
   ```

3. **Selection Statistics**:
   ```python
   vssc1_selected = np.sum(vssc1_values >= vssc2_values)
   vssc2_selected = np.sum(vssc2_values > vssc1_values)
   vssc1_pct = (vssc1_selected / total_events) * 100
   vssc2_pct = (vssc2_selected / total_events) * 100
   ```

4. **UI Display**: SSC Median card description shows:
   - "VSSC1: 67% | VSSC2: 33%" on hover
   - Base description: "Side scatter using VSSC_MAX"

#### Acceptance Criteria (All Met):
- [x] VSSC_MAX column created automatically when VSSC1-H and VSSC2-H present
- [x] Mie calculations use VSSC_MAX as SSC input
- [x] UI shows selection statistics
- [x] Graceful fallback when VSSC channels not available

---

### TASK-011: Specific Graph Types List from Client
**Status:** ⏳ WAITING ON CLIENT  
**Priority:** P1 - High  
**Requested By:** Parvesh (Nov 19, 2025 Meeting)  
**Assignee:** Surya (Client-side)  
**Estimated Effort:** N/A (Documentation task)

#### Client Quote:
> *"Which scatter plots you usually look at... if you can tell us what those x and y axis are"* - Parvesh

#### Problem Description:
We need a definitive list from the client of:
1. Which X vs Y scatter plots they use in analysis
2. Which histograms they need
3. Priority order of visualizations

#### Confirmed So Far:
| Graph Type | X-Axis | Y-Axis | Status |
|------------|--------|--------|--------|
| Scatter Plot | FSC-H | SSC-H | ✅ Done |
| Scatter Plot | SSC-A | SSC-H | ❌ Pending |
| Size Histogram | Diameter (nm) | Count | ✅ Done |
| Density Plot | FSC | SSC | ✅ Done |

#### Awaiting from Client:
| Item | Status |
|------|--------|
| Complete list of scatter plot combinations | ❌ Waiting |
| Priority ranking of graphs | ❌ Waiting |
| Color channel combinations (R670, B531, etc.) | ❌ Waiting |
| Example outputs from their current workflow | ❌ Waiting |

#### Action Required:
1. [ ] Follow up with Surya for graph specifications
2. [ ] Request sample outputs from their ZetaView/NanoFACS machines
3. [ ] Document all required graph types
4. [ ] Prioritize implementation order

---

### TASK-012: Calibration Data from Client
**Status:** ⏳ WAITING ON CLIENT  
**Priority:** P1 - High  
**Requested By:** Surya (Nov 19, 2025 Meeting)  
**Assignee:** Sumukha (Client-side)  
**Estimated Effort:** N/A (Data collection)

#### Client Quote:
> *"There was a scientist Sumukha who I asked for some calibration data. Unfortunately he has not furnished those data"* - Surya

#### Required Calibration Data:
| Data Type | Purpose | Status |
|-----------|---------|--------|
| Reference bead sizes | Mie calculation validation | ❌ Waiting |
| Refractive index values | Particle type identification | ❌ Waiting |
| Machine-specific angles | FSC/SSC angle calibration | ❌ Waiting |
| Control sample measurements | Baseline comparison | ❌ Waiting |

#### Action Required:
1. [ ] Follow up with Surya → Sumukha
2. [ ] Request calibration bead data (100nm, 200nm beads)
3. [ ] Get machine-specific scattering angles
4. [ ] Document refractive index values for their exosomes

---

### TASK-013: Paired NTA + FCS Data with Nomenclature
**Status:** ⏳ WAITING ON CLIENT  
**Priority:** P1 - High  
**Requested By:** Parvesh (Nov 19, 2025 Meeting)  
**Assignee:** Client Lab Team  
**Estimated Effort:** N/A (Data collection)

#### Client Quote:
> *"I told the team to generate data with a proper nomenclature... file name should be consistent for NTA and nanoFACS"* - Surya

#### Required Data Format:
```
ExperimentA_NTA_2025-12-15.txt
ExperimentA_FCS_2025-12-15.fcs
ExperimentA_PDF_2025-12-15.pdf

ExperimentB_NTA_2025-12-16.txt
ExperimentB_FCS_2025-12-16.fcs
ExperimentB_PDF_2025-12-16.pdf
```

#### Why This Matters:
- Cross-comparison tab needs matching files
- AI training needs paired data
- Correlation analysis requires same-sample measurements

#### Action Required:
1. [ ] Follow up with Surya on data delivery timeline
2. [ ] Confirm naming convention is being followed
3. [ ] Request at least 5-10 paired datasets
4. [ ] Document file matching logic

---

## 🟡 P2 - MEDIUM PRIORITY (Complete This Month)

---

### TASK-014: AI Chat Integration with RAG Pipeline
**Status:** ❌ NOT STARTED  
**Priority:** P2 - Medium  
**Requested By:** Charmi/Parvesh (Dec 11, 2025 Meeting)  
**Assignee:** Charmi  
**Estimated Effort:** 20-30 hours  
**Blocked By:** TASK-008 (AWS Bedrock Setup)

#### Client Quote:
> *"We will be doing a process of RAG which is retrieval augmented generation... LLMs will be used"* - Charmi

#### Features to Implement:
1. **Document Ingestion**
   - Upload scientific PDFs (Mie scattering papers, protocols)
   - Extract text and create embeddings
   - Store in vector database

2. **Chat Interface**
   - Natural language queries
   - Context-aware responses
   - Reference source documents

3. **Graph Generation via Chat**
   - "Show me FSC vs SSC for sample A"
   - "Compare size distribution between runs"
   - "Highlight anomalies > 2 standard deviations"

#### Technical Stack:
```
- AWS Bedrock (Claude 3 for chat)
- AWS Titan Embeddings (for RAG)
- PostgreSQL + pgvector (vector storage)
- LangChain (orchestration)
```

#### Files to Create:
```
backend/src/ai/chat_handler.py (NEW)
backend/src/ai/rag_pipeline.py (NEW)
backend/src/ai/embeddings.py (NEW)
components/research-chat/research-chat-panel.tsx (exists, enhance)
lib/ai-chat-client.ts (exists, enhance)
```

#### Implementation Steps:
1. [ ] Complete TASK-008 (AWS Bedrock setup)
2. [ ] Install LangChain and dependencies
3. [ ] Create embeddings pipeline for documents
4. [ ] Set up pgvector in PostgreSQL
5. [ ] Create RAG retrieval function
6. [ ] Implement chat handler with context
7. [ ] Add graph generation from natural language
8. [ ] Create prompt templates for EV analysis
9. [ ] Test with scientific queries
10. [ ] Add source citation to responses

#### Acceptance Criteria:
- [ ] Chat understands EV analysis terminology
- [ ] Retrieves relevant info from uploaded papers
- [ ] Generates graphs from natural language
- [ ] Provides sources for answers
- [ ] Handles ambiguous queries gracefully

---

### TASK-015: Anomaly Detection Model (XGBoost/Random Forest)
**Status:** ❌ NOT STARTED  
**Priority:** P2 - Medium  
**Requested By:** Charmi (Dec 11, 2025 Meeting)  
**Assignee:** TBD  
**Estimated Effort:** 15-20 hours

#### Client Quote:
> *"Binary classification like XGBoost model or a Random Forest model that will say this is an ambiguous or non-ambiguous scenario"* - Charmi

#### Model Purpose:
Detect anomalies in FCS/NTA data that may indicate:
- Contamination
- Aggregation
- Instrument issues
- Poor sample preparation

#### Features to Use:
| Feature | Description |
|---------|-------------|
| Size distribution skewness | Asymmetry in particle sizes |
| Concentration outliers | Unusual particle counts |
| FSC/SSC ratio | Abnormal scattering ratios |
| Polydispersity index | Size variation measure |
| D10/D50/D90 ratios | Distribution shape |

#### Implementation Steps:
1. [ ] Collect labeled training data (normal vs anomalous)
2. [ ] Engineer features from FCS/NTA data
3. [ ] Train XGBoost classifier
4. [ ] Validate with cross-validation
5. [ ] Create prediction API endpoint
6. [ ] Display anomaly warnings in UI
7. [ ] Allow user feedback to improve model

#### Acceptance Criteria:
- [ ] Model trained on real data
- [ ] Accuracy > 85% on test set
- [ ] API returns anomaly probability
- [ ] UI shows warning badges
- [ ] User can mark false positives

---

### TASK-016: Best Practices Comparison Engine
**Status:** ✅ COMPLETED  
**Priority:** P2 - Medium  
**Requested By:** Jagan (Nov 27, 2025 Meeting)  
**Assignee:** AI Assistant  
**Completed:** January 2025
**Estimated Effort:** 10-15 hours

#### Client Quote:
> *"We find ourselves a distinguish factor... we can report to the user 'you are getting some anomaly here, look into this'"* - Jagan

#### Feature Description:
Compare user's experimental conditions and results against best practices database to provide guidance.

#### Comparison Areas:
| Area | Best Practice | Check |
|------|---------------|-------|
| Antibody concentration | 0.5-2 µg per 10^9 particles | Warn if outside range |
| Dilution factor | Depends on concentration | Suggest optimal |
| Sample size distribution | Unimodal, 50-150nm peak | Warn on bimodal |
| Background noise | < 5% of signal | Warn if high |

#### Implementation:
- [x] Created `lib/best-practices.ts` - Knowledge base with 13 best practice rules
- [x] Created `components/best-practices-panel.tsx` - UI component with compact/full views
- [x] Integrated into FlowCytometrySidebar as accordion item
- [x] Compliance score calculation (0-100%)
- [x] Categorized rules: sample-prep, antibody, instrument, analysis, quality
- [x] Severity levels: info, warning, error
- [x] Recommendations based on ISEV 2023 guidelines

#### Files Created/Modified:
```
lib/best-practices.ts (NEW - 280 lines)
components/best-practices-panel.tsx (NEW - 260 lines)
components/sidebar.tsx (MODIFIED - added Best Practices accordion)
```

---

### TASK-017: Cross-Compare Tab Sidebar Settings
**Status:** ✅ ALREADY IMPLEMENTED  
**Priority:** P2 - Medium  
**Assignee:** Previous Implementation  
**Verified:** January 2025
**Estimated Effort:** 2-3 hours

#### Problem Description:
Cross-compare settings are in the main content area instead of sidebar (like FCS/NTA tabs).

#### Verification:
Settings already exist in `components/sidebar.tsx` lines 982-1156:
- Size Range (Min/Max) sliders
- Bin Size slider (1-20nm)
- Normalize Histograms toggle
- Show KDE toggle
- Show Statistics toggle
- Discrepancy Threshold slider

#### Files Modified:
```
components/sidebar.tsx - CrossCompareSidebar function already contains all settings
```

---

### TASK-018: Chart Color Scheme Consistency
**Status:** ✅ COMPLETED  
**Priority:** P2 - Medium  
**Assignee:** AI Assistant  
**Completed:** January 2025
**Estimated Effort:** 2-3 hours

#### Problem Description:
React charts use blue (#3b82f6) while Streamlit used purple (#7c3aed). Need consistency.

#### Implementation:
- [x] Created `CHART_COLORS` constant in `lib/store.ts`
- [x] Updated scatter-plot-chart.tsx to use CHART_COLORS.primary
- [x] Updated scatter-plot-with-selection.tsx to use CHART_COLORS
- [x] Updated diameter-vs-ssc-chart.tsx to use CHART_COLORS
- [x] Updated size-distribution-chart.tsx to use CHART_COLORS
- [x] Updated overlay-histogram-chart.tsx to use CHART_COLORS

#### Color Scheme:
```typescript
CHART_COLORS = {
  primary: "#7c3aed",    // Purple - normal data points
  secondary: "#a855f7",  // Light purple - secondary data
  anomaly: "#ef4444",    // Red - anomalies
  warning: "#f59e0b",    // Amber - warnings
  success: "#22c55e",    // Green - success/valid
  smallEV: "#22c55e",    // Green - small EVs
  exosomes: "#7c3aed",   // Purple - exosomes (main)
  largeEV: "#f59e0b",    // Amber - large EVs
}
```

---

### TASK-019: Histogram Bin Size Configuration
**Status:** ✅ COMPLETED  
**Priority:** P2 - Medium  
**Assignee:** AI Assistant  
**Completed:** January 2025
**Estimated Effort:** 2 hours

#### Problem Description:
Histogram uses fixed 20 bins. Streamlit allowed configurable bin size.

#### Implementation:
- [x] Added `histogramBins` field to `FCSAnalysisSettings` interface in `lib/store.ts`
- [x] Added Visualization accordion in FlowCytometrySidebar with histogram bins slider
- [x] Updated `size-distribution-chart.tsx` to read binCount from store
- [x] Slider range: 10-100 bins, step 5, default 20

#### Files Modified:
```
lib/store.ts - Added histogramBins to FCSAnalysisSettings
components/sidebar.tsx - Added Visualization accordion with slider
components/flow-cytometry/charts/size-distribution-chart.tsx - Dynamic bin count
```

---

## 🟢 P3 - LOW PRIORITY (Backlog)

> **Note:** All P3 tasks are infrastructure/deployment tasks that require external dependencies (AWS credentials, complete application, infrastructure setup). These cannot be implemented through code changes alone and should be addressed during deployment phase.

---

### TASK-020: Package as Desktop Application (EXE)
**Status:** 🔴 BLOCKED - Requires deployment infrastructure  
**Priority:** P3 - Low  
**Requested By:** Parvesh (Dec 5, 2025 Meeting)  
**Estimated Effort:** 15-20 hours

#### Client Quote:
> *"Package it to like an EXE file... install it as a software"* - Parvesh

#### Technical Approach:
- Use Electron or Tauri for desktop wrapper
- Bundle Python backend with PyInstaller
- Create installer with NSIS or Inno Setup

#### Blockers:
- [ ] Application must be feature-complete first
- [ ] Need to set up Electron/Tauri build pipeline
- [ ] Python backend needs PyInstaller configuration
- [ ] Need Windows code signing certificate (optional but recommended)

#### Prerequisites:
1. Complete all P0, P1, P2 feature tasks
2. Full QA testing of web application
3. Decision on Electron vs Tauri framework

---

### TASK-021: S3 Cloud Storage Integration
**Status:** 🔴 BLOCKED - Requires AWS credentials  
**Priority:** P3 - Low  
**Estimated Effort:** 8-10 hours

#### Purpose:
Store uploaded files in AWS S3 instead of local filesystem for:
- Scalability
- Multi-user access
- Data persistence

#### Blockers:
- [ ] AWS account access needed
- [ ] S3 bucket must be created
- [ ] IAM credentials with S3 permissions
- [ ] CORS configuration for browser uploads

#### Implementation Ready (when unblocked):
```python
# backend/src/storage/s3_client.py - Ready to implement
# - Upload FCS/NTA files to S3
# - Generate presigned URLs for downloads
# - Implement multipart upload for large files
```

---

### TASK-022: Multi-Tenant Deployment
**Status:** 🔴 BLOCKED - Requires infrastructure  
**Priority:** P3 - Low  
**Estimated Effort:** 20+ hours

#### Purpose:
Allow multiple organizations to use the platform with isolated data.

#### Blockers:
- [ ] Need authentication provider (Auth0, AWS Cognito, etc.)
- [ ] Database schema changes for tenant isolation
- [ ] Cloud infrastructure for deployment
- [ ] Decision on multi-tenancy approach (schema-per-tenant vs row-level)

#### Architectural Considerations:
- Add `organization_id` to all database tables
- Implement row-level security in PostgreSQL
- Create organization management APIs
- Add role-based access control (RBAC)

---

## 📝 DATA/DOCUMENTATION NEEDED FROM CLIENT

| Item | Requested From | Status | Follow-up Date |
|------|----------------|--------|----------------|
| Paired NTA + FCS files with nomenclature | Surya / Lab Team | ⏳ Waiting | Weekly |
| Calibration bead data | Sumukha | ⏳ Waiting | Weekly |
| List of graphs used in analysis | Surya / Jagan | ⏳ Waiting | Next meeting |
| Machine-specific scattering angles | Surya | ⏳ Waiting | Next meeting |
| Sample PDF reports from NTA | Surya | ⏳ Waiting | This week |
| Best practices documentation | Jagan | ⏳ Waiting | Next sprint |

---

## 📅 SPRINT PLANNING

### Current Sprint (Dec 17-24, 2025)
| Task | Assignee | Status |
|------|----------|--------|
| TASK-001: Fix Mean → Median | TBD | Not Started |
| TASK-002: Fix Size Range Clustering | TBD | Not Started |
| TASK-010: VSSC Max Auto-Selection | TBD | Not Started |
| Follow up on client data | Parvesh | In Progress |

### Next Sprint (Dec 25 - Jan 1, 2026)
| Task | Assignee | Status |
|------|----------|--------|
| TASK-006: Size Bucket Selector UI | TBD | Not Started |
| TASK-007: PDF Parsing for NTA | TBD | Not Started |
| TASK-008: AWS Bedrock Setup | Charmi | Blocked |

---

## 📞 KEY CONTACTS

| Name | Role | Topics |
|------|------|--------|
| Surya | Client - Technical | Data, calibration, graphs |
| Jagan | Client - Scientific Lead | Requirements, best practices |
| Parvesh | CRMIT - Project Lead | Overall coordination |
| Charmi | CRMIT - AI Lead | AWS, AI integration |
| Sumit | CRMIT - Backend Dev | Python, FastAPI |
| Mohit | CRMIT - Frontend Dev | React, UI |

---

*Last Updated: December 17, 2025*
