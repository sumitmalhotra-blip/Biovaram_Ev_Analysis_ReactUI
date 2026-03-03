"""
Database Backup & Restore Router
==================================

Endpoints for database backup, restore, and management.
Desktop-mode feature for data protection and portability.

Endpoints:
- GET  /db/info              - Database file info (size, location, table counts)
- POST /db/backup            - Create a backup of the SQLite database
- POST /db/restore           - Restore database from a backup file
- GET  /db/backups           - List available backups
- DELETE /db/backup/{name}   - Delete a specific backup

Author: CRMIT Backend Team
Date: March 3, 2026
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from loguru import logger

from src.api.config import get_settings
from src.database.connection import get_engine

router = APIRouter()
settings = get_settings()


# ============================================================================
# Response Models
# ============================================================================

class DatabaseInfo(BaseModel):
    """Database information."""
    path: str
    size_bytes: int
    size_mb: float
    exists: bool
    table_counts: dict = {}
    last_modified: Optional[str] = None
    backup_count: int = 0


class BackupInfo(BaseModel):
    """Backup file information."""
    name: str
    path: str
    size_bytes: int
    size_mb: float
    created_at: str


class BackupResponse(BaseModel):
    """Response after creating a backup."""
    success: bool
    message: str
    backup: Optional[BackupInfo] = None


class RestoreResponse(BaseModel):
    """Response after restoring from backup."""
    success: bool
    message: str


# ============================================================================
# Helpers
# ============================================================================

def _get_db_path() -> Path:
    """Get the SQLite database file path from the connection URL."""
    db_url = os.environ.get("CRMIT_DATABASE_URL", settings.database_url)
    # Extract file path from sqlite+aiosqlite:///path
    if ":///" in db_url:
        path_part = db_url.split("///", 1)[1]
        return Path(path_part).resolve()
    return Path("data/crmit.db").resolve()


def _get_backup_dir() -> Path:
    """Get the backup directory, creating it if needed."""
    db_path = _get_db_path()
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/db/info", response_model=DatabaseInfo)
async def database_info():
    """
    Get database file info: size, location, table row counts.
    """
    db_path = _get_db_path()
    backup_dir = _get_backup_dir()
    
    info = DatabaseInfo(
        path=str(db_path),
        size_bytes=0,
        size_mb=0.0,
        exists=db_path.exists(),
    )
    
    if db_path.exists():
        stat = db_path.stat()
        info.size_bytes = stat.st_size
        info.size_mb = round(stat.st_size / (1024 * 1024), 2)
        info.last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
    
    # Count backups
    if backup_dir.exists():
        info.backup_count = len(list(backup_dir.glob("*.db")))
    
    # Get table counts via a raw query
    try:
        import aiosqlite
        async with aiosqlite.connect(str(db_path)) as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'alembic_%'"
            )
            tables = await cursor.fetchall()
            
            counts = {}
            for (table_name,) in tables:
                try:
                    cursor = await conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
                    row = await cursor.fetchone()
                    counts[table_name] = row[0] if row else 0
                except Exception:
                    counts[table_name] = -1
            info.table_counts = counts
    except Exception as e:
        logger.warning(f"Could not read table counts: {e}")
    
    return info


@router.post("/db/backup", response_model=BackupResponse)
async def create_backup():
    """
    Create a timestamped backup of the SQLite database.
    Backup is saved to the `backups/` directory next to the database file.
    """
    db_path = _get_db_path()
    
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database file not found")
    
    backup_dir = _get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"crmit_backup_{timestamp}.db"
    backup_path = backup_dir / backup_name
    
    try:
        # Use SQLite's backup API for a consistent copy (handles WAL mode)
        import aiosqlite
        import sqlite3
        
        # Direct file copy is fine for SQLite in WAL mode when no writes are active
        # But using SQLite backup API is safer
        source_conn = sqlite3.connect(str(db_path))
        dest_conn = sqlite3.connect(str(backup_path))
        
        source_conn.backup(dest_conn)
        
        source_conn.close()
        dest_conn.close()
        
        stat = backup_path.stat()
        backup_info = BackupInfo(
            name=backup_name,
            path=str(backup_path),
            size_bytes=stat.st_size,
            size_mb=round(stat.st_size / (1024 * 1024), 2),
            created_at=datetime.now().isoformat(),
        )
        
        logger.info(f"Database backup created: {backup_name} ({backup_info.size_mb} MB)")
        
        return BackupResponse(
            success=True,
            message=f"Backup created: {backup_name}",
            backup=backup_info,
        )
    
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        # Clean up partial backup
        if backup_path.exists():
            backup_path.unlink()
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")


@router.get("/db/backups", response_model=list[BackupInfo])
async def list_backups():
    """
    List all available database backups, newest first.
    """
    backup_dir = _get_backup_dir()
    backups = []
    
    for f in sorted(backup_dir.glob("*.db"), reverse=True):
        stat = f.stat()
        backups.append(BackupInfo(
            name=f.name,
            path=str(f),
            size_bytes=stat.st_size,
            size_mb=round(stat.st_size / (1024 * 1024), 2),
            created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
        ))
    
    return backups


@router.get("/db/backup/{name}")
async def download_backup(name: str):
    """
    Download a specific backup file.
    """
    # Sanitize filename to prevent path traversal
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail="Invalid backup name")
    
    backup_dir = _get_backup_dir()
    backup_path = backup_dir / name
    
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail=f"Backup not found: {name}")
    
    return FileResponse(
        path=str(backup_path),
        filename=name,
        media_type="application/octet-stream",
    )


@router.post("/db/restore", response_model=RestoreResponse)
async def restore_backup(backup_name: Optional[str] = None, file: Optional[UploadFile] = File(None)):
    """
    Restore database from a named backup or an uploaded file.
    
    - If `backup_name` is provided, restores from the backups directory
    - If a file is uploaded, restores from the uploaded .db file
    
    **WARNING:** This replaces the current database. A pre-restore backup is
    automatically created first.
    """
    db_path = _get_db_path()
    
    # Determine source
    if backup_name:
        if "/" in backup_name or "\\" in backup_name or ".." in backup_name:
            raise HTTPException(status_code=400, detail="Invalid backup name")
        
        backup_dir = _get_backup_dir()
        source_path = backup_dir / backup_name
        
        if not source_path.exists():
            raise HTTPException(status_code=404, detail=f"Backup not found: {backup_name}")
    elif file:
        if not file.filename or not file.filename.endswith(".db"):
            raise HTTPException(status_code=400, detail="File must be a .db SQLite database")
        
        # Save uploaded file to temp
        temp_path = _get_backup_dir() / f"_upload_temp_{file.filename}"
        try:
            content = await file.read()
            with open(temp_path, "wb") as f:
                f.write(content)
            source_path = temp_path
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")
    else:
        raise HTTPException(status_code=400, detail="Provide either backup_name or upload a .db file")
    
    try:
        # Create a pre-restore backup first (safety net)
        if db_path.exists():
            pre_restore_name = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            pre_restore_path = _get_backup_dir() / pre_restore_name
            
            import sqlite3
            source_conn = sqlite3.connect(str(db_path))
            dest_conn = sqlite3.connect(str(pre_restore_path))
            source_conn.backup(dest_conn)
            source_conn.close()
            dest_conn.close()
            
            logger.info(f"Pre-restore backup: {pre_restore_name}")
        
        # Restore: copy source over current DB
        import sqlite3
        source_conn = sqlite3.connect(str(source_path))
        dest_conn = sqlite3.connect(str(db_path))
        
        source_conn.backup(dest_conn)
        
        source_conn.close()
        dest_conn.close()
        
        logger.info(f"Database restored from: {source_path.name}")
        
        return RestoreResponse(
            success=True,
            message=f"Database restored successfully. A pre-restore backup was saved as '{pre_restore_name}'." if db_path.exists() else "Database restored successfully.",
        )
    
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")
    
    finally:
        # Clean up temp upload file
        if file and 'temp_path' in locals() and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


@router.delete("/db/backup/{name}")
async def delete_backup(name: str):
    """
    Delete a specific backup file.
    """
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail="Invalid backup name")
    
    backup_dir = _get_backup_dir()
    backup_path = backup_dir / name
    
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail=f"Backup not found: {name}")
    
    try:
        backup_path.unlink()
        logger.info(f"Backup deleted: {name}")
        return {"success": True, "message": f"Backup '{name}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {e}")
