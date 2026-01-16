# 🎯 BioVaram EV Analysis Platform - January 7, 2025 Execution Plan

**Created:** December 31, 2025  
**Deadline:** January 7, 2025 (Customer Meeting)  
**Working Days Available:** 6 days (Dec 31 - Jan 6)

---

## 📊 Executive Summary

This plan outlines a focused 6-day sprint to complete 5 priority tasks before the customer meeting. The strategy prioritizes **customer-facing features first** (T-003), followed by **quick wins** (CRMIT-005), and then **progressive enhancements** (CRMIT-008, CRMIT-002, CRMIT-003).

### Task Overview

| Priority | ID | Task | Est. Effort | Target Day |
|----------|-----|------|-------------|------------|
| 🔴 P1 | T-003 | Previous Analysis Review | 1 day | Day 1 |
| 🟢 P2 | CRMIT-005 | Excel Export | 0.5 day | Day 2 AM |
| 🟡 P3 | CRMIT-008 | Anomaly Highlighting | 1.5 days | Day 2 PM - Day 3 |
| 🟡 P4 | CRMIT-002 | Auto Axis Selection | 2 days | Day 4-5 AM |
| 🟠 P5 | CRMIT-003 | Alert System | 2 days | Day 5 PM - Day 6 |

---

## 📅 Day-by-Day Implementation Schedule

### Day 1: December 31, 2025 (Tuesday)
#### Focus: T-003 - Previous Analysis Review

**Objective:** Make sidebar sample selection load saved analysis data.

**Morning (4 hours):**
1. **Backend API Enhancement**
   - Modify `backend/src/api/routers/samples.py`
   - Add endpoint `GET /samples/{id}/full-analysis` returning complete FCS/NTA results
   - Include: statistics, size distribution, scatter data, experimental conditions

2. **Frontend API Client**
   - Update `lib/api-client.ts` - Add `loadSampleAnalysis(sampleId)` method
   - Update `hooks/use-api.ts` - Add `useSampleAnalysis` hook

**Afternoon (4 hours):**
3. **Store State Management**
   - Modify `lib/store.ts`
   - Add `loadSavedAnalysis(sampleId)` action
   - Add `isLoadingAnalysis` state

4. **Sidebar Integration**
   - Modify `components/sidebar.tsx`
   - Wire `onSampleClick` handler to:
     - Call `loadSampleAnalysis(sampleId)`
     - Switch to appropriate tab (FCS/NTA)
     - Populate store state with loaded results

**Deliverable:** Clicking a sample in sidebar loads its full analysis.

---

### Day 2: January 1, 2025 (Wednesday)
#### Focus: CRMIT-005 (Excel Export) + CRMIT-008 Start

**Morning (4 hours) - Excel Export:**

1. **Backend Setup**
   - Add `openpyxl>=3.1.0` to `backend/requirements.txt`
   - Create `backend/src/api/routers/export.py`
   - Implement `POST /export/excel/{sample_id}` endpoint

2. **Excel Structure:**
   ```
   Sheet 1: Summary (sample info, date, key metrics)
   Sheet 2: FCS Statistics (D10, D50, D90, mean, median, CV)
   Sheet 3: NTA Statistics (if applicable)
   Sheet 4: Size Distribution (binned histogram data)
   Sheet 5: Raw Events (first 10,000 events for FCS)
   ```

3. **Frontend Integration**
   - Add `exportToExcel()` to `lib/api-client.ts`
   - Update `lib/export-utils.ts` with `downloadExcelReport()`
   - Add Excel button to export dropdown in UI

**Afternoon (4 hours) - Anomaly Highlighting Start:**

