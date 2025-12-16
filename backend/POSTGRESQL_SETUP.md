# PostgreSQL Installation & Setup Guide

**Date:** November 21, 2025  
**Component:** CRMIT Backend Database  
**Author:** CRMIT Backend Team

---

## Table of Contents

1. [Overview](#overview)
2. [Installation Options](#installation-options)
3. [Step-by-Step Installation](#step-by-step-installation)
4. [Database Setup](#database-setup)
5. [Alembic Migrations](#alembic-migrations)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The CRMIT backend uses **PostgreSQL 15+** as the primary database for storing:
- Sample metadata and file paths
- FCS analysis results (flow cytometry)
- NTA analysis results (nanoparticle tracking)
- Processing job queue and status
- Quality control reports
- User accounts and audit logs

**Requirements:**
- PostgreSQL 15 or higher
- 2GB+ available disk space
- Administrator access (for installation)

---

## Installation Options

### Option A: Direct Download (Recommended for Windows)

**Pros:** Full PostgreSQL installation with pgAdmin GUI, official support  
**Cons:** Larger installation size (~250MB)

Download: https://www.postgresql.org/download/windows/

### Option B: Chocolatey (Quick Install)

**Pros:** Simple command-line installation, easy updates  
**Cons:** Requires Chocolatey package manager

```powershell
choco install postgresql
```

### Option C: Docker (Development/Testing)

**Pros:** Isolated environment, no system installation, easy cleanup  
**Cons:** Requires Docker Desktop, uses more resources

```powershell
docker run -d `
  --name crmit-postgres `
  -e POSTGRES_PASSWORD=crmit123 `
  -e POSTGRES_USER=crmit `
  -e POSTGRES_DB=crmit_db `
  -p 5432:5432 `
  -v crmit-pgdata:/var/lib/postgresql/data `
  postgres:15
```

---

## Step-by-Step Installation

### Method 1: Direct Download (Recommended)

#### Step 1: Download Installer

1. Visit: https://www.postgresql.org/download/windows/
2. Click **"Download the installer"**
3. Select PostgreSQL 15 or higher (64-bit)
4. Save file (e.g., `postgresql-15.x-windows-x64.exe`)

#### Step 2: Run Installer

1. **Run installer as Administrator**
2. **Installation Directory:** Default (`C:\Program Files\PostgreSQL\15`)
3. **Select Components:** ✅ PostgreSQL Server, ✅ pgAdmin 4, ✅ Command Line Tools
4. **Data Directory:** Default (`C:\Program Files\PostgreSQL\15\data`)
5. **Password:** Enter password for `postgres` superuser (e.g., `postgres123`)
   - ⚠️ **IMPORTANT:** Remember this password!
6. **Port:** Default (5432)
7. **Locale:** Default (C)
8. Click **Next** through remaining screens
9. Wait for installation to complete

#### Step 3: Add PostgreSQL to PATH

1. Open **System Properties** (Windows Key + Pause/Break)
2. Click **Advanced system settings**
3. Click **Environment Variables**
4. Under **System variables**, select `Path` → Click **Edit**
5. Click **New** → Add: `C:\Program Files\PostgreSQL\15\bin`
6. Click **OK** on all dialogs
7. **Restart PowerShell** to apply changes

#### Step 4: Verify Installation

```powershell
# Check PostgreSQL version
psql --version

# Expected output:
# psql (PostgreSQL) 15.x
```

---

### Method 2: Chocolatey Install

#### Prerequisites

Install Chocolatey if not already installed:
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

#### Install PostgreSQL

```powershell
# Install PostgreSQL
choco install postgresql -y

# Refresh environment variables
refreshenv

# Verify
psql --version
```

---

## Database Setup

### Step 1: Create Database and User

```powershell
# Connect to PostgreSQL as superuser
psql -U postgres

# Or if using Docker:
docker exec -it crmit-postgres psql -U postgres
```

In the PostgreSQL shell:

```sql
-- Create database
CREATE DATABASE crmit_db;

-- Create user
CREATE USER crmit WITH PASSWORD 'crmit123';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE crmit_db TO crmit;

-- Exit
\q
```

### Step 2: Configure Environment

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and update database connection:

```ini
# Database Configuration
CRMIT_DB_URL=postgresql+asyncpg://crmit:crmit123@localhost:5432/crmit_db

# For Docker:
# CRMIT_DB_URL=postgresql+asyncpg://crmit:crmit123@localhost:5432/crmit_db

# Security (CHANGE THIS!)
CRMIT_SECRET_KEY=your-secret-key-here-change-me
```

**Generate a secure secret key:**

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 3: Install Python Dependencies

```powershell
# Navigate to project root
cd "c:\CRM IT Project\EV (Exosome) Project"

# Install database packages
pip install sqlalchemy asyncpg psycopg2-binary alembic
```

---

## Alembic Migrations

Alembic manages database schema changes systematically.

### Step 1: Initialize Alembic

```powershell
# Initialize Alembic
alembic init alembic
```

This creates:
```
alembic/
  ├── env.py              # Alembic environment configuration
  ├── script.py.mako      # Migration template
  └── versions/           # Migration scripts
alembic.ini               # Alembic configuration
```

### Step 2: Configure Alembic

**Edit `alembic.ini`:**

```ini
# Line 63: Comment out hardcoded URL
# sqlalchemy.url = driver://user:pass@localhost/dbname

# We'll use environment variable instead
```

**Edit `alembic/env.py`:**

Add imports at top (after existing imports):

```python
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import Base
from src.api.config import get_settings
```

Replace `target_metadata = None` with:

```python
# Line ~20
target_metadata = Base.metadata
```

In `run_migrations_online()` function, replace `config.get_main_option("sqlalchemy.url")` with:

```python
# Line ~70
def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    settings = get_settings()
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = str(settings.database_url)
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    # ... rest of function
```

### Step 3: Create Initial Migration

```powershell
# Generate migration from models
alembic revision --autogenerate -m "Initial schema"

# Output:
# Generating c:\...\alembic\versions\abc123_initial_schema.py ... done
```

**Review the migration file:**

Open `alembic/versions/abc123_initial_schema.py` and verify it creates all tables:
- samples
- fcs_results
- nta_results
- processing_jobs
- qc_reports
- users
- audit_log
- tem_results

### Step 4: Apply Migration

```powershell
# Apply migrations to database
alembic upgrade head

# Output:
# INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
# INFO  [alembic.runtime.migration] Will assume transactional DDL.
# INFO  [alembic.runtime.migration] Running upgrade  -> abc123, Initial schema
```

### Step 5: Verify Tables

```powershell
# Connect to database
psql -U crmit -d crmit_db

# List tables
\dt

# Expected output:
#            List of relations
#  Schema |       Name       | Type  | Owner
# --------+------------------+-------+-------
#  public | alembic_version  | table | crmit
#  public | audit_log        | table | crmit
#  public | fcs_results      | table | crmit
#  public | nta_results      | table | crmit
#  public | processing_jobs  | table | crmit
#  public | qc_reports       | table | crmit
#  public | samples          | table | crmit
#  public | tem_results      | table | crmit
#  public | users            | table | crmit

# Describe samples table
\d samples

# Exit
\q
```

---

## Verification

### Test 1: Database Connection

```powershell
python -c "from src.database.connection import check_connection; import asyncio; asyncio.run(check_connection())"
```

**Expected output:**
```
✅ Database connection successful
```

### Test 2: FastAPI Server

```powershell
# Start server
python src/api/main.py
```

**Expected output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
✅ Database connection successful
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Open browser: http://localhost:8000/docs

Verify endpoints:
- ✅ `GET /health` → 200 OK
- ✅ `GET /api/v1/status` → Shows database info
- ✅ `GET /api/v1/samples` → Empty list (no samples yet)

### Test 3: Upload File

Use Swagger UI (http://localhost:8000/docs):

1. Navigate to **POST /api/v1/upload/fcs**
2. Click **Try it out**
3. Upload a test FCS file
4. Fill in metadata (treatment, concentration)
5. Click **Execute**
6. Verify response includes `job_id` and database record created

Check database:
```powershell
psql -U crmit -d crmit_db -c "SELECT sample_id, treatment, processing_status FROM samples;"
```

---

## Troubleshooting

### Issue: `psql: command not found`

**Cause:** PostgreSQL bin directory not in PATH

**Solution:**
1. Verify installation location: `C:\Program Files\PostgreSQL\15\bin`
2. Add to PATH (see Step 3 of installation)
3. Restart PowerShell

### Issue: `FATAL: password authentication failed`

**Cause:** Incorrect password or user not created

**Solution:**
```powershell
# Reset password
psql -U postgres
```
```sql
ALTER USER crmit WITH PASSWORD 'crmit123';
```

### Issue: `could not connect to server: Connection refused`

**Cause:** PostgreSQL service not running

**Solution (Windows):**
```powershell
# Check service status
Get-Service postgresql*

# Start service
Start-Service postgresql-x64-15
```

**Solution (Docker):**
```powershell
# Check container status
docker ps -a | Select-String crmit-postgres

# Start container
docker start crmit-postgres
```

### Issue: `sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable)`

**Cause:** Migrations not applied

**Solution:**
```powershell
# Apply migrations
alembic upgrade head
```

### Issue: Alembic can't import models

**Cause:** Python path not configured in `alembic/env.py`

**Solution:** Verify `sys.path.insert(0, ...)` in Step 2 of Alembic setup

### Issue: `ImportError: cannot import name 'asyncpg'`

**Cause:** Missing Python package

**Solution:**
```powershell
pip install asyncpg
```

---

## Next Steps

After successful setup:

1. ✅ **Test Upload Endpoint:** Upload sample FCS/NTA files
2. ✅ **Verify Database:** Check records in `samples` and `processing_jobs` tables
3. ✅ **Implement Background Jobs:** Set up Celery/RQ for async processing
4. ✅ **Run Integration Tests:** `pytest tests/test_integration.py`
5. ✅ **Production Deployment:** Configure PostgreSQL for production (connection pooling, backups, monitoring)

---

## Production Considerations

### Security

- ✅ Change default passwords
- ✅ Use environment variables (never commit `.env`)
- ✅ Enable SSL/TLS for database connections
- ✅ Restrict database access (firewall rules)

### Performance

- ✅ Configure connection pooling (already done in `connection.py`)
- ✅ Create indexes on frequently queried columns (already done in models)
- ✅ Monitor query performance (`pg_stat_statements`)
- ✅ Regular `VACUUM` and `ANALYZE`

### Backups

```powershell
# Backup database
pg_dump -U crmit crmit_db > backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql

# Restore database
psql -U crmit crmit_db < backup_20251121_120000.sql
```

### Monitoring

- ✅ Enable PostgreSQL logging
- ✅ Monitor disk space
- ✅ Set up alerts for failed connections
- ✅ Use pgAdmin or similar for GUI monitoring

---

## Summary

**Installation:**
- ✅ PostgreSQL 15+ installed
- ✅ Added to system PATH
- ✅ Service running

**Database:**
- ✅ Database `crmit_db` created
- ✅ User `crmit` with privileges
- ✅ Connection string configured in `.env`

**Migrations:**
- ✅ Alembic initialized
- ✅ Initial migration created and applied
- ✅ All 8 tables created

**Verification:**
- ✅ Connection test passed
- ✅ FastAPI server starts
- ✅ Endpoints accessible

**Ready for:**
- 🚀 File uploads
- 🚀 Data processing
- 🚀 Integration testing
- 🚀 Production deployment

---

**Support:** For issues, check logs in `logs/` directory or contact backend team.
