# CRMIT Backend Quick Start Guide

**Last Updated:** November 21, 2025  
**Estimated Time:** 30-45 minutes

---

## 🚀 Quick Start (5 Steps)

### Step 1: Install Python Dependencies (5 minutes)

```powershell
# Option A: Automated installation
python install_backend_deps.py

# Option B: Manual installation
pip install fastapi uvicorn sqlalchemy asyncpg psycopg2-binary alembic pydantic-settings loguru pandas numpy pyarrow pytest pytest-asyncio
```

### Step 2: Install PostgreSQL (10-15 minutes)

**Choose one option:**

**Option A: Chocolatey (Fastest)**
```powershell
choco install postgresql -y
refreshenv
```

**Option B: Direct Download**
- Download: https://www.postgresql.org/download/windows/
- Run installer
- Remember superuser password!

**Option C: Docker (Recommended for Testing)**
```powershell
docker run -d --name crmit-postgres -e POSTGRES_PASSWORD=crmit123 -e POSTGRES_USER=crmit -e POSTGRES_DB=crmit_db -p 5432:5432 postgres:15
```

**Verify:**
```powershell
psql --version
# Expected: psql (PostgreSQL) 15.x
```

### Step 3: Create Database (2 minutes)

```powershell
# Connect to PostgreSQL
psql -U postgres

# Or for Docker:
# docker exec -it crmit-postgres psql -U postgres
```

In PostgreSQL shell:
```sql
CREATE DATABASE crmit_db;
CREATE USER crmit WITH PASSWORD 'crmit123';
GRANT ALL PRIVILEGES ON DATABASE crmit_db TO crmit;
\q
```

### Step 4: Configure Environment (2 minutes)

```powershell
# Copy environment template
Copy-Item .env.example .env

# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy output and paste into .env as CRMIT_SECRET_KEY
```

**Edit `.env`:**
```ini
CRMIT_DB_URL=postgresql+asyncpg://crmit:crmit123@localhost:5432/crmit_db
CRMIT_SECRET_KEY=<paste-generated-key-here>
```

### Step 5: Initialize Database (5 minutes)

```powershell
# Initialize Alembic
alembic init alembic
```

**Edit `alembic/env.py`:**

Add after imports (line ~10):
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import Base
from src.api.config import get_settings
```

Replace `target_metadata = None` with (line ~20):
```python
target_metadata = Base.metadata
```

In `run_migrations_online()`, replace config line (line ~70):
```python
def run_migrations_online() -> None:
    settings = get_settings()
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = str(settings.database_url)
    # ... rest unchanged
```

**Create and apply migration:**
```powershell
# Generate migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

**Verify:**
```powershell
psql -U crmit -d crmit_db -c "\dt"
# Should show 8 tables: samples, fcs_results, nta_results, etc.
```

---

## ✅ Test Your Setup (5 minutes)

### Test 1: Database Connection

```powershell
python -c "from src.database.connection import check_connection; import asyncio; asyncio.run(check_connection())"
```

**Expected:** ✅ Database connection successful

### Test 2: Start API Server

```powershell
python src/api/main.py
```

**Expected:**
```
INFO:     Started server process [12345]
✅ Database connection successful
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Test 3: API Endpoints

Open browser: http://localhost:8000/docs

**Try these endpoints:**
1. **GET /health** → Click "Try it out" → Execute → 200 OK
2. **GET /api/v1/status** → Execute → Shows database info
3. **GET /api/v1/samples** → Execute → Empty list `{"total": 0, "samples": []}`

### Test 4: Upload File

In Swagger UI:
1. Go to **POST /api/v1/upload/fcs**
2. Click "Try it out"
3. Upload a test FCS file (e.g., from `nanoFACS/10000 exo and cd81/`)
4. Fill in:
   - treatment: "CD81"
   - concentration_ug: 1.0
   - operator: "Test User"
5. Click "Execute"
6. Verify response includes `job_id`

**Check database:**
```powershell
psql -U crmit -d crmit_db -c "SELECT sample_id, treatment, processing_status FROM samples;"
```

---

## 📋 Troubleshooting

### Issue: `psql: command not found`

**Solution:**
```powershell
# Add to PATH
$env:Path += ";C:\Program Files\PostgreSQL\15\bin"

# Make permanent (System Properties > Environment Variables)
```

### Issue: `Connection refused` to PostgreSQL

**Solution:**
```powershell
# Windows: Check service
Get-Service postgresql*
Start-Service postgresql-x64-15

