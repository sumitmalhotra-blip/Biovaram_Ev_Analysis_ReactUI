# Changes Since Last Git Push - January 29, 2026

## Summary
This document lists all changes made since the last git push for manual review. Some changes may have introduced bugs that need to be reverted.

---

## MODIFIED FILES

### 1. `backend/src/api/routers/samples.py`
**Changes Made:**
- `/scatter-data` endpoint: Changed from single-solution Mie to multi-solution Mie using VSSC/BSSC channels
- `/size-bins` endpoint: 
  - Added cache lookup from FCSResult table (instant response)
  - Added fallback to multi-solution Mie calculation
  - Increased sample size from 10,000 to 100,000 events
  - Size bin thresholds: Small <50nm, Medium 50-200nm, Large >200nm
- `/fcs/values` endpoint: Changed to multi-solution Mie
- `/reanalyze` endpoint: Added multi-solution Mie support
- `ReanalyzeRequest` model: Added calibration_mode, bead_material, bead_size, fsc_angle_range, ssc_angle_range fields

**Potential Issues:**
- ❌ `/size-bins` cache query may fail: "Multiple rows were found when one or none was required"
- ⚠️ Multi-solution Mie may be slower than original

---

### 2. `backend/src/api/routers/upload.py`
**Changes Made:**
- Added size bins calculation during FCS file upload
- Size bins are cached to FCSResult table for fast retrieval
- Added 100,000 event sampling for size bin calculation
- Added `size_bins_cache` dict to `fcs_results`
- Updated `create_fcs_result()` call to include:
  - `particle_size_d10_nm`, `particle_size_d90_nm`, `particle_size_std_nm`
  - `size_bin_small_count`, `size_bin_medium_count`, `size_bin_large_count`
  - `size_bin_small_pct`, `size_bin_medium_pct`, `size_bin_large_pct`
  - `size_bins_calculated`

**Potential Issues:**
- ⚠️ Additional processing time during upload (~10-15 seconds)

---

### 3. `backend/src/database/models.py`
**Changes Made:**
- Added new columns to `FCSResult` model:
  ```python
  size_bin_small_count = Column(Integer, nullable=True)
  size_bin_medium_count = Column(Integer, nullable=True)
  size_bin_large_count = Column(Integer, nullable=True)
  size_bin_small_pct = Column(Float, nullable=True)
  size_bin_medium_pct = Column(Float, nullable=True)
  size_bin_large_pct = Column(Float, nullable=True)
  size_bins_calculated = Column(Boolean, nullable=True, default=False)
  ```

**Potential Issues:**
- ⚠️ Requires database migration (already applied: `b67fc2b4d806`)

---

### 4. `backend/src/physics/mie_scatter.py`
**Changes Made:**
- Line 238: Fixed `miepython.single_sphere()` call from 4 args to 3 args (for miepython 3.0.2)
  - Before: `qext, qsca, qback, g = miepython.single_sphere(self.m, x, 0, True)`
  - After: `qext, qsca, qback, g = miepython.single_sphere(self.m, x, 0)`

**Potential Issues:**
- None - this was a bug fix

---

### 5. `components/flow-cytometry/charts/event-vs-size-chart.tsx`
**Changes Made:**
- Line 77: Increased `max_events` from 10,000 to 50,000

**Potential Issues:**
- ⚠️ May cause slower chart rendering

---

### 6. `components/flow-cytometry/calibration-settings-panel.tsx` (NEW FILE)
**Changes Made:**
- This is a NEW file - entire component was created
- Provides calibration settings UI for FCS analysis
- Multiple fixes for TypeError with `detectedSettings.channels`

**Potential Issues:**
- ❌ TypeError may still occur if `detectedSettings` is undefined
- ⚠️ Component may be causing sidebar overflow issues

---

### 7. `components/sidebar.tsx`
**Changes Made:**
- Imported `CalibrationSettingsPanel` component
- **REMOVED** the old "Experiment Parameters" accordion section (~120 lines)
- **REMOVED** the old "Angular Parameters" accordion section (~50 lines)
- **REPLACED** with `<CalibrationSettingsPanel />` component inside the sidebar
- Changed Accordion `defaultValue` from `["params", "angles", "analysis", "categories"]` to `["analysis", "categories"]`

**Potential Issues:**
- ❌ **HIGH RISK**: Major structural change - removed inline controls
- ⚠️ CalibrationSettingsPanel may cause overflow/height issues
- ⚠️ If CalibrationSettingsPanel errors, entire sidebar may break

**To Revert:**
```bash
git checkout HEAD -- components/sidebar.tsx
```

---

### 8. `lib/api-client.ts`
**Changes Made:**
- Minor changes (likely timeout or endpoint updates)

---

