# Next Steps Roadmap - Post Documentation
**Date:** November 19, 2025  
**Status:** DOCUMENTATION COMPLETE ✅ - Ready for next phase

---

## 🎯 Current Status

### ✅ Completed (100%)
1. **Backend Architecture** - 7-layer modular design
2. **Data Processing Pipeline** - FCS + NTA batch processing
3. **Mie Scatter Physics** - Size calculation from scatter
4. **Multi-Modal Fusion** - FCS + NTA integration
5. **Visualization Suite** - Publication-quality plots
6. **Quality Control** - Automated QC checks
7. **Comprehensive Documentation** - 19 files with inline comments

### 📊 Codebase Health
- Production code: 36 files (fully documented)
- Test coverage: Basic (needs expansion)
- Documentation: 95%+ critical path coverage
- Architecture compliance: 100%

---

## 🚀 Phase 1: Immediate Next Steps (Week 1-2)

### 1.1 Codebase Cleanup ⚡ PRIORITY
**Status:** Ready to execute  
**Time:** 2 hours  
**Owner:** Backend team

**Actions:**
- [ ] Review CLEANUP_PLAN.md
- [ ] Create git backup: `git tag pre-cleanup-backup`
- [ ] Delete 22 test/obsolete scripts
- [ ] Delete 17 redundant documentation files
- [ ] Clean __pycache__ directories
- [ ] Update .gitignore
- [ ] Test core pipelines still work

**Deliverable:** Clean, production-ready codebase

---

### 1.2 Unit Testing Suite 🧪
**Status:** 70% of code lacks tests  
**Time:** 1 week  
**Owner:** Backend team

**Priority Test Coverage:**
1. **src/physics/mie_scatter.py**
   - Test size calculation accuracy
   - Test calibration curve generation
   - Test edge cases (outliers, noise)

2. **src/preprocessing/quality_control.py**
   - Test QC thresholds
   - Test pass/fail logic
   - Test error handling

3. **src/fusion/sample_matcher.py**
   - Test exact matching
   - Test fuzzy matching (threshold validation)
   - Test unmatched sample handling

4. **Integration tests:**
   - End-to-end pipeline: FCS → Processing → Plots
   - End-to-end: NTA → Processing → Plots
   - Multi-modal: FCS + NTA → Fusion → Features

**Tools:**
```bash
pip install pytest pytest-cov pytest-mock
pytest tests/ --cov=src --cov-report=html
```

**Target:** 80% code coverage

---

### 1.3 Configuration Management 🔧
**Status:** Hardcoded values need extraction  
**Time:** 2-3 days  
**Owner:** Backend team

**Create config files:**

1. **config/processing_config.yaml**
```yaml
fcs:
  min_events: 1000
  max_cv: 100
  outlier_filter_percentile: 99.9
  
nta:
  min_concentration: 1e8
  max_concentration: 1e13
  valid_size_range: [30, 200]
  
mie:
  calibration_method: "percentile"
  refractive_index_particle: 1.45
  refractive_index_medium: 1.33
  wavelength_nm: 488
```

2. **config/paths_config.yaml**
```yaml
data:
  raw_fcs: "data/raw/fcs"
  raw_nta: "data/raw/nta"
  processed: "data/processed"
  parquet: "data/parquet"
  
output:
  figures: "figures"
  reports: "reports"
  logs: "logs"
```

**Benefits:**
- Easy parameter tuning without code changes
- Environment-specific configs (dev/test/prod)
- Version control for parameters

---

### 1.4 CI/CD Pipeline 🔄
**Status:** Not implemented  
**Time:** 1 week  
**Owner:** DevOps + Backend

**GitHub Actions Workflow:**

**.github/workflows/ci.yml**
```yaml
name: Backend CI/CD

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest tests/ --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - name: Lint with flake8
        run: |
          pip install flake8
          flake8 src/ scripts/ --max-line-length=120
```

**Benefits:**
- Automatic testing on every commit
- Catch bugs before they reach production
- Code quality enforcement

---

## 🔬 Phase 2: Research & Validation (Week 3-4)

### 2.1 Mie Scatter Validation 📊
**Status:** Implemented, needs biological validation  
**Time:** 1 week  
**Owner:** Research scientist + Backend

