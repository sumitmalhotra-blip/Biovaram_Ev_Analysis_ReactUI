# CRMIT Exosome Analysis Platform - Deployment Guide

**Version:** 1.0  
**Date:** November 27, 2025  
**Status:** Production Ready

---

## 🎯 Quick Start (Development)

### Prerequisites
- Python 3.11 or 3.13
- PostgreSQL 18
- Git

### 1. Clone Repository
```powershell
git clone https://github.com/isumitmalhotra/CRMIT-Project-.git
cd CRMIT-Project-
```

### 2. Create Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment
Create `.env` file in project root:
```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/crmit_db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=True

# AWS S3 (Optional - for cloud storage)
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
AWS_S3_BUCKET=crmit-data-bucket
AWS_REGION=us-east-1

# Logging
LOG_LEVEL=INFO
```

### 5. Setup Database
```powershell
# Start PostgreSQL (if not running)
# Run migrations
alembic upgrade head
```

### 6. Start Backend API
```powershell
# Terminal 1: Backend API
cd "c:\CRM IT Project\EV (Exosome) Project"
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: **http://localhost:8000**  
API docs: **http://localhost:8000/docs**

### 7. Start Frontend (Streamlit)
```powershell
# Terminal 2: Streamlit UI
cd "c:\CRM IT Project\EV (Exosome) Project"
streamlit run apps/biovaram_streamlit/app.py
```

Frontend will be available at: **http://localhost:8501**

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                          │
│  Streamlit Web App (Port 8501)                              │
│  - File Upload + Metadata Forms                             │
│  - Real-time Visualizations                                 │
│  - Sample Database Browser                                  │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP REST API
                 ↓
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND API                               │
│  FastAPI Server (Port 8000)                                 │
│  - /api/v1/upload/fcs, /upload/nta                         │
│  - /api/v1/samples, /samples/{id}                          │
│  - /api/v1/jobs, /process                                  │
└────────────────┬────────────────────────────────────────────┘
                 │ SQLAlchemy ORM
                 ↓
┌─────────────────────────────────────────────────────────────┐
│                     DATABASE                                 │
│  PostgreSQL 18 (Port 5432)                                  │
│  - samples, fcs_results, nta_results                        │
│  - qc_reports, processing_jobs                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
CRMIT/
├── apps/
│   └── biovaram_streamlit/
│       ├── app.py                    # Main Streamlit UI
│       └── api_client.py             # Backend API wrapper
├── src/
│   ├── api/
│   │   ├── main.py                   # FastAPI app
│   │   ├── routers/                  # API endpoints
│   │   └── config.py                 # Settings
│   ├── database/
│   │   ├── models.py                 # SQLAlchemy models
│   │   ├── crud.py                   # Database operations
│   │   └── connection.py             # DB engine
│   ├── parsers/
│   │   ├── parse_fcs.py              # Flow cytometry parser
│   │   └── parse_nta.py              # NTA parser
│   ├── preprocessing/
│   │   ├── qc_engine.py              # Quality control
│   │   └── size_binning.py           # Particle size bins
│   └── visualization/
│       ├── fcs_plots.py              # Scatter plots
│       └── size_intensity_plots.py   # Size vs intensity
├── alembic/                          # Database migrations
├── config/                           # JSON configuration files
├── data/                             # Raw data storage
├── requirements.txt                  # Python dependencies
└── .env                              # Environment variables
```

---

## 🔧 Configuration Files

### `config/qc_thresholds.json`
Quality control thresholds for FCS/NTA data:
```json
{
  "fcs": {
    "min_event_count": 1000,
    "max_event_count": 1000000,
    "min_fsc_median": 100,
    "max_fsc_median": 100000
  },
  "nta": {
    "min_particle_count": 100,
    "min_mean_size_nm": 30,
    "max_mean_size_nm": 200
  }
}
```

### `config/parser_rules.json`
Filename parsing rules for metadata extraction:
```json
{
  "patterns": {
    "lot_number": "L\\d+",
    "fraction": "F\\d+",
    "treatment": "(CD81|CD9|CD63|ISO|Exo)",
    "concentration": "(\\d+\\.?\\d*)ug"
  }
}
```

---

## 🚀 Production Deployment

### Option 1: Docker (Recommended)

**Create `docker-compose.yml`:**
```yaml
version: '3.8'

services:
  db:
    image: postgres:18
    environment:
      POSTGRES_DB: crmit_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: .
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:${DB_PASSWORD}@db:5432/crmit_db

  frontend:
    build: .
    command: streamlit run apps/biovaram_streamlit/app.py --server.port 8501
    volumes:
      - .:/app
    ports:
      - "8501:8501"
    depends_on:
      - backend

volumes:
  postgres_data:
```

