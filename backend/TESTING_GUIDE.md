# CRMIT Platform - Testing Guide

**Date:** November 27, 2025  
**Status:** Ready for Testing  
**Completion:** 100% ✅

---

## 🎯 Quick Start Testing

### Step 1: Start All Services

Open **3 PowerShell terminals**:

#### Terminal 1: PostgreSQL (if not running as service)
```powershell
# Usually runs as Windows service, check with:
Get-Service -Name postgresql*

# If not running:
pg_ctl -D "C:\Program Files\PostgreSQL\18\data" start
```

#### Terminal 2: Backend API
```powershell
cd "C:\CRM IT Project\EV (Exosome) Project"
.\venv\Scripts\Activate.ps1
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Verify:** Open http://localhost:8000/docs in browser

#### Terminal 3: Streamlit Frontend
```powershell
cd "C:\CRM IT Project\EV (Exosome) Project"
.\venv\Scripts\Activate.ps1
streamlit run apps/biovaram_streamlit/app.py
```

**Expected Output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

**Verify:** Open http://localhost:8501 in browser

---

## 🧪 Manual Testing Checklist

### Test 1: API Health Check ✅
**Action:** Check backend is running
```powershell
curl http://localhost:8000/health
```

**Expected Result:**
```json
{"status":"healthy","timestamp":"2025-11-27T...","database":"connected"}
```

---

### Test 2: Frontend Connection ✅
**Action:** 
1. Open http://localhost:8501
2. Look for banner at top of page

**Expected Result:**
- Green banner: "✅ Connected to backend API at http://localhost:8000"
- If red banner: Backend not running

---

### Test 3: Upload FCS File with Metadata ✅

**Action:**
1. Go to **Tab 1: Dashboard**
2. Click "Browse files" or drag & drop
3. Select file: `nanoFACS/10000 exo and cd81/Exo Control.fcs`
4. Fill metadata form:
   - **Sample ID:** `TEST_EXO_001` (required)
   - **Treatment:** `Control`
   - **Concentration:** `0` μg
   - **Preparation Method:** `SEC`
   - **Operator:** `Your Name`
   - **Notes:** `Test upload from Streamlit`
5. Click **✅ Save Metadata & Process File**

**Expected Result:**
- "✅ Metadata saved successfully!"
- "✅ Uploaded to API: Sample ID = 123"
- Sample appears in **sidebar** under "Sample Database"
- Shows: Sample ID, Treatment, Status, Created date
- Bottom shows: **🔬 FCS Analysis Results**
  - Total Events: ~50,000
  - Channels: 15-20
  - List of channel names

---

### Test 4: View Sample in Sidebar ✅

**Action:**
1. Check **left sidebar** in Tab 1
2. Look for "🧪 Sample Database" section
3. See filters: Treatment (All/CD81/CD9/etc), Status (All/uploaded/processing/etc)
4. Find your uploaded sample "TEST_EXO_001"
5. Click to expand

**Expected Result:**
- Sample listed with:
  - Treatment: Control
  - Status: uploaded
  - Created: 2025-11-27
- "View Details" button available

---

### Test 5: Filter Samples ✅

**Action:**
1. In sidebar, select filter **Treatment: CD81**
2. Click **🔄 Refresh** button

**Expected Result:**
- Only CD81 samples shown
- Count updates: "Showing X of Y samples"

---

### Test 6: Tab 2 Particle Size Analysis ✅

**Action:**
1. Go to **Tab 2: 🧪 Flow Cytometry**
2. Upload file: `nanoFACS/10000 exo and cd81/Exo+ 1ug CD81 SEC.fcs`
3. *Optional:* Expand "📋 Sample Metadata" and fill form
4. Click "📤 Upload to API & Analyze" if using API
5. Wait for auto-column detection
6. Verify FSC and SSC columns auto-selected
7. Click **Apply Selection**
8. Click **Run Analysis**

**Expected Result:**
- Progress indicator: "Building theoretical lookup..."
- Progress: "Computing particle sizes (vectorized)..."
- "Processing complete in X.Xs"
- **4 stat cards displayed:**
  - Mean Size (nm): ~70-100
  - Median Size (nm): ~70-100
  - Std Dev: ~20-40
  - Total Events: ~50,000
- Histogram plot of size distribution
- Scatter plot: Size vs Intensity

---

### Test 7: Plot Labels ✅

**Action:**
1. In Tab 2 results, check plot axis labels
2. Check section header

**Expected Result:**
- Section header: "🔬 Particle Size vs Scatter Intensity Analysis"
- Plot X-axis: "Forward Scatter (FSC-A) - Size Proxy"
- Plot Y-axis: "Side Scatter (SSC-A) - Granularity"
- Stat cards say "Mean Size" not "Mean Diameter"

---

### Test 8: Error Handling ✅

**Action:**
1. In Tab 1, upload a file
2. Leave **Sample ID** blank
3. Click "Save Metadata & Process File"

**Expected Result:**
- Red error message: "❌ Sample ID is required"
- Form does not submit
- No API call made

---

### Test 9: API Fallback ✅

**Action:**
1. Stop backend API (Ctrl+C in Terminal 2)
2. In Streamlit, upload a CSV file
3. Observe behavior

**Expected Result:**
- Red banner: "⚠️ Backend API not available. Please start the FastAPI server..."
- Yellow warning: "⚠️ Backend API not available. Processing file locally..."
- File still processed and displayed
- No sample added to sidebar database

---

### Test 10: Database Verification ✅

**Action:**
Open pgAdmin or psql:
```powershell
psql -h localhost -U postgres -d crmit_db