### 9. `lib/store.ts`
**Changes Made:**
- **Added new fields to `FCSAnalysisSettings` interface:**
  - `calibrationMode: 'calibrated' | 'theoretical'`
  - `beadMaterial: 'polystyrene' | 'silica' | 'pmma'`
  - `beadSize: number`
  - `detectedSettings?: { wavelength_nm, confidence, instrument, fsc_angle_range, ssc_angle_range, channels }`
  - `showAdvancedSettings: boolean`

- **Modified `setFCSFileMetadata` function:**
  - Changed from simple setter to complex function
  - Auto-populates `fcsAnalysisSettings` from metadata's `recommended_settings`
  - Creates default calibration settings when metadata is received

**Potential Issues:**
- ❌ **HIGH RISK**: If `detectedSettings` structure doesn't match expected format, it will crash
- ⚠️ Type safety issues - TypeScript may not catch undefined access
- ⚠️ The auto-population may overwrite user settings unexpectedly

**To Revert:**
```bash
git checkout HEAD -- lib/store.ts
```

---

## NEW FILES

### 1. `backend/alembic/versions/b67fc2b4d806_add_size_bins_cache_columns_to_fcsresult.py`
- Database migration for size bins cache columns

### 2. `backend/docs/technical/PLATFORM_TECHNICAL_GUIDE.md`
- Technical documentation

### 3. `backend/docs/technical/PARTICLE_SIZING_AND_DISTRIBUTION_ANALYSIS.md`
- Technical documentation on Gaussian/particle sizing

### 4. `backend/src/utils/instrument_detection.py`
- Instrument detection utility

### 5. `components/flow-cytometry/calibration-settings-panel.tsx`
- New calibration settings panel component

### 6. `components/cross-compare/supplementary-metadata-table.tsx`
- New component for cross-compare

### 7. `components/cross-compare/validation-summary-card.tsx`
- New component for cross-compare

---

## KNOWN BUGS INTRODUCED
l
1. ✅ **FIXED: "Multiple rows were found when one or none was required"** - `/size-bins` endpoint
   - Cause: `scalar_one_or_none()` fails when sample has multiple FCSResult records
   - Fix Applied: Changed to `.scalars().first()` with `.limit(1)` at line 1357

2. **Sidebar not visible / Frozen UI** - ❌ NOT FIXED
   - **Root Cause Identified**: 
     - sidebar.tsx now embeds `<CalibrationSettingsPanel />` component
     - CalibrationSettingsPanel accesses `detectedSettings.channels.map()` without null checks
     - If metadata never loads or errors, the panel crashes and breaks sidebar
   - **Files to check**: 
     - `components/flow-cytometry/calibration-settings-panel.tsx`
     - `components/sidebar.tsx`
     - `lib/store.ts`

3. **UI lagging/freezing** - ⚠️ PARTIALLY ADDRESSED
   - Cause: Increased event counts (50K in charts, 100K in size bins)
   - Also: CalibrationSettingsPanel may be re-rendering too often
   - Also: Multiple API calls in parallel

4. **CalibrationSettingsPanel TypeError** - ⚠️ MAY STILL OCCUR
   - Error: `Cannot read properties of undefined (reading 'map')`
   - Location: calibration-settings-panel.tsx accessing `detectedSettings.channels`
   - We added Array.isArray checks but component may still have issues

---

## RECOMMENDED ACTIONS

### MOST LIKELY FIX FOR SIDEBAR/FROZEN UI:
**The main problem is the CalibrationSettingsPanel component inside sidebar.tsx**

Option A - Quick Fix (Safest):
```bash
git checkout HEAD -- components/sidebar.tsx
```
This will restore the old sidebar with inline controls (the way it was before)

Option B - Keep New Panel But Fix Errors:
Need to add error boundaries and null checks in `CalibrationSettingsPanel`

### Other Quick Fixes to Try:
1. ✅ DONE: Fixed the `/size-bins` cache query to use `.first()` instead of `.scalar_one_or_none()`
2. ✅ DONE: Reduced `max_events` back to 10,000 in event-vs-size-chart.tsx
3. ✅ DONE: Added Error Boundary wrapper to CalibrationSettingsPanel
4. ✅ DONE: Added `overflow-hidden` and `max-h-[60vh] overflow-y-auto` to CardContent to fix overflow

### If Issues Persist - Revert Options:
1. `git checkout HEAD -- backend/src/api/routers/samples.py` - Revert samples.py changes
2. `git checkout HEAD -- components/flow-cytometry/charts/event-vs-size-chart.tsx` - Revert chart changes
3. `git checkout HEAD -- lib/store.ts` - Revert store changes

---

## GIT COMMANDS TO REVERT ALL CHANGES

```bash
# To see all changes
git diff HEAD

# To revert a specific file
git checkout HEAD -- <filepath>

# To revert ALL changes (nuclear option)
git checkout HEAD -- .

# To stash changes for later review
git stash push -m "Changes from Jan 29 session"
```