**Run:**
```powershell
docker-compose up -d
```

### Option 2: Windows Server

1. **Install Python 3.13**
2. **Install PostgreSQL 18**
3. **Clone repository to `C:\CRMIT\`**
4. **Create Windows Services:**

```powershell
# Backend Service
sc.exe create CRMITBackend binPath= "C:\CRMIT\venv\Scripts\python.exe -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000" start= auto

# Frontend Service
sc.exe create CRMITFrontend binPath= "C:\CRMIT\venv\Scripts\streamlit.exe run apps/biovaram_streamlit/app.py" start= auto
```

### Option 3: Linux Server (Ubuntu 22.04)

```bash
# Install dependencies
sudo apt update
sudo apt install python3.11 python3-pip postgresql-14

# Clone and setup
git clone https://github.com/isumitmalhotra/CRMIT-Project-.git /opt/crmit
cd /opt/crmit
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create systemd services
sudo nano /etc/systemd/system/crmit-backend.service
```

**crmit-backend.service:**
```ini
[Unit]
Description=CRMIT Backend API
After=network.target postgresql.service

[Service]
User=www-data
WorkingDirectory=/opt/crmit
Environment="PATH=/opt/crmit/venv/bin"
ExecStart=/opt/crmit/venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl enable crmit-backend
sudo systemctl start crmit-backend
```

---

## 🔐 Security Checklist

- [ ] Change default PostgreSQL password
- [ ] Set strong `SECRET_KEY` in `.env`
- [ ] Enable HTTPS with SSL certificates
- [ ] Restrict database access to localhost
- [ ] Configure firewall rules
- [ ] Enable CORS only for trusted domains
- [ ] Implement authentication (JWT tokens)
- [ ] Regular security updates

---

## 📊 Monitoring

### Health Checks
```bash
# Backend API
curl http://localhost:8000/health

# Database
psql -h localhost -U postgres -d crmit_db -c "SELECT COUNT(*) FROM samples;"
```

### Logs
```powershell
# View API logs
Get-Content logs/api.log -Wait -Tail 50

# View processing logs
Get-Content logs/processing_log_*.csv | Select-Object -Last 20
```

---

## 🐛 Troubleshooting

### Issue: "Connection refused" from Streamlit to API
**Solution:**
```powershell
# Check if backend is running
curl http://localhost:8000/health

# Restart backend
uvicorn src.api.main:app --reload
```

### Issue: Database migration errors
**Solution:**
```powershell
# Reset migrations (WARNING: Destroys data)
alembic downgrade base
alembic upgrade head
```

### Issue: Import errors in Streamlit
**Solution:**
```powershell
# Ensure api_client.py is in same directory
cd apps/biovaram_streamlit
python -c "from api_client import get_client; print('OK')"
```

---

## 📚 API Documentation

Once backend is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/upload/fcs` | Upload FCS file |
| POST | `/api/v1/upload/nta` | Upload NTA file |
| GET | `/api/v1/samples` | List all samples |
| GET | `/api/v1/samples/{id}` | Get sample details |
| DELETE | `/api/v1/samples/{id}` | Delete sample |
| POST | `/api/v1/process` | Trigger processing job |
| GET | `/api/v1/jobs/{id}` | Get job status |

---

## 📝 Testing

### Run Unit Tests
```powershell
pytest tests/ -v --cov=src --cov-report=html
```

### Manual Testing Workflow
1. Start backend and frontend
2. Upload FCS file with metadata
3. Verify sample appears in sidebar
4. Check database: `SELECT * FROM samples;`
5. View processing results
6. Download QC report

---

## 🔄 Updates and Maintenance

### Update Dependencies
```powershell
pip install --upgrade -r requirements.txt
```

### Database Backup
```powershell
pg_dump -h localhost -U postgres crmit_db > backup_$(Get-Date -Format 'yyyyMMdd').sql
```

### Database Restore
```powershell
psql -h localhost -U postgres crmit_db < backup_20251127.sql
```

---

## 📞 Support

**Documentation:** See `README.md`, `CRMIT-Development-Plan.md`  
**Issues:** GitHub Issues  
**Architecture:** See `CRMIT_ARCHITECTURE_ANALYSIS.md`

---

**Last Updated:** November 27, 2025  
**Deployed By:** CRMIT DevOps Team
