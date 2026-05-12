"""
Database Connection Management
===============================

Async SQLAlchemy engine and session management.

Provides:
- Async database engine
- Session factory
- Dependency injection for FastAPI
- Connection pool management

Author: CRMIT Backend Team
Date: November 21, 2025
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (  # type: ignore[import-not-found]
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool, QueuePool  # type: ignore[import-not-found]
from loguru import logger

from src.api.config import get_settings

settings = get_settings()

# ============================================================================
# Database Engine
# ============================================================================

# Global engine instance (created on first use)
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """
    Get or create the async database engine.
    
    Returns:
        AsyncEngine instance
    
    Configuration:
    - Pool size: Configurable via settings
    - Echo SQL: Controlled by settings.db_echo
    - Connection recycling: 3600 seconds (1 hour)
    
    Usage:
        from src.database.connection import get_engine
        engine = get_engine()
    """
    global _engine
    
    if _engine is None:
        logger.info("🔌 Creating database engine...")
        logger.info(f"   Database URL: {settings.database_url.split('@')[-1]}")  # Hide credentials
        
        # Use NullPool for async engines (required for asyncpg)
        poolclass = NullPool
        logger.info("   Pool: NullPool (async engine)")
        
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.db_echo,
            poolclass=poolclass,
            pool_pre_ping=True,  # Verify connections before using
        )
        
        logger.success("✅ Database engine created")
    
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the async session factory.
    
    Returns:
        Session factory for creating new sessions
    
    Usage:
        from src.database.connection import get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            # Use session
            pass
    """
    global _session_factory
    
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=False,  # Manual flushing for better control
            autocommit=False,  # Explicit transaction management
        )
        logger.info("✅ Session factory created")
    
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection for FastAPI routes.
    
    Yields:
        AsyncSession for database operations
    
    Usage in FastAPI:
        from fastapi import Depends
        from src.database.connection import get_session
        
        @app.get("/samples")
        async def list_samples(db: AsyncSession = Depends(get_session)):
            result = await db.execute(select(Sample))
            return result.scalars().all()
    
    Transaction Management:
    - Auto-commits on success
    - Auto-rollbacks on exception
    - Always closes session
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_connections():
    """
    Close all database connections.
    
    Call this during application shutdown.
    
    Usage:
        from src.database.connection import close_connections
        
        @app.on_event("shutdown")
        async def shutdown():
            await close_connections()
    """
    global _engine, _session_factory
    
    if _engine is not None:
        logger.info("🔌 Closing database connections...")
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.success("✅ Database connections closed")


# ============================================================================
# Database Initialization
# ============================================================================

def _sqlalchemy_type_to_sqlite(col) -> str:
    """Best-effort mapping of SQLAlchemy column types to SQLite type names."""
    from sqlalchemy import Integer, String, Float, Boolean, DateTime, JSON, Text
    py_type = col.type
    if isinstance(py_type, Integer):
        return "INTEGER"
    if isinstance(py_type, Float):
        return "REAL"
    if isinstance(py_type, Boolean):
        return "INTEGER"
    if isinstance(py_type, DateTime):
        return "TIMESTAMP"
    if isinstance(py_type, (JSON, Text)):
        return "TEXT"
    if isinstance(py_type, String):
        return "TEXT"
    return "TEXT"


def _migrate_missing_columns_sync(conn) -> None:
    """Add any model-defined columns that are missing from the existing
    sqlite database. Desktop installs ship with a sqlite file that may have
    been created by an older release whose schema is missing columns the
    current code expects (e.g. ``nta_results.viscosity``). Without this
    step, queries crash with ``OperationalError: no such column: ...``.

    Adds ALL missing columns as nullable. Never drops or alters existing
    columns — additive only, safe to run on every startup.
    """
    from sqlalchemy import inspect, text
    from src.database.models import Base

    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            # create_all just made this table — nothing to migrate.
            continue
        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
        for col in table.columns:
            if col.name in existing_cols:
                continue
            sqlite_type = _sqlalchemy_type_to_sqlite(col)
            null_clause = "" if col.nullable else " NOT NULL"
            default_clause = ""
            if col.server_default is not None:
                default_clause = f" DEFAULT {col.server_default.arg}"
            elif col.default is not None and getattr(col.default, "arg", None) is not None:
                default = col.default.arg
                if isinstance(default, str):
                    default_clause = f" DEFAULT '{default}'"
                elif isinstance(default, (int, float)):
                    default_clause = f" DEFAULT {default}"
            ddl = (
                f'ALTER TABLE "{table_name}" '
                f'ADD COLUMN "{col.name}" {sqlite_type}{null_clause}{default_clause}'
            )
            try:
                conn.execute(text(ddl))
                logger.info(f"📐 Added missing column: {table_name}.{col.name}")
            except Exception as exc:
                # NOT NULL on an existing-row table fails — drop NOT NULL and retry.
                if not col.nullable:
                    fallback_ddl = (
                        f'ALTER TABLE "{table_name}" '
                        f'ADD COLUMN "{col.name}" {sqlite_type}{default_clause}'
                    )
                    try:
                        conn.execute(text(fallback_ddl))
                        logger.warning(
                            f"📐 Added {table_name}.{col.name} as NULLABLE "
                            f"(model requires NOT NULL; existing rows would conflict)"
                        )
                        continue
                    except Exception:
                        pass
                logger.error(f"Schema migration: could not add {table_name}.{col.name}: {exc}")


async def init_database():
    """
    Initialize database with all tables.

    Creates any missing tables and ALTER TABLEs in any model columns that
    are missing on existing tables (additive only; never destructive).
    """
    from src.database.models import Base

    engine = get_engine()

    logger.info("📊 Initializing database schema...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_missing_columns_sync)

    logger.success("✅ Database schema initialized")


async def check_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection successful, False otherwise
    
    Usage:
        from src.database.connection import check_connection
        if await check_connection():
            print("Database is available")
    """
    try:
        factory = get_session_factory()
        async with factory() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        logger.success("✅ Database connection verified")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


# ============================================================================
# Context Manager for Manual Sessions
# ============================================================================

class DatabaseSession:
    """
    Context manager for manual session management.
    
    Use this when you need explicit transaction control outside FastAPI.
    
    Usage:
        from src.database.connection import DatabaseSession
        
        async with DatabaseSession() as db:
            sample = Sample(sample_id="TEST001", ...)
            db.add(sample)
            await db.flush()  # Optional: flush without commit
            # Commits automatically on context exit
    """
    
    def __init__(self):
        self.factory = get_session_factory()
        self.session: AsyncSession | None = None
    
    async def __aenter__(self) -> AsyncSession:
        self.session = self.factory()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):  # type: ignore[no-untyped-def]
        if exc_type is not None:
            await self.session.rollback()  # type: ignore[union-attr]
        else:
            await self.session.commit()  # type: ignore[union-attr]
        await self.session.close()  # type: ignore[union-attr]