# Docker: Check container
docker ps -a | Select-String crmit
docker start crmit-postgres
```

### Issue: `Import "uvicorn" could not be resolved`

**Solution:**
```powershell
pip install uvicorn
```

### Issue: Alembic can't find models

**Solution:** Verify `sys.path.insert()` in `alembic/env.py` (see Step 5)

### Issue: Database tables not created

**Solution:**
```powershell
# Check current version
alembic current

# Apply migrations
alembic upgrade head
```

---

## 🎯 Next Steps

After successful setup:

### Immediate

1. **Upload Sample Files**
   - Upload FCS files from `nanoFACS/` directory
   - Upload NTA files from `NTA/` directory
   - Verify in database

2. **Run Integration Tests**
   ```powershell
   pytest tests/test_integration.py -v
   ```

3. **Explore API**
   - Try all endpoints in Swagger UI
   - Test filtering: `/api/v1/samples?treatment=CD81`
   - Test job status: `/api/v1/jobs/{job_id}`

### Short-Term (Today)

4. **Implement Background Jobs**
   - Install Redis: `choco install redis-64`
   - Install RQ: `pip install rq`
   - Create worker script
   - Move parsing to background

5. **Connect Frontend**
   - Start React/Streamlit app
   - Test file upload from UI
   - Display sample list

### Medium-Term (This Week)

6. **Add Authentication**
   - Implement JWT tokens
   - User registration/login
   - Protect endpoints

7. **Production Deployment**
   - Configure Nginx
   - Enable HTTPS
   - Set up monitoring

---

## 📚 Documentation

**Primary Docs:**
- [BACKEND_IMPLEMENTATION_SUMMARY.md](./BACKEND_IMPLEMENTATION_SUMMARY.md) - Complete overview
- [POSTGRESQL_SETUP.md](./POSTGRESQL_SETUP.md) - Detailed database setup
- [API Docs](http://localhost:8000/docs) - Interactive API documentation

**Configuration:**
- `.env.example` - Environment variables template
- `alembic.ini` - Alembic configuration
- `src/api/config.py` - Application settings

**Code:**
- `src/api/` - FastAPI application
- `src/database/` - Database models and operations
- `tests/` - Integration tests

---

## 📊 Current Status

✅ **Completed:**
- FastAPI REST API (13 endpoints)
- PostgreSQL database schema (8 tables)
- CRUD operations (25 functions)
- File upload handling
- Job status tracking
- Integration tests (13 tests)

⏳ **Next Priority:**
- Background job queue
- Actual file parsing integration
- Frontend connection

🔮 **Future:**
- Authentication
- Advanced analytics
- Production deployment

---

## 💡 Tips

### Development Workflow

```powershell
# Terminal 1: API Server
python src/api/main.py

# Terminal 2: Database
psql -U crmit -d crmit_db

# Terminal 3: Testing
pytest tests/ -v
```

### Database Management

```powershell
# View logs
psql -U crmit -d crmit_db -c "SELECT * FROM processing_jobs ORDER BY created_at DESC LIMIT 10;"

# Clear data (development only!)
psql -U crmit -d crmit_db -c "TRUNCATE samples CASCADE;"

# Backup
pg_dump -U crmit crmit_db > backup.sql

# Restore
psql -U crmit crmit_db < backup.sql
```

### API Testing

```powershell
# List samples
curl http://localhost:8000/api/v1/samples

# Get sample
curl http://localhost:8000/api/v1/samples/P5_F10_CD81

# Check job
curl http://localhost:8000/api/v1/jobs/{job_id}
```

---

## 🎉 Success Checklist

- [ ] Python dependencies installed
- [ ] PostgreSQL installed and running
- [ ] Database and user created
- [ ] `.env` configured with database URL
- [ ] Alembic initialized
- [ ] Migrations applied
- [ ] 8 tables created in database
- [ ] API server starts successfully
- [ ] `/docs` accessible in browser
- [ ] Health check returns 200 OK
- [ ] Sample file uploaded
- [ ] Database record created
- [ ] Integration tests pass

**If all checked:** 🎉 **YOU'RE READY TO GO!**

---

## 📞 Need Help?

**Check Documentation:**
1. This guide (you are here)
2. `BACKEND_IMPLEMENTATION_SUMMARY.md` - Full overview
3. `POSTGRESQL_SETUP.md` - Database details
4. API docs at http://localhost:8000/docs

**Common Issues:**
- Database connection → Check PostgreSQL service running
- Import errors → Reinstall dependencies: `pip install -r requirements.txt`
- Migration errors → Check `alembic/env.py` configuration
- API errors → Check logs in console output

**Still Stuck?**
- Review error messages carefully
- Check `logs/` directory
- Verify all steps completed
- Try restarting services

---

**Last Updated:** November 21, 2025  
**Version:** 1.0  
**Status:** Ready for Production Setup
