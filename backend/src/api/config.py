"""
API Configuration
=================

Centralized configuration for FastAPI application.
Loads from environment variables with sensible defaults.

Author: CRMIT Backend Team
Date: November 21, 2025
"""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings  # type: ignore[import-not-found]
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Environment Variables:
    - CRMIT_ENV: Environment (development, staging, production)
    - CRMIT_DB_URL: Database connection string
    - CRMIT_UPLOAD_DIR: File upload directory
    - CRMIT_PARQUET_DIR: Parquet storage directory
    - CRMIT_MAX_UPLOAD_SIZE: Max file size in MB
    - CRMIT_CORS_ORIGINS: Comma-separated allowed origins
    """
    
    # Application
    app_name: str = "CRMIT API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    
    # API
    api_prefix: str = "/api/v1"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    
    # Database - Use SQLite by default for local development
    database_url: str = "sqlite+aiosqlite:///./data/crmit.db"
    db_echo: bool = False  # Log SQL queries
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # File Storage
    upload_dir: Path = Path("data/uploads")
    parquet_dir: Path = Path("data/parquet")
    temp_dir: Path = Path("data/temp")
    max_upload_size_mb: int = 100
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8501"
    cors_credentials: bool = True
    cors_methods: List[str] = ["*"]
    cors_headers: List[str] = ["*"]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    # Security
    secret_key: str = "CHANGE_THIS_IN_PRODUCTION_USE_SECURE_RANDOM_KEY"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Processing
    max_workers: int = 4
    task_timeout_seconds: int = 300
    
    # Quality Control
    qc_min_events_fcs: int = 1000
    qc_temp_min_celsius: float = 15.0
    qc_temp_max_celsius: float = 25.0
    
    model_config = {
        "env_prefix": "CRMIT_",
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings instance
    
    Usage:
        from src.api.config import get_settings
        settings = get_settings()
        print(settings.database_url)
    """
    return Settings()


# Create directories on module import
settings = get_settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.parquet_dir.mkdir(parents=True, exist_ok=True)
settings.temp_dir.mkdir(parents=True, exist_ok=True)
