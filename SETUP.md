# 🚀 First-Time Setup Guide

Complete step-by-step instructions for setting up the BioVaram EV Analysis Platform on a new machine.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Windows Setup](#windows-setup)
3. [macOS/Linux Setup](#macoslinux-setup)
4. [Database Setup](#database-setup)
5. [Starting the Application](#starting-the-application)
6. [Verifying the Setup](#verifying-the-setup)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Version | Download Link |
|----------|---------|---------------|
| **Git** | Latest | https://git-scm.com/downloads |
| **Node.js** | 18.0+ | https://nodejs.org/ (LTS recommended) |
| **Python** | 3.10 - 3.12 | https://www.python.org/downloads/ |
| **PostgreSQL** | 15+ (optional) | https://www.postgresql.org/download/ |

### Recommended Tools

- **VS Code** - Code editor with excellent TypeScript/Python support
- **TablePlus** or **pgAdmin** - Database GUI (optional)
- **Postman** - API testing (optional)

---

## Windows Setup

### Step 1: Clone the Repository

```powershell
# Open PowerShell as Administrator
cd C:\Users\YourUsername\Projects  # or wherever you want to put it
git clone https://github.com/sumitmalhotra-blip/Biovaram_Ev_Analysis_ReactUI.git
cd Biovaram_Ev_Analysis_ReactUI
```

### Step 2: Install Frontend Dependencies

```powershell
# Install Node.js packages using npm
npm install

# Alternative: Use pnpm (faster)
npm install -g pnpm
pnpm install
```

### Step 3: Setup Python Backend

```powershell
# Navigate to backend folder
cd backend

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
# Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# Upgrade pip
python -m pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt

# Return to root folder
cd ..
```

### Step 4: Configure Environment Variables

**Frontend Configuration** - Create `.env.local` in root folder:

```powershell
# Create the file
New-Item -Path ".env.local" -ItemType File

# Add content (use notepad or VS Code)
```

Add this content to `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_SECRET=your-development-secret-key-change-in-production
NEXTAUTH_URL=http://localhost:3000
```

**Backend Configuration** - Create `.env` in `backend/` folder:

```powershell
cd backend
New-Item -Path ".env" -ItemType File
```

Add this content to `backend/.env`:
```env
# Database (SQLite for development - no setup needed)
CRMIT_DB_URL=sqlite+aiosqlite:///./data/crmit.db

# For PostgreSQL (production):
# CRMIT_DB_URL=postgresql+asyncpg://username:password@localhost:5432/crmit_db

# Environment
CRMIT_ENVIRONMENT=development
CRMIT_LOG_LEVEL=DEBUG

# CORS Origins (add your frontend URL)
CRMIT_CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

---

## macOS/Linux Setup

### Step 1: Clone the Repository

```bash
cd ~/Projects  # or wherever you want
git clone https://github.com/sumitmalhotra-blip/Biovaram_Ev_Analysis_ReactUI.git
cd Biovaram_Ev_Analysis_ReactUI
```

### Step 2: Install Frontend Dependencies

```bash
npm install
# or
pnpm install
```

### Step 3: Setup Python Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

cd ..
```

### Step 4: Environment Variables

Same as Windows, but use `touch` to create files:

```bash
touch .env.local
touch backend/.env
```

---

## Database Setup

### Option A: SQLite (Recommended for Development)

**No setup required!** The application automatically creates a SQLite database at `backend/data/crmit.db` on first run.

### Option B: PostgreSQL (Production)

1. **Install PostgreSQL** (version 15+ recommended)

2. **Create Database**:
```sql
CREATE DATABASE crmit_db;
CREATE USER crmit_user WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE crmit_db TO crmit_user;
```

3. **Update `backend/.env`**:
```env
CRMIT_DB_URL=postgresql+asyncpg://crmit_user:your_password@localhost:5432/crmit_db
```

4. **Run Migrations**:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
alembic upgrade head
```

---

## Starting the Application

### Method 1: Quick Start (Windows - Recommended)

```powershell
# From project root
.\start.ps1
```

This script starts both frontend and backend in separate windows.

### Method 2: Manual Start (Two Terminals)

**Terminal 1 - Backend API:**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python run_api.py
```

**Terminal 2 - Frontend:**
```powershell
npm run dev
```

### Method 3: macOS/Linux

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python run_api.py
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

---

## Verifying the Setup

### 1. Check Backend Health

Open in browser: **http://localhost:8000/health**

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": "connected"
}
```

### 2. Check API Documentation

Open in browser: **http://localhost:8000/docs**

You should see the Swagger UI with all API endpoints.

### 3. Check Frontend

Open in browser: **http://localhost:3000**

You should see the BioVaram EV Analysis Platform login page.

### 4. Test File Upload

1. Login or create an account
2. Go to "Flow Cytometry" tab
3. Upload a sample FCS file
4. Verify you see the analysis results

---

## Troubleshooting

### Common Issues

#### 1. "npm install" fails

```powershell
# Clear npm cache
npm cache clean --force

# Delete node_modules and try again
Remove-Item -Recurse -Force node_modules
npm install
```

#### 2. Python package installation fails

```powershell
# Make sure you're in the virtual environment
.\venv\Scripts\Activate.ps1

# Upgrade pip first
python -m pip install --upgrade pip setuptools wheel

# Then try again
pip install -r requirements.txt
```

#### 3. "miepython" import error

The miepython package requires specific API usage. If you see errors related to `single_sphere`:

```python
# Old API (won't work with miepython 3.0+):
miepython.single_sphere(m, x, 0)

# New API (correct):
miepython.single_sphere(m, x, 0, True)  # 4th param is e_field
```

This is already fixed in the codebase.

#### 4. Port already in use

```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual number)
taskkill /PID <PID> /F
```

#### 5. CORS errors in browser

Make sure your `backend/.env` includes the frontend URL:
```env
CRMIT_CORS_ORIGINS=["http://localhost:3000"]
```

#### 6. Database connection errors

For SQLite, ensure the `backend/data/` folder exists:
```powershell
mkdir backend\data -Force
```

For PostgreSQL, verify the connection string and that the database server is running.

---

## Development Workflow

### Making Changes

1. **Backend changes** auto-reload if `run_api.py` is running with `--reload`
2. **Frontend changes** auto-refresh in the browser (Fast Refresh)

### Running Linters

```powershell
# Frontend (ESLint + TypeScript check)
npm run lint
npm run type-check

# Backend (if configured)
cd backend
pip install ruff
ruff check src/
```

### Useful Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start frontend in development mode |
| `npm run build` | Build frontend for production |
| `python run_api.py` | Start backend API |
| `alembic upgrade head` | Apply database migrations |
| `alembic revision --autogenerate -m "message"` | Create new migration |

---

## Getting Help

- Check `TASK_TRACKER.md` for current development status
- Read `backend/docs/DEVELOPER_GUIDE.md` for coding guidelines
- Check `backend/docs/API_REFERENCE.md` for API documentation

---

*Last Updated: January 26, 2026*
