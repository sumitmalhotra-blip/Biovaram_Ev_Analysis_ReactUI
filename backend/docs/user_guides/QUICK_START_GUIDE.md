# 🚀 CRMIT EV Project - Quick Start Guide
**For new developers joining the project**

---

## 📋 Project Overview (30 seconds)

**What:** Backend system for multi-modal exosome analysis (NanoFACS + NTA + TEM + Western Blot)  
**Goal:** Automate exosome characterization pipeline with ML-ready data outputs  
**Status:** Core backend complete, frontend integration in progress

**Key Tech:** Python 3.10, Pandas, NumPy, PyArrow (Parquet), Matplotlib, Loguru

---

## ⚡ Quick Setup (5 minutes)

```powershell
# 1. Clone repository
git clone https://github.com/isumitmalhotra/CRMIT-Project-.git
cd "c:\CRM IT Project\EV (Exosome) Project"

# 2. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Test installation
python -c "from src.parsers import FCSParser; print('✅ Setup complete!')"
```

---

## 📚 Essential Reading (30 minutes)

**Read in this order:**

1. **README.md** (5 min) - Project overview
2. **CRMIT_ARCHITECTURE_ANALYSIS.md** (10 min) - 7-layer architecture
3. **MASTER_BACKEND_DOCUMENTATION.md** (10 min) - File inventory
4. **NEXT_STEPS_ROADMAP.md** (5 min) - What we're building next

**Optional but useful:**
- **DOCUMENTATION_PROGRESS.md** - What's been documented
- **DATA_FORMATS_FOR_ML_GUIDE.md** - Data structures
- **MIE_QUICK_REFERENCE.md** - Mie scatter physics

---

## 🏃 Run Your First Pipeline (10 minutes)

### 1. Process FCS Files
```powershell
python scripts/batch_process_fcs.py `
  --input-dir "nanoFACS/10000 exo and cd81" `
  --output-dir "data/parquet/nanofacs" `
  --add-mie-sizes
```

**What it does:** Parses FCS files → Calculates statistics → Adds Mie scatter sizes → Saves Parquet

### 2. Generate Plots
```powershell
python scripts/generate_fcs_plots.py `
  --parquet-dir "data/parquet/nanofacs/events" `
  --output-dir "figures/fcs"
```

**What it does:** Creates scatter plots with size vs intensity

### 3. Integrate Multi-Modal Data
```powershell
python scripts/integrate_data.py
```

**What it does:** FCS + NTA → Combined features (ML-ready Parquet)

---

## 📁 Key Directories

```
├── scripts/          # Production scripts (18 files)
│   ├── batch_process_fcs.py      # Main FCS processor
│   ├── batch_process_nta.py      # Main NTA processor
│   ├── integrate_data.py         # Multi-modal fusion
│   └── validate_fcs_vs_nta.py    # Cross-validation
│
├── src/              # Core modules (17 files)
│   ├── parsers/      # FCS/NTA file parsers
│   ├── preprocessing/# QC, normalization, binning
│   ├── visualization/# Plotting functions
│   ├── physics/      # Mie scatter calculations
│   └── fusion/       # Multi-modal integration
│
├── data/             # Data files
│   ├── raw/          # Original FCS/NTA files
│   ├── parquet/      # Processed Parquet files
│   └── processed/    # ML-ready datasets
│
├── figures/          # Generated plots
├── logs/             # Processing logs
├── config/           # Configuration files
└── docs/             # Additional documentation
```

---

## 🔧 Common Tasks

### Add New FCS File Processing
1. Place FCS files in `data/raw/fcs/`
2. Run: `python scripts/batch_process_fcs.py`
3. Check output: `data/parquet/nanofacs/`

### Generate Plots for Sample
```python
from src.visualization.fcs_plots import FCSPlotter

plotter = FCSPlotter()
plotter.plot_scatter(
    data=your_data,
    x='particle_size_nm',
    y='B531-H',
    output_file='figures/my_plot.png'
)
```

### Validate Mie Sizing
```powershell
python scripts/validate_fcs_vs_nta.py `
  --fcs data/processed/fcs `
  --nta data/parquet/nta `
  --output figures/validation.png
```