**Tasks:**
1. **Collect matched FCS + NTA samples:**
   - Need 20+ samples with both FCS and NTA data
   - Cover size range: 40-150nm
   - Include different markers (CD9, CD81, CD63)

2. **Run validation analysis:**
   ```bash
   python scripts/validate_fcs_vs_nta.py \
     --fcs data/processed/fcs \
     --nta data/parquet/nta \
     --output figures/validation_report.png
   ```

3. **Check acceptance criteria:**
   - Pearson R > 0.8? ✅/❌
   - Mean error < 10nm? ✅/❌
   - MAPE < 20%? ✅/❌

4. **If validation fails:**
   - Adjust Mie calibration parameters
   - Check for systematic bias
   - Re-run with filtered outliers

**Deliverable:** Validation report for publication

---

### 2.2 Benchmark Against Literature 📚
**Status:** Not started  
**Time:** 3-4 days  
**Owner:** Research scientist

**Compare results with:**
1. **FCM-Pass (Görgens 2019)**
   - Size distributions
   - Marker detection rates
   - Sensitivity/specificity

2. **Commercial NTA (Malvern/Particle Metrix)**
   - Size accuracy
   - Concentration measurements
   - Reproducibility

3. **Published exosome datasets:**
   - EV-TRACK database
   - MISEV2018 reference samples

**Questions to answer:**
- Does our sizing agree with literature?
- Are marker detection rates comparable?
- Any systematic differences?

---

### 2.3 Performance Optimization 🚀
**Status:** Works but slow for large datasets  
**Time:** 1 week  
**Owner:** Backend team

**Profile current performance:**
```python
# Add timing to key functions
import time
from functools import wraps

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"{func.__name__} took {elapsed:.2f}s")
        return result
    return wrapper
```

**Optimization targets:**
1. **Mie calculation** (currently slowest)
   - Vectorize calculations (use numpy broadcasting)
   - Cache repeated calculations
   - Consider GPU acceleration (cupy) for large files

2. **Parquet I/O**
   - Use PyArrow tables directly (avoid pandas conversion)
   - Enable dictionary encoding for categorical columns
   - Use compression (snappy is fast)

3. **Plotting**
   - Subsample for density plots (10k events max)
   - Use hexbin instead of scatter for large datasets
   - Parallel plot generation (multiprocessing)

**Target:** 10x speedup for 100k+ event files

---

## 🎨 Phase 3: Frontend Integration (Week 5-8)

### 3.1 API Development 🔌
**Status:** Placeholder exists (integration/api_bridge.py)  
**Time:** 2 weeks  
**Owner:** Backend + Frontend teams

**REST API endpoints needed:**

```python
# FastAPI implementation
from fastapi import FastAPI, UploadFile
from pydantic import BaseModel

app = FastAPI()

# 1. File Upload
@app.post("/api/upload/fcs")
async def upload_fcs(file: UploadFile, metadata: dict):
    """Upload FCS file with metadata from popup"""
    pass

# 2. Processing Status
@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Check processing status"""
    pass

# 3. Results Retrieval
@app.get("/api/results/{sample_id}")
async def get_results(sample_id: str):
    """Get processed results + plots"""
    pass

# 4. Batch Processing
@app.post("/api/batch/process")
async def batch_process(sample_ids: list[str]):
    """Process multiple samples"""
    pass
```

**Features:**
- Async processing (Celery/RQ)
- Progress tracking
- Error handling
- Result caching

---

### 3.2 Database Schema 💾
**Status:** Using Parquet files (good for ML, not for UI queries)  
**Time:** 1 week  
**Owner:** Backend team

**Add PostgreSQL/MongoDB for:**

**Sample Metadata:**
```sql
CREATE TABLE samples (
    sample_id VARCHAR(255) PRIMARY KEY,
    biological_sample_id VARCHAR(100) NOT NULL,
    treatment VARCHAR(50) NOT NULL,
    concentration_ug FLOAT,
    preparation_method VARCHAR(50),
    experiment_date DATE,
    operator VARCHAR(100),
    upload_timestamp TIMESTAMP DEFAULT NOW(),
    processing_status VARCHAR(20),
    qc_status VARCHAR(20),
    file_path_fcs TEXT,
    file_path_nta TEXT,
    file_path_tem TEXT
);
```