4. **Scatter Plot Enhancement**
   - Modify `components/flow-cytometry/charts/scatter-plot-chart.tsx`
   - Enhance existing `anomalousIndices` prop rendering
   - Add red color (#ef4444) for anomaly points
   - Increase point size for visibility
   - Add z-index priority (render on top)

**Deliverable:** Excel export working, anomaly highlighting in progress.

---

### Day 3: January 2, 2025 (Thursday)
#### Focus: CRMIT-008 - Anomaly Highlighting (Complete)

**Morning (4 hours):**

1. **Complete All Scatter Plot Charts**
   - `scatter-plot-with-selection.tsx` - Add anomaly layer
   - `diameter-vs-ssc-chart.tsx` - Add anomaly overlay

2. **Legend & Tooltip**
   - Add legend showing "Normal" (purple) vs "Anomaly" (red)
   - Tooltip enhancement: "⚠️ Anomaly detected" for flagged points

**Afternoon (4 hours):**

3. **Threshold Configuration UI**
   - Add slider in Settings panel for anomaly threshold (1-3 std dev)
   - Store threshold in `lib/store.ts` FCS settings

4. **Backend Integration**
   - Verify `src/visualization/anomaly_detection.py` returns indices
   - Ensure API response includes anomaly data

**Deliverable:** All scatter plots show red dots for anomalous points.

---

### Day 4: January 3, 2025 (Friday)
#### Focus: CRMIT-002 - Auto Axis Selection (Backend Integration)

**Note:** Backend already exists at `src/visualization/auto_axis_selector.py`

**Morning (4 hours):**

1. **API Endpoint**
   - Create or modify `backend/src/api/routers/analysis.py`
   - Add `GET /analysis/{sample_id}/suggest-axes` endpoint
   - Call `AutoAxisSelector.select_best_axes()`
   - Return: recommended X/Y axis pair + confidence score

2. **Response Schema:**
   ```json
   {
     "recommended": {
       "x_axis": "FSC-A",
       "y_axis": "SSC-A",
       "score": 0.95,
       "reasoning": "High variance, low correlation"
     },
     "alternatives": [
       {"x_axis": "FSC-H", "y_axis": "SSC-H", "score": 0.82}
     ]
   }
   ```

**Afternoon (4 hours):**

3. **Frontend API Integration**
   - Add `getSuggestedAxes()` to `lib/api-client.ts`
   - Add `suggestedAxes` state to store

4. **Store Updates**
   - Modify `lib/store.ts` to include suggested axes in FCSAnalysisSettings

**Deliverable:** API endpoint returns axis suggestions.

---

### Day 5: January 4, 2025 (Saturday)
#### Focus: CRMIT-002 (UI Complete) + CRMIT-003 Start

**Morning (4 hours) - Auto Axis Selector UI:**

1. **New Component**
   - Create `components/flow-cytometry/auto-axis-selector.tsx`
   - Display: "💡 Suggested: FSC-A vs SSC-A (95% confidence)"
   - "Apply Suggestion" button

2. **Integration**
   - Add to `flow-cytometry-tab.tsx` near axis dropdowns
   - Call API on file upload
   - Show suggestion badge

**Afternoon (4 hours) - Alert System Foundation:**

3. **Database Migration**
   - Create `backend/alembic/versions/xxx_add_alerts_table.py`
   ```sql
   CREATE TABLE alerts (
       id SERIAL PRIMARY KEY,
       sample_id INTEGER REFERENCES samples(id),
       alert_type VARCHAR(50),
       severity VARCHAR(20),
       message TEXT,
       created_at TIMESTAMP DEFAULT NOW(),
       acknowledged BOOLEAN DEFAULT FALSE,
       acknowledged_at TIMESTAMP NULL
   );
   ```

4. **Database Model**
   - Add `Alert` model to `backend/src/database/models.py`

**Deliverable:** Auto axis selector in UI, alerts table created.

---

### Day 6: January 5-6, 2025 (Sunday-Monday)
#### Focus: CRMIT-003 - Alert System (Complete) + Final Testing

**Day 6 AM (4 hours):**

1. **Alerts API Router**
   - Create `backend/src/api/routers/alerts.py`
   - Endpoints:
     - `GET /alerts` - List all alerts (with filters)
     - `GET /alerts/{sample_id}` - Alerts for sample
     - `POST /alerts` - Create alert (internal use)
     - `PATCH /alerts/{id}/acknowledge` - Mark as seen

2. **Alert Generation**
   - Modify `src/visualization/anomaly_detection.py`
   - Auto-generate alert when anomaly count > threshold
   - Severity levels: low (< 5%), medium (5-10%), high (> 10%)

**Day 6 PM (4 hours):**

3. **Dashboard Alerts Panel**
   - Create `components/dashboard/alerts-panel.tsx`
   - Show recent alerts with severity badges
   - Click to navigate to sample

4. **Final Integration & Testing**
   - Frontend API client methods for alerts
   - Integration testing across all features
   - Bug fixes and polish

**Buffer Time (Jan 6 PM):**
   - Address any blockers
   - Demo preparation
   - Documentation updates

**Deliverable:** Complete alert system with dashboard panel.

---

## 🔗 Task Dependencies

```
                    ┌─────────────────────┐
                    │ T-003: Previous     │ ◄── Must complete first
                    │ Analysis Review     │     (enables loading saved data)
                    └─────────┬───────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ CRMIT-005: Excel │ │ CRMIT-008:       │ │ CRMIT-002: Auto  │
│ Export           │ │ Anomaly          │ │ Axis Selection   │
│ (Independent)    │ │ Highlighting     │ │ (Backend exists) │
└──────────────────┘ └────────┬─────────┘ └──────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ CRMIT-003: Alert    │ ◄── Depends on anomaly
                    │ System              │     detection working
                    └─────────────────────┘
```

### Parallelization Opportunities

| Day | Can Run in Parallel |
|-----|---------------------|
| Day 2 | CRMIT-005 (AM) + CRMIT-008 (PM) - Different code paths |
| Day 5 | CRMIT-002 UI + CRMIT-003 DB setup - Frontend vs Backend |

---

## 📁 Files to Create/Modify

### New Files to Create

| File | Task | Purpose |
|------|------|---------|
| `backend/src/api/routers/export.py` | CRMIT-005 | Excel export endpoint |
| `backend/src/api/routers/alerts.py` | CRMIT-003 | Alerts CRUD API |
| `backend/alembic/versions/xxx_add_alerts.py` | CRMIT-003 | DB migration |
| `components/flow-cytometry/auto-axis-selector.tsx` | CRMIT-002 | Axis suggestion UI |
| `components/dashboard/alerts-panel.tsx` | CRMIT-003 | Alert dashboard widget |

### Files to Modify

| File | Tasks | Changes |
|------|-------|---------|
| `backend/src/api/routers/samples.py` | T-003 | Add full-analysis endpoint |
| `backend/src/database/models.py` | CRMIT-003 | Add Alert model |
| `backend/requirements.txt` | CRMIT-005 | Add openpyxl |
| `lib/store.ts` | T-003, CRMIT-002 | Add loadSavedAnalysis, suggestedAxes |
| `lib/api-client.ts` | All | Add new API methods |
| `hooks/use-api.ts` | T-003 | Add useSampleAnalysis hook |
| `components/sidebar.tsx` | T-003 | Wire sample click handler |
| `components/flow-cytometry/charts/*.tsx` | CRMIT-008 | Enhance anomaly rendering |
| `components/flow-cytometry/flow-cytometry-tab.tsx` | CRMIT-002 | Integrate axis selector |

---

## ⚠️ Risk Mitigation

### Risk 1: CRMIT-003 (Alert System) May Not Fully Complete

**Probability:** Medium  
**Impact:** Medium  
**Mitigation:**
- Prioritize core CRUD operations
- Skip email notifications for demo (phase 2)
- Deliver basic alerts panel, acknowledge feature as stretch goal

### Risk 2: Database Migration Issues

**Probability:** Low  
**Impact:** High  
**Mitigation:**
- Test migration on dev database first
- Keep backup of `crmit.db`
- Have rollback script ready

### Risk 3: Authentication Integration Gaps

**Probability:** Low  
**Impact:** Medium  
**Mitigation:**
- Verify T-004 (auth) works with sample queries
- Test user_id associations before T-003 work
- Fallback: Support non-authenticated mode for demo

---

## ✅ Definition of Done

### T-003: Previous Analysis Review
- [ ] Clicking sample in sidebar loads its analysis
- [ ] FCS tab populates with stored statistics
- [ ] Charts render with loaded data
- [ ] Settings reflect saved experimental conditions

### CRMIT-005: Excel Export
- [ ] "Export to Excel" button in UI
- [ ] Multi-sheet Excel file downloads
- [ ] Contains: Summary, Statistics, Size Distribution
- [ ] Works for both FCS and NTA samples

### CRMIT-008: Anomaly Highlighting
- [ ] Red dots visible on scatter plots for anomalies
- [ ] Legend distinguishes normal vs anomaly points
- [ ] Tooltip shows anomaly status
- [ ] Threshold is configurable

### CRMIT-002: Auto Axis Selection
- [ ] API returns axis suggestions
- [ ] UI shows "Suggested: X vs Y" badge
- [ ] "Apply Suggestion" updates dropdowns
- [ ] Works after file upload

### CRMIT-003: Alert System
- [ ] Alerts table in database
- [ ] Alerts generated on anomaly detection
- [ ] Dashboard shows recent alerts
- [ ] Alerts link to sample details

---

## 📞 Daily Standup Checkpoints

| Day | End-of-Day Goal | Verify With |
|-----|-----------------|-------------|
| Day 1 | Sample click loads analysis | Test sidebar → FCS tab |
| Day 2 | Excel downloads, anomaly colors visible | Download file, visual check |
| Day 3 | All charts show anomalies | Screenshot all chart types |
| Day 4 | Axis suggestions API working | Postman/curl test |
| Day 5 | Axis selector in UI, alerts table created | UI visible, DB check |
| Day 6 | Full integration working | End-to-end demo flow |

---

## 🎯 Demo Script for Jan 7 Meeting

1. **Login** (T-004 ✅) → Show authentication works
2. **Upload FCS file** → Analysis runs automatically
3. **View scatter plot** → Point out red anomaly dots (CRMIT-008)
4. **Note suggested axes** → Click "Apply Suggestion" (CRMIT-002)
5. **Export to Excel** → Download and open file (CRMIT-005)
6. **Navigate away, click sidebar sample** → Previous analysis loads (T-003)
7. **Dashboard** → Show alerts panel (CRMIT-003)

---

*Plan created: December 31, 2025*  
*Last updated: December 31, 2025*
uld wo