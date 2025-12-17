"""
Database Models
===============

SQLAlchemy ORM models for CRMIT platform.

Tables:
1. samples          - Master sample registry
2. fcs_results      - Flow cytometry analysis results
3. nta_results      - Nanoparticle tracking analysis results
4. tem_results      - Transmission electron microscopy results (future)
5. processing_jobs  - Async processing job queue
6. qc_reports       - Quality control reports
7. users            - User accounts (future)
8. audit_log        - Activity audit trail

Author: CRMIT Backend Team
Date: November 21, 2025
"""

from datetime import datetime  # noqa: F401
from typing import Optional  # noqa: F401
from sqlalchemy import (  # type: ignore[import-not-found]
    Column, Integer, String, Float, Boolean, DateTime, Text, 
    ForeignKey, Enum, JSON, Index  # noqa: F401
)
from sqlalchemy.orm import declarative_base, relationship  # type: ignore[import-not-found]
from sqlalchemy.sql import func  # type: ignore[import-not-found]
import enum

Base = declarative_base()


# ============================================================================
# Enums
# ============================================================================

class ProcessingStatus(str, enum.Enum):
    """Processing job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QCStatus(str, enum.Enum):
    """Quality control status."""
    PENDING = "pending"  # Initial state before QC runs
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class InstrumentType(str, enum.Enum):
    """Instrument type."""
    FCS = "fcs"
    NTA = "nta"
    TEM = "tem"
    WESTERN_BLOT = "western_blot"


# ============================================================================
# Sample Models
# ============================================================================

class Sample(Base):
    """
    Master sample registry - links all measurements from same biological sample.
    
    This is the central table that connects data from multiple instruments.
    Each biological sample (e.g., "P5_F10_CD81") gets one row, with links
    to FCS, NTA, and TEM measurements via relationships.
    """
    __tablename__ = "samples"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Sample Identification
    sample_id = Column(String(255), unique=True, nullable=False, index=True)
    biological_sample_id = Column(String(100), nullable=True, index=True)  # e.g., "P5_F10"
    
    # Experimental Metadata
    treatment = Column(String(50), nullable=True, index=True)  # e.g., "CD81", "ISO", "Control"
    concentration_ug = Column(Float, nullable=True)  # Antibody concentration (µg)
    preparation_method = Column(String(50), nullable=True)  # e.g., "SEC", "Centrifugation"
    passage_number = Column(Integer, nullable=True)  # Cell passage number
    fraction_number = Column(Integer, nullable=True)  # Fraction number (F10, F16, etc.)
    
    # Timestamps
    experiment_date = Column(DateTime, nullable=True)
    upload_timestamp = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Processing Status
    processing_status = Column(String(20), nullable=False, default="pending", index=True)
    qc_status = Column(String(20), nullable=True, index=True)  # Overall QC status
    
    # File Paths (relative to storage root)
    file_path_fcs = Column(Text, nullable=True)
    file_path_nta = Column(Text, nullable=True)
    file_path_tem = Column(Text, nullable=True)
    
    # Metadata
    operator = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    fcs_results = relationship("FCSResult", back_populates="sample", cascade="all, delete-orphan")
    nta_results = relationship("NTAResult", back_populates="sample", cascade="all, delete-orphan")
    qc_reports = relationship("QCReport", back_populates="sample", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="sample", cascade="all, delete-orphan")
    experimental_conditions = relationship("ExperimentalConditions", back_populates="sample", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_sample_treatment_date', 'treatment', 'experiment_date'),
        Index('idx_sample_status', 'processing_status', 'qc_status'),
    )
    
    def __repr__(self) -> str:
        return f"<Sample(id={self.id}, sample_id='{self.sample_id}', treatment='{self.treatment}')>"


# ============================================================================
# FCS Results
# ============================================================================

class FCSResult(Base):
    """
    Flow cytometry analysis results.
    
    Stores summary statistics from FCS file processing.
    Raw event data is stored in Parquet files for performance.
    """
    __tablename__ = "fcs_results"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=False, index=True)
    
    # Event Statistics
    total_events = Column(Integer, nullable=False)
    
    # Scatter Statistics (Forward Scatter, Side Scatter)
    fsc_mean = Column(Float, nullable=True)
    fsc_median = Column(Float, nullable=True)
    fsc_std = Column(Float, nullable=True)
    fsc_cv = Column(Float, nullable=True)  # Coefficient of variation
    
    ssc_mean = Column(Float, nullable=True)
    ssc_median = Column(Float, nullable=True)
    ssc_std = Column(Float, nullable=True)
    ssc_cv = Column(Float, nullable=True)
    
    # Particle Sizing (Mie scatter-based)
    particle_size_mean_nm = Column(Float, nullable=True)
    particle_size_median_nm = Column(Float, nullable=True)
    particle_size_std_nm = Column(Float, nullable=True)
    particle_size_d10_nm = Column(Float, nullable=True)
    particle_size_d90_nm = Column(Float, nullable=True)
    
    # Marker Expression (% positive events)
    cd9_positive_pct = Column(Float, nullable=True)
    cd81_positive_pct = Column(Float, nullable=True)
    cd63_positive_pct = Column(Float, nullable=True)
    
    # Fluorescence Statistics (JSON for flexibility)
    fluorescence_stats = Column(JSON, nullable=True)  # {"B530-A": {"mean": 1234, ...}, ...}
    
    # Quality Metrics
    debris_pct = Column(Float, nullable=True)  # % events in debris gate
    doublets_pct = Column(Float, nullable=True)  # % doublet events
    
    # File Reference (nullable - may not have parquet file initially)
    parquet_file_path = Column(Text, nullable=True)
    
    # Timestamps
    processed_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationship
    sample = relationship("Sample", back_populates="fcs_results")
    
    def __repr__(self) -> str:
        return f"<FCSResult(id={self.id}, sample_id={self.sample_id}, events={self.total_events})>"


# ============================================================================
# NTA Results
# ============================================================================

class NTAResult(Base):
    """
    Nanoparticle Tracking Analysis (ZetaView) results.
    
    Stores size distribution and concentration measurements.
    """
    __tablename__ = "nta_results"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=False, index=True)
    
    # Size Distribution
    mean_size_nm = Column(Float, nullable=False)
    median_size_nm = Column(Float, nullable=False)  # D50
    mode_size_nm = Column(Float, nullable=True)
    d10_nm = Column(Float, nullable=True)  # 10th percentile
    d50_nm = Column(Float, nullable=True)  # Median
    d90_nm = Column(Float, nullable=True)  # 90th percentile
    std_dev_nm = Column(Float, nullable=True)
    
    # Concentration
    concentration_particles_ml = Column(Float, nullable=True)
    concentration_particles_ml_error = Column(Float, nullable=True)
    
    # Size Bins (percentage in each bin)
    bin_30_50nm_pct = Column(Float, nullable=True)
    bin_50_80nm_pct = Column(Float, nullable=True)
    bin_80_100nm_pct = Column(Float, nullable=True)
    bin_100_120nm_pct = Column(Float, nullable=True)
    bin_120_150nm_pct = Column(Float, nullable=True)
    bin_150_200nm_pct = Column(Float, nullable=True)
    
    # Measurement Conditions
    temperature_celsius = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)
    conductivity = Column(Float, nullable=True)
    
    # File Reference (nullable - may not have parquet file initially)
    parquet_file_path = Column(Text, nullable=True)
    
    # Timestamps
    measurement_date = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationship
    sample = relationship("Sample", back_populates="nta_results")
    
    def __repr__(self) -> str:
        return f"<NTAResult(id={self.id}, sample_id={self.sample_id}, mean_size={self.mean_size_nm:.1f}nm)>"


# ============================================================================
# Processing Jobs
# ============================================================================

class ProcessingJob(Base):
    """
    Background processing job tracker.
    
    Tracks async processing tasks (file parsing, batch analysis, etc.).
    Used for job queue management and status updates.
    """
    __tablename__ = "processing_jobs"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)  # UUID
    
    # Foreign Key (optional - not all jobs are sample-specific)
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=True, index=True)
    
    # Job Details
    job_type = Column(String(50), nullable=False, index=True)  # "fcs_parse", "nta_parse", "batch_process"
    status = Column(String(20), nullable=False, default="pending", index=True)
    
    # Progress Tracking
    progress_percent = Column(Integer, nullable=False, default=0)
    current_step = Column(String(255), nullable=True)
    
    # Results
    result_data = Column(JSON, nullable=True)  # Arbitrary result data
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    sample = relationship("Sample", back_populates="processing_jobs")
    
    # Indexes
    __table_args__ = (
        Index('idx_job_status_created', 'status', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<ProcessingJob(id={self.id}, job_id='{self.job_id}', status='{self.status}')>"


# ============================================================================
# QC Reports
# ============================================================================

class QCReport(Base):
    """
    Quality control reports.
    
    Stores QC check results for each sample/instrument combination.
    """
    __tablename__ = "qc_reports"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=False, index=True)
    
    # QC Details
    instrument_type = Column(String(20), nullable=False, index=True)  # "fcs", "nta", "tem"
    qc_status = Column(String(20), nullable=False, index=True)  # "pass", "warn", "fail"
    
    # QC Checks (JSON for flexibility)
    checks_performed = Column(JSON, nullable=False)  # List of check names
    checks_passed = Column(JSON, nullable=False)  # List of passed checks
    checks_failed = Column(JSON, nullable=False)  # List of failed checks
    checks_warnings = Column(JSON, nullable=True)  # List of warnings
    
    # Details
    qc_flags = Column(Text, nullable=True)  # Semicolon-separated flags
    failure_reason = Column(Text, nullable=True)
    
    # Timestamps
    checked_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationship
    sample = relationship("Sample", back_populates="qc_reports")
    
    # Indexes
    __table_args__ = (
        Index('idx_qc_instrument_status', 'instrument_type', 'qc_status'),
    )
    
    def __repr__(self) -> str:
        return f"<QCReport(id={self.id}, sample_id={self.sample_id}, status='{self.qc_status}')>"


# ============================================================================
# Experimental Conditions (TASK-009)
# ============================================================================

class ExperimentalConditions(Base):
    """
    Experimental conditions captured during sample processing.
    
    TASK-009: Store experimental metadata for reproducibility and AI analysis.
    
    Client Quote (Jagan, Nov 27, 2025):
    "Capture important experimental metadata for your analysis.
    This information helps ensure reproducibility and proper interpretation of results."
    """
    __tablename__ = "experimental_conditions"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key - links to sample
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=False, index=True)
    
    # Measurement Conditions
    temperature_celsius = Column(Float, nullable=True)  # e.g., 22.5
    ph = Column(Float, nullable=True)  # e.g., 7.4
    
    # Buffer and Media
    substrate_buffer = Column(String(100), nullable=True)  # e.g., "PBS", "HEPES", "Custom"
    custom_buffer = Column(String(255), nullable=True)  # For custom buffer specification
    
    # Sample Preparation
    sample_volume_ul = Column(Float, nullable=True)  # Sample volume in microliters
    dilution_factor = Column(Integer, nullable=True)  # e.g., 100, 500, 1000
    
    # Antibody Details
    antibody_used = Column(String(100), nullable=True)  # e.g., "CD81", "CD9", "CD63"
    antibody_concentration_ug = Column(Float, nullable=True)  # Concentration in µg
    
    # Incubation
    incubation_time_min = Column(Float, nullable=True)  # Incubation time in minutes
    
    # Sample Type and Preparation Method
    sample_type = Column(String(100), nullable=True)  # e.g., "SEC", "Centrifugation", "Ultracentrifugation"
    filter_size_um = Column(Float, nullable=True)  # e.g., 0.22, 0.45
    
    # Operator and Notes
    operator = Column(String(100), nullable=False)  # Required: who performed the experiment
    notes = Column(Text, nullable=True)  # Free-text notes
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationship
    sample = relationship("Sample", back_populates="experimental_conditions")
    
    def __repr__(self) -> str:
        return f"<ExperimentalConditions(id={self.id}, sample_id={self.sample_id}, operator='{self.operator}')>"
    
    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "sample_id": self.sample_id,
            "temperature_celsius": self.temperature_celsius,
            "ph": self.ph,
            "substrate_buffer": self.substrate_buffer,
            "custom_buffer": self.custom_buffer,
            "sample_volume_ul": self.sample_volume_ul,
            "dilution_factor": self.dilution_factor,
            "antibody_used": self.antibody_used,
            "antibody_concentration_ug": self.antibody_concentration_ug,
            "incubation_time_min": self.incubation_time_min,
            "sample_type": self.sample_type,
            "filter_size_um": self.filter_size_um,
            "operator": self.operator,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================================
# User Management (Future)
# ============================================================================

class User(Base):
    """
    User accounts for authentication and authorization.
    
    Future feature - not implemented yet.
    """
    __tablename__ = "users"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Authentication
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255), nullable=True)
    organization = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default="user")  # "admin", "user", "viewer"
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    last_login = Column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


# ============================================================================
# Audit Log
# ============================================================================

class AuditLog(Base):
    """
    Activity audit trail for compliance and debugging.
    
    Tracks all significant actions (uploads, deletions, QC overrides, etc.).
    """
    __tablename__ = "audit_log"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Action Details
    action = Column(String(100), nullable=False, index=True)  # "upload_fcs", "delete_sample", etc.
    entity_type = Column(String(50), nullable=False)  # "sample", "fcs_result", etc.
    entity_id = Column(Integer, nullable=True)
    
    # User (optional - for future auth)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    username = Column(String(100), nullable=True)
    
    # Details
    details = Column(JSON, nullable=True)  # Arbitrary action details
    ip_address = Column(String(45), nullable=True)  # IPv6-compatible
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action='{self.action}', timestamp='{self.timestamp}')>"


# ============================================================================
# Helper Functions
# ============================================================================

def create_all_tables(engine):
    """
    Create all tables in the database.
    
    Args:
        engine: SQLAlchemy engine
    
    Usage:
        from sqlalchemy import create_engine
        from src.database.models import create_all_tables
        
        engine = create_engine("postgresql://...")
        create_all_tables(engine)
    """
    Base.metadata.create_all(bind=engine)


def drop_all_tables(engine):
    """
    Drop all tables in the database.
    
    WARNING: This will delete all data!
    
    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.drop_all(bind=engine)