---

## 🐛 Troubleshooting

### Import Error: "Module not found"
```powershell
# Ensure virtual environment is activated
.\.venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

### File Not Found
```powershell
# Check path is absolute
$fullPath = Resolve-Path "relative/path"

# Or use Path object
from pathlib import Path
file_path = Path("data/raw/fcs/sample.fcs").resolve()
```

### Mie Calculation Slow
```python
# Use smart filtering to remove outliers
from scripts.reprocess_with_smart_filtering import main
main()  # Uses 99.9th percentile filter
```

---

## 📊 Understanding the Code

### Architecture (7 Layers)
1. **Input Layer:** FCS/NTA file parsing
2. **Preprocessing:** QC, normalization, size binning
3. **Physics:** Mie scatter size calculation
4. **Fusion:** Multi-instrument integration
5. **ML Features:** Feature extraction
6. **Visualization:** Plot generation
7. **Output:** Parquet files, plots, reports

### Key Concepts

**FCS Files:**
- Flow cytometry data (forward/side scatter + fluorescence)
- Events = individual particles measured
- Channels: FSC-A, SSC-A, B531-H (blue), Y595-H (yellow), etc.

**NTA Files:**
- Nanoparticle Tracking Analysis
- Tracks Brownian motion → calculates size
- Outputs: D10, D50, D90 (10th, 50th, 90th percentiles)

**Mie Scattering:**
- Physics model: scatter intensity → particle size
- Requires calibration vs NTA
- Implemented in `src/physics/mie_scatter.py`

**Size Bins:**
- Small: 40-80nm (typical exosomes)
- Medium: 80-100nm
- Large: 100-120nm
- XL: >120nm (microvesicles)

---

## 🧪 Testing

```powershell
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_parser.py -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html
```

---

## 🆘 Getting Help

### Code Questions
1. Check inline comments (95% of code documented)
2. Read function docstrings
3. Review MASTER_BACKEND_DOCUMENTATION.md

### Scientific Questions
1. Check MIE_QUICK_REFERENCE.md
2. Review MEETING_QUESTIONS.md (important decisions)
3. Read NanoFACS-Histogram-Plots.md

### Architecture Questions
1. CRMIT_ARCHITECTURE_ANALYSIS.md
2. DATA_FORMATS_FOR_ML_GUIDE.md
3. UNIFIED_DATA_FORMAT_STRATEGY.md

### Next Steps Questions
1. NEXT_STEPS_ROADMAP.md (4-month plan)
2. COMPLETION_SUMMARY.md (current status)
3. TASK_TRACKER.md (complete history)

---

## ✅ Checklist for First Week

- [ ] Setup complete (Python, dependencies)
- [ ] Read README and architecture docs
- [ ] Run batch_process_fcs.py successfully
- [ ] Generate plots with generate_fcs_plots.py
- [ ] Understand Mie scatter basics
- [ ] Review code comments in 2-3 key files
- [ ] Run tests (pytest)
- [ ] Create first pull request

---

## 🎯 Next Phase Priorities

**Week 1-2:**
1. Execute cleanup (remove test files)
2. Build unit test suite (80% coverage target)
3. Extract configs to YAML files

**Week 3-4:**
4. Validate Mie sizing with real samples
5. Optimize performance (10x speedup)
6. Start API development

**See NEXT_STEPS_ROADMAP.md for complete plan**

---

## 🚀 You're Ready!

**Commands to remember:**
```powershell
# Activate environment
.\.venv\Scripts\Activate.ps1

# Process FCS files
python scripts/batch_process_fcs.py --help

# Generate plots
python scripts/generate_fcs_plots.py --help

# Run tests
python -m pytest tests/
```

**Docs to bookmark:**
- MASTER_BACKEND_DOCUMENTATION.md
- NEXT_STEPS_ROADMAP.md
- CRMIT_ARCHITECTURE_ANALYSIS.md

**Happy coding! 🎉**