**Processing Results:**
```sql
CREATE TABLE fcs_results (
    result_id SERIAL PRIMARY KEY,
    sample_id VARCHAR(255) REFERENCES samples(sample_id),
    total_events INT,
    fsc_mean FLOAT,
    ssc_mean FLOAT,
    particle_size_median_nm FLOAT,
    cd9_positive_pct FLOAT,
    cd81_positive_pct FLOAT,
    qc_passed BOOLEAN,
    processed_at TIMESTAMP DEFAULT NOW()
);
```

**Benefits:**
- Fast UI queries
- User authentication
- Audit trails
- Real-time status updates

---

### 3.3 Visualization Dashboard 📊
**Status:** Plots exist, need interactive UI  
**Time:** 2 weeks  
**Owner:** Frontend team

**Requirements from Nov 18 meeting:**
1. **Upload Interface:**
   - Drag-and-drop file upload
   - Metadata popup (biological ID, treatment, concentration)
   - Batch upload support

2. **Processing View:**
   - Real-time progress bar
   - QC status indicators
   - Error messages

3. **Results View:**
   - Interactive plots (Plotly/D3.js)
   - Download plots as PNG/PDF
   - Export data as CSV
   - Compare multiple samples

4. **Decision Support:**
   - "Proceed to TEM?" recommendation
   - Color-coded warnings (red = reject, green = proceed)
   - Explanation tooltips

**Technology Stack:**
- Frontend: React + TypeScript
- Charts: Plotly.js or Recharts
- State: Redux/Zustand
- API: Axios for REST calls

---

## 🧬 Phase 4: Advanced Features (Month 3+)

### 4.1 Machine Learning Models 🤖
**Status:** Data ready, models not trained  
**Time:** 2-3 weeks  
**Owner:** ML engineer

**Models to train:**

1. **Quality Predictor:**
   - Input: FCS stats (event count, CV, scatter values)
   - Output: Good/Bad sample (binary classification)
   - Use: Auto-reject bad samples before manual review

2. **Marker Presence Classifier:**
   - Input: Size + intensity features
   - Output: CD9/CD81/CD63 present? (multi-label)
   - Use: Automated marker detection

3. **Size Distribution Predictor:**
   - Input: FCS scatter values
   - Output: Predicted NTA size distribution
   - Use: Estimate NTA results without running NTA

**Data preparation:**
```python
# Already have combined_features.parquet from integrate_data.py
import pandas as pd

data = pd.read_parquet('data/processed/combined_features.parquet')
X = data.drop(['sample_id', 'qc_status'], axis=1)
y = data['qc_status']

from sklearn.ensemble import RandomForestClassifier
model = RandomForestClassifier()
model.fit(X_train, y_train)
```

---

### 4.2 TEM Integration 🔬
**Status:** TEM data not yet processed  
**Time:** 2 weeks  
**Owner:** Backend team

**Tasks:**
1. **TEM Image Parser:**
   - Extract particle sizes from TEM images
   - Calculate size distributions
   - Detect membrane structures (viability check)

2. **TEM + FCS + NTA Fusion:**
   - Match samples across 3 instruments
   - Cross-validate size measurements
   - Generate comprehensive reports

3. **Decision Logic:**
   ```
   IF NTA shows particles at 80nm
   AND FCS shows CD9 at 80nm (THIS SCRIPT)
   AND TEM confirms membrane structure
   → Proceed to Western Blot
   ```

---

### 4.3 Western Blot Integration 🧪
**Status:** Data format not defined  
**Time:** 1 week  
**Owner:** Backend team

**Requirements:**
1. **Gel Image Analysis:**
   - Band detection
   - Intensity quantification
   - Molecular weight estimation

2. **Protein Quantification:**
   - Normalize to loading control
   - Calculate ratios (CD9/CD81/CD63)
   - Compare treated vs control

3. **Final Report:**
   - Combine all 4 instruments
   - Generate publication-ready figures
   - Export to PDF/Word

---

## 📋 Phase 5: Production Deployment (Month 4)

### 5.1 Infrastructure Setup 🏗️
**Status:** Running locally only  
**Time:** 2 weeks  
**Owner:** DevOps

**Required:**
1. **Cloud Hosting:**
   - AWS/Azure/GCP compute instances
   - S3/Blob storage for data
   - RDS/Aurora for database

2. **Docker Containers:**
   ```dockerfile
   FROM python:3.10-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0"]
   ```