-- Check samples table
SELECT sample_id, treatment, status, created_at 
FROM samples 
ORDER BY created_at DESC 
LIMIT 5;

-- Check FCS results
SELECT s.sample_id, f.event_count, f.channel_count 
FROM samples s 
LEFT JOIN fcs_results f ON s.id = f.sample_id 
LIMIT 5;
```

**Expected Result:**
- `TEST_EXO_001` sample exists
- `treatment` = 'Control'
- `status` = 'uploaded' or 'completed'
- `created_at` = recent timestamp

---

## 🤖 Automated Testing

### Run End-to-End Tests

```powershell
cd "C:\CRM IT Project\EV (Exosome) Project"
python tests/test_e2e_system.py
```

**Expected Output:**
```
######################################################################
   CRMIT PLATFORM - END-TO-END SYSTEM TESTS
######################################################################

======================================================================
                           TEST 1: PREREQUISITES
======================================================================

  ✅ PASS - Python 3.11+
         Version: 3.13.0
  ✅ PASS - Backend API Running
         http://localhost:8000
  ✅ PASS - Frontend UI Running
         http://localhost:8501
  ✅ PASS - Test Data Available

======================================================================
                           TEST 2: API ENDPOINTS
======================================================================

  ✅ PASS - Health Check
         GET /health → 200
  ✅ PASS - Status Endpoint
         GET /api/v1/status → 200
  ...

======================================================================
                              TEST SUMMARY
======================================================================

  ✅ Prerequisites........................ 4/4 (100%)
  ✅ API Endpoints........................ 4/4 (100%)
  ✅ File Upload.......................... 3/3 (100%)
  ✅ Sample Filtering..................... 2/2 (100%)
  ✅ Data Visualization................... 1/1 (100%)
  ✅ Error Handling....................... 2/2 (100%)
  ✅ Performance.......................... 2/2 (100%)

Overall Results:
  Total Tests: 18
  Passed: 18
  Failed: 0
  Success Rate: 100.0%

🎉 ALL TESTS PASSED! System is ready for production.
```

---

## 🐛 Troubleshooting

### Issue: "Module not found: api_client"
**Solution:**
```powershell
cd "C:\CRM IT Project\EV (Exosome) Project\apps\biovaram_streamlit"
ls api_client.py  # Verify file exists

# If missing, the file should be in the same directory as app.py
```

### Issue: "Connection refused to database"
**Solution:**
```powershell
# Check PostgreSQL service
Get-Service -Name postgresql*

# Start if stopped
Start-Service postgresql-x64-18

# Or manually:
pg_ctl -D "C:\Program Files\PostgreSQL\18\data" start

# Test connection:
psql -h localhost -U postgres -d crmit_db
```

### Issue: "Backend API not available"
**Solution:**
```powershell
# Check if uvicorn is running
Get-Process | Where-Object {$_.ProcessName -like "*python*"}

# Check port 8000
netstat -ano | findstr :8000

# Restart backend:
cd "C:\CRM IT Project\EV (Exosome) Project"
uvicorn src.api.main:app --reload
```

### Issue: "Import error: requests"
**Solution:**
```powershell
pip install requests
# Or reinstall all:
pip install -r requirements.txt
```

### Issue: Streamlit shows old code
**Solution:**
```powershell
# Stop Streamlit (Ctrl+C)
# Clear cache:
Remove-Item -Recurse -Force "$env:USERPROFILE\.streamlit\cache"

# Restart:
streamlit run apps/biovaram_streamlit/app.py
```

---

## 📊 Success Criteria

### ✅ All Tests Pass When:
- [ ] Backend API responds to http://localhost:8000/health
- [ ] Streamlit UI loads at http://localhost:8501
- [ ] File upload works (FCS/NTA)
- [ ] Metadata form submits successfully
- [ ] Sample appears in sidebar database
- [ ] Sample details display correctly
- [ ] Filters work (Treatment, Status)
- [ ] Tab 2 analysis completes
- [ ] Plot labels show "Size vs Intensity"
- [ ] Database contains uploaded samples
- [ ] Automated tests pass: `python tests/test_e2e_system.py`

---

## 📝 Test Results Log

**Date:** _____________  
**Tester:** _____________  

| Test # | Test Name | Status | Notes |
|--------|-----------|--------|-------|
| 1 | API Health Check | ⬜ | |
| 2 | Frontend Connection | ⬜ | |
| 3 | Upload FCS File | ⬜ | |
| 4 | View Sample in Sidebar | ⬜ | |
| 5 | Filter Samples | ⬜ | |
| 6 | Tab 2 Analysis | ⬜ | |
| 7 | Plot Labels | ⬜ | |
| 8 | Error Handling | ⬜ | |
| 9 | API Fallback | ⬜ | |
| 10 | Database Verification | ⬜ | |
| 11 | Automated Tests | ⬜ | |

**Overall Status:** ⬜ Pass / ⬜ Fail  
**Comments:** ___________________________________________

---

## 🎉 Next Steps After Testing

Once all tests pass:

1. **Deploy to staging server**
   - Follow `DEPLOYMENT.md` guide
   - Use Docker or Windows Server setup

2. **Train users**
   - Show upload workflow
   - Explain metadata fields
   - Demonstrate filtering

3. **Monitor performance**
   - Check API response times
   - Monitor database size
   - Review logs regularly

4. **Schedule backups**
   - Daily database backups
   - Weekly full system backups

5. **Production launch** 🚀

---

**Last Updated:** November 27, 2025  
**Version:** 1.0  
**Status:** Production Ready ✅
