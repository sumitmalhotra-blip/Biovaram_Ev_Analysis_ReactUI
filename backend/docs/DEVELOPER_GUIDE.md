# Developer Onboarding Guide

**For New Developers Joining the BioVaram EV Analysis Platform**

*Last Updated: January 2026*

---

## 👋 Welcome!

This guide will help you get up to speed with the codebase. Read it completely before writing any code.

---

## 📚 Table of Contents

1. [Understanding the Domain](#1-understanding-the-domain)
2. [Technology Stack](#2-technology-stack)
3. [Setting Up Your Environment](#3-setting-up-your-environment)
4. [Codebase Walkthrough](#4-codebase-walkthrough)
5. [Key Files You'll Work With](#5-key-files-youll-work-with)
6. [Common Tasks](#6-common-tasks)
7. [Coding Standards](#7-coding-standards)
8. [Debugging Tips](#8-debugging-tips)

---

## 1. Understanding the Domain

### What Are Extracellular Vesicles (EVs)?

EVs are tiny particles (30-500 nanometers) released by cells. They carry proteins, RNA, and other molecules. They're being researched for:
- Drug delivery
- Disease diagnosis
- Cell-to-cell communication

### What Does This Platform Do?

We analyze EVs using two laboratory techniques:

| Technique | What It Measures | File Format | Events/File |
|-----------|------------------|-------------|-------------|
| **NanoFACS** (Flow Cytometry) | Light scatter from individual particles | `.fcs` | 100K - 1M |
| **NTA** (ZetaView) | Particle movement in liquid | `.txt` | Size bins |

### Key Terms You'll See

| Term | Meaning |
|------|---------|
| **FSC** | Forward Scatter - light scattered forward (correlates with size) |
| **SSC** | Side Scatter - light scattered sideways (correlates with internal complexity) |
| **Mie Theory** | Physics equations to calculate particle size from light scatter |
| **D10/D50/D90** | Particle diameters at 10th, 50th, 90th percentile |
| **Event** | One particle detection in flow cytometry |
| **Channel** | A detector measuring one specific wavelength/angle |

---

## 2. Technology Stack

### Frontend

| Technology | Purpose | Docs |
|------------|---------|------|
| **Next.js 14** | React framework | https://nextjs.org/docs |
| **TypeScript** | Type-safe JavaScript | https://www.typescriptlang.org/ |
| **Tailwind CSS** | Styling | https://tailwindcss.com/ |
| **Shadcn/UI** | Component library | https://ui.shadcn.com/ |
| **Recharts** | Charts | https://recharts.org/ |
| **NextAuth.js** | Authentication | https://next-auth.js.org/ |

### Backend

| Technology | Purpose | Docs |
|------------|---------|------|
| **FastAPI** | REST API framework | https://fastapi.tiangolo.com/ |
| **Python 3.10+** | Backend language | https://docs.python.org/ |
| **SQLAlchemy** | Database ORM | https://docs.sqlalchemy.org/ |
| **Pandas** | Data manipulation | https://pandas.pydata.org/ |
| **NumPy** | Numerical computing | https://numpy.org/ |
| **miepython** | Mie scattering calculations | https://miepython.readthedocs.io/ |
| **flowio** | FCS file parsing | https://github.com/whitews/FlowIO |

---

## 3. Setting Up Your Environment

### Required Tools

```powershell
# Check versions
node --version    # Should be 18+
python --version  # Should be 3.10+
git --version     # Any recent version
```

### Installation

```powershell
# Clone
git clone https://github.com/sumitmalhotra-blip/Biovaram_Ev_Analysis_ReactUI.git
cd Biovaram_Ev_Analysis_ReactUI

# Frontend
npm install

# Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### IDE Setup (VS Code)

Install these extensions:
- Python
- Pylance
- ESLint
- Prettier
- Tailwind CSS IntelliSense

### Running Locally

**Terminal 1 - Backend:**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python run_api.py
# API runs at http://localhost:8000
```

**Terminal 2 - Frontend:**
```powershell
npm run dev
# App runs at http://localhost:3000
```

---

## 4. Codebase Walkthrough

### Frontend Structure

```
app/                          # Next.js App Router
├── page.tsx                  # Main dashboard (entry point)
├── layout.tsx                # Root layout with providers
├── globals.css               # Global styles
├── (auth)/                   # Auth pages (grouped route)
│   ├── login/page.tsx
│   └── signup/page.tsx
└── api/                      # API route handlers
    └── research/route.ts     # AI chat endpoint

components/                    # React components
├── flow-cytometry/           # FCS analysis UI
│   ├── fcs-tab.tsx          # Main FCS tab
│   ├── file-upload.tsx      # Upload component
│   └── analysis-results.tsx # Results display
├── nta/                      # NTA analysis UI
├── cross-compare/            # Comparison tools
├── charts/                   # Visualization components
│   ├── scatter-chart.tsx
│   ├── histogram-chart.tsx
│   └── ...
├── ui/                       # Shadcn base components
│   ├── button.tsx
│   ├── card.tsx
│   └── ...
├── sidebar.tsx               # Navigation sidebar
├── header.tsx                # Top header
└── tab-navigation.tsx        # Tab switcher

lib/                          # Utilities
├── api-client.ts            # Backend API wrapper
├── auth.ts                  # NextAuth config
├── export-utils.ts          # PDF/Excel export
├── store.ts                 # Zustand state management
└── utils.ts                 # Helper functions

hooks/                        # Custom React hooks
├── use-api.ts               # API call hook
├── use-toast.ts             # Toast notifications
└── use-mobile.ts            # Mobile detection
```

### Backend Structure

```
backend/
├── run_api.py               # Entry point - starts server
├── requirements.txt         # Python dependencies
│
├── src/                     # Main source code
│   ├── api/                 # FastAPI application
│   │   ├── main.py         # App initialization, CORS
│   │   ├── config.py       # Settings/environment
│   │   └── routers/        # Endpoint modules
│   │       ├── upload.py   # File upload endpoints
│   │       ├── samples.py  # Sample CRUD
│   │       ├── results.py  # Analysis results
│   │       └── auth.py     # Authentication
│   │
│   ├── parsers/             # File parsing
│   │   ├── base_parser.py  # Abstract base class
│   │   ├── fcs_parser.py   # FCS file parser (IMPORTANT)
│   │   └── nta_parser.py   # NTA file parser
│   │
│   ├── physics/             # Scientific calculations
│   │   ├── mie_scatter.py  # Mie theory (CORE PHYSICS)
│   │   ├── size_distribution.py  # Size calculations
│   │   ├── bead_calibration.py   # Calibration curves
│   │   └── statistics_utils.py   # Stats helpers
│   │
│   ├── visualization/       # Plot generation
│   │   ├── fcs_plots.py    # FCS visualizations
│   │   ├── nta_plots.py    # NTA visualizations
│   │   └── cross_comparison.py
│   │
│   ├── database/            # Database layer
│   │   ├── models.py       # SQLAlchemy models
│   │   └── connection.py   # DB connection
│   │
│   └── fcs_calibration.py  # SSC-to-size calibration
│
├── scripts/                 # Standalone scripts
│   ├── compare_single_vs_multi_solution.py  # Mie comparison
│   ├── batch_process_fcs.py                  # Batch processing
│   └── ...
│
├── data/                    # Data storage
│   ├── uploads/            # Raw uploaded files
│   ├── parquet/            # Processed data
│   └── temp/               # Temporary files
│
├── figures/                 # Generated plots
│
├── nanoFACS/               # Sample FCS data
├── NTA/                    # Sample NTA data
└── Literature/             # Reference papers
```

---

## 5. Key Files You'll Work With

### Frontend Priority Files

| File | What It Does | When You'll Edit It |
|------|--------------|---------------------|
| `components/flow-cytometry/fcs-tab.tsx` | Main FCS analysis UI | Adding FCS features |
| `components/nta/nta-tab.tsx` | Main NTA analysis UI | Adding NTA features |
| `lib/api-client.ts` | API calls to backend | Adding new API calls |
| `components/charts/*.tsx` | Chart components | Modifying visualizations |

### Backend Priority Files

| File | What It Does | When You'll Edit It |
|------|--------------|---------------------|
| `src/api/routers/upload.py` | File upload handling | Changing upload logic |
| `src/parsers/fcs_parser.py` | FCS file parsing | Fixing parsing issues |
| `src/physics/mie_scatter.py` | Size calculations | Modifying Mie theory |
| `src/fcs_calibration.py` | SSC-to-size calibration | Calibration changes |

---

## 6. Common Tasks

### Task: Add a New API Endpoint

1. Create route in `backend/src/api/routers/`
2. Register in `backend/src/api/main.py`
3. Add frontend call in `lib/api-client.ts`
4. Test with Swagger: http://localhost:8000/docs

**Example Backend Endpoint:**
```python
# backend/src/api/routers/my_feature.py
from fastapi import APIRouter

router = APIRouter(prefix="/my-feature", tags=["My Feature"])

@router.get("/")
async def get_something():
    return {"message": "Hello"}
```

**Example Frontend Call:**
```typescript
// lib/api-client.ts
export async function getMyFeature() {
  const response = await fetch(`${API_BASE}/my-feature/`);
  return response.json();
}
```

### Task: Add a New Chart Component

1. Create in `components/charts/my-chart.tsx`
2. Import in the tab that needs it
3. Pass data as props

**Example:**
```tsx
// components/charts/my-chart.tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';

interface MyChartProps {
  data: Array<{ name: string; value: number }>;
}

export function MyChart({ data }: MyChartProps) {
  return (
    <BarChart width={500} height={300} data={data}>
      <XAxis dataKey="name" />
      <YAxis />
      <Tooltip />
      <Bar dataKey="value" fill="#8884d8" />
    </BarChart>
  );
}
```

### Task: Parse a New Field from FCS Files

1. Open `backend/src/parsers/fcs_parser.py`
2. Find the `parse()` method
3. Add extraction logic
4. Test with a sample file

---

## 7. Coding Standards

### Python

```python
# Use type hints
def calculate_size(ssc_values: np.ndarray) -> np.ndarray:
    """
    Calculate particle sizes from SSC values.
    
    Args:
        ssc_values: Array of side scatter values
        
    Returns:
        Array of diameters in nanometers
    """
    return calibration.ssc_to_size(ssc_values)

# Use f-strings
print(f"Processed {len(events)} events")

# Use pathlib for paths
from pathlib import Path
file_path = Path("data") / "uploads" / filename
```

### TypeScript

```typescript
// Use explicit types
interface SampleData {
  id: string;
  name: string;
  eventCount: number;
}

// Use async/await
async function fetchSample(id: string): Promise<SampleData> {
  const response = await fetch(`/api/samples/${id}`);
  return response.json();
}

// Destructure props
function SampleCard({ sample }: { sample: SampleData }) {
  return <div>{sample.name}</div>;
}
```

### Git Commits

```
feat: Add multi-solution Mie sizing
fix: Correct NTA percentile calculation
docs: Update API documentation
refactor: Simplify FCS parser logic
test: Add unit tests for calibration
```

---

## 8. Debugging Tips

### Backend Issues

```powershell
# Check API is running
curl http://localhost:8000/health

# View API logs in terminal where run_api.py is running

# Test endpoints with Swagger UI
# Open http://localhost:8000/docs in browser

# Debug Python script
python -m pdb scripts/my_script.py
```

### Frontend Issues

```powershell
# Check for TypeScript errors
npm run build

# View browser console (F12)
# Check Network tab for API calls

# Debug React components
# Use React DevTools browser extension
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `CORS error` | Backend not running | Start backend with `python run_api.py` |
| `Module not found` | Missing package | Run `pip install -r requirements.txt` |
| `FCS parsing failed` | Invalid file format | Check file is valid FCS 2.0/3.0 |
| `NaN in size calculations` | Invalid SSC values | Filter for SSC > 0 before calculation |

---

## 🎯 Your First Week

### Day 1-2: Setup & Explore
- [ ] Clone repository and install dependencies
- [ ] Run both frontend and backend
- [ ] Upload a sample FCS file and see analysis
- [ ] Read through this guide completely

### Day 3-4: Understand Code
- [ ] Read `fcs_parser.py` and understand FCS structure
- [ ] Read `mie_scatter.py` and understand Mie theory basics
- [ ] Read one frontend component end-to-end

### Day 5: First Task
- [ ] Pick a small task from TASK_TRACKER.md
- [ ] Create a feature branch
- [ ] Make the change
- [ ] Test thoroughly
- [ ] Create a PR

---

## 📞 Getting Help

1. **Check existing docs** in `backend/docs/`
2. **Read the Literature** PDFs in `backend/Literature/`
3. **Ask the team** on Slack/Teams
4. **Check meeting notes** in `backend/docs/meeting_notes/`

---

*Good luck! Welcome to the team!* 🚀