3. **Kubernetes/Docker Compose:**
   - Backend API
   - Worker queue (Celery)
   - Redis cache
   - PostgreSQL database

---

### 5.2 Security & Authentication 🔒
**Status:** No auth implemented  
**Time:** 1 week  
**Owner:** Backend team

**Implement:**
1. **User Authentication:**
   - JWT tokens
   - Role-based access (researcher/admin)
   - OAuth2 (Google/Microsoft login)

2. **Data Security:**
   - Encrypt data at rest (S3 encryption)
   - Encrypt data in transit (HTTPS/TLS)
   - HIPAA compliance (if handling patient data)

3. **Audit Logging:**
   - Log all file uploads
   - Log all processing jobs
   - Log all data access

---

### 5.3 Monitoring & Alerting 📡
**Status:** Basic logging only  
**Time:** 3-4 days  
**Owner:** DevOps

**Setup:**
1. **Application Monitoring:**
   - Sentry for error tracking
   - New Relic/DataDog for performance
   - Custom dashboards (Grafana)

2. **Alerts:**
   - Processing failures → Slack/Email
   - High error rates → Page on-call engineer
   - Disk space warnings

3. **Metrics:**
   - Files processed per day
   - Average processing time
   - Error rates by type
   - User activity

---

## 🎯 Success Metrics

### Technical KPIs
- [ ] Test coverage > 80%
- [ ] API response time < 200ms (p95)
- [ ] Processing time < 2min for 100k events
- [ ] Uptime > 99.5%

### Scientific KPIs
- [ ] FCS vs NTA correlation R > 0.85
- [ ] Size accuracy error < 10nm (MAPE < 15%)
- [ ] Marker detection sensitivity > 90%
- [ ] False positive rate < 5%

### User Experience KPIs
- [ ] Upload to results < 5 minutes
- [ ] User satisfaction score > 4.5/5
- [ ] Support tickets < 10/month
- [ ] User adoption > 80% of target users

---

## 📅 Timeline Summary

| Phase | Duration | Status | Dependencies |
|-------|----------|--------|--------------|
| **Immediate** (Cleanup) | 2 hours | Ready | None |
| **Testing** | 1 week | Ready | Cleanup complete |
| **Config** | 3 days | Ready | Testing started |
| **CI/CD** | 1 week | Ready | Testing complete |
| **Validation** | 1 week | Needs data | None |
| **API Dev** | 2 weeks | Ready | Testing complete |
| **Database** | 1 week | Ready | API started |
| **Frontend** | 2 weeks | Ready | API complete |
| **ML Models** | 3 weeks | Needs data | Validation complete |
| **TEM Integration** | 2 weeks | Format TBD | Backend stable |
| **Deployment** | 2 weeks | Ready | All above complete |

**Total:** ~3-4 months to full production

---

## 🚦 Decision Points

### Week 2: After Testing
- Is code coverage adequate (>80%)?
- Are all critical paths tested?
- **GO/NO-GO:** Proceed to API development?

### Week 4: After Validation
- Does Mie sizing correlate with NTA (R>0.8)?
- Are marker detection rates acceptable?
- **GO/NO-GO:** Use Mie scatter or find alternative?

### Week 8: After Frontend POC
- Is UI/UX acceptable to researchers?
- Are workflows intuitive?
- **GO/NO-GO:** Proceed to full deployment?

---

## ❓ Open Questions

1. **Data Hosting:**
   - Where will data be stored long-term? (On-prem? Cloud?)
   - What's the data retention policy?
   - Backup strategy?

2. **Scalability:**
   - Expected users: 10? 100? 1000?
   - Files per day: 10? 100? 1000?
   - Data volume: GB? TB? PB?

3. **Commercial:**
   - Is this internal tool or product?
   - Pricing model if product?
   - Support SLAs?

4. **Regulatory:**
   - Need FDA approval? (If medical device)
   - HIPAA compliance required?
   - Data privacy regulations (GDPR)?

---

## 📞 Next Meeting Agenda

**Suggested topics:**
1. Review cleanup plan - approve deletion list
2. Prioritize Phase 1 tasks (testing vs config vs API?)
3. Assign owners to each task
4. Discuss validation strategy (sample collection)
5. Frontend requirements review
6. Infrastructure decisions (cloud provider, costs)
7. Timeline approval and resource allocation

---

**Status:** ✅ Ready to proceed - awaiting team decision on priorities!
