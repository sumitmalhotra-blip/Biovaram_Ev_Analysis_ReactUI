"""
Database Models
===============

SQLAlchemy ORM models for CRMIT platform.

Tables:
1. samples          - Master sample registry
2. fcs_results      - Flow cytometry analysis results
3. nta_results      - Nanoparticle tracking analysis results
4. processing_jobs  - Async processing job queue
5. qc_reports       - Quality control reports
6. users            - User accounts
7. alerts           - Alert system (CRMIT-003)
8. experimental_conditions - Experiment metadata (TASK-009)

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


# NOTE: InstrumentType and UserRole enums were removed in Phase 4 cleanup.
# QCReport.instrument_type and User.role use plain String(20) columns instead.
# If enum-level validation is needed in the future, add them back and
# change the column types to Enum(...).


class AlertSeverity(str, enum.Enum):
    """Alert severity levels (CRMIT-003)."""
    INFO = "info"           # Informational, no action required
    WARNING = "warning"     # Potential issue, review recommended
    CRITICAL = "critical"   # Significant issue, action required
    ERROR = "error"         # System error during processing


class AlertType(str, enum.Enum):
    """Alert type categories (CRMIT-003)."""
    ANOMALY_DETECTED = "anomaly_detected"           # Anomalous data points found
    QUALITY_WARNING = "quality_warning"             # QC threshold exceeded
    POPULATION_SHIFT = "population_shift"           # Significant change from baseline
    SIZE_DISTRIBUTION_UNUSUAL = "size_distribution_unusual"  # Abnormal size patterns
    HIGH_DEBRIS = "high_debris"                     # High debris percentage
    LOW_EVENT_COUNT = "low_event_count"             # Insufficient events for analysis
    PROCESSING_ERROR = "processing_error"           # Error during analysis
    CALIBRATION_NEEDED = "calibration_needed"       # Instrument calibration recommended


# ============================================================================
# User Model (T-004: Authentication)
# ============================================================================

class User(Base):
    """
    User accounts for authentication and authorization.
    
    Stores user credentials and profile information.
    Links to samples and analyses for data ownership.
    """
    __tablename__ = "users"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")
    organization = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    email_verified = Column(Boolean, nullable=False, default=False)  # TODO: implement email verification flow
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    samples = relationship("Sample", back_populates="owner", foreign_keys="Sample.user_id")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"


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
    
    # User ownership (T-004: Authentication)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Sample Identification
    sample_id = Column(String(255), unique=True, nullable=False, index=True)
    biological_sample_id = Column(String(100), nullable=True, index=True)  # e.g., "P5_F10"
    
    # Experimental Metadata
    treatment = Column(String(50), nullable=True, index=True)  # e.g., "CD81", "ISO", "Control"
    concentration_ug = Column(Float, nullable=True)  # Antibody concentration (µg)
    preparation_method = Column(String(50), nullable=True)  # e.g., "SEC", "Centrifugation"
    passage_number = Column(Integer, nullable=True)  # Cell passage number — TODO: wire in upload
    fraction_number = Column(Integer, nullable=True)  # Fraction number — TODO: wire in upload
    
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
    owner = relationship("User", back_populates="samples", foreign_keys=[user_id])
    fcs_results = relationship("FCSResult", back_populates="sample", cascade="all, delete-orphan")
    nta_results = relationship("NTAResult", back_populates="sample", cascade="all, delete-orphan")
    qc_reports = relationship("QCReport", back_populates="sample", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="sample", cascade="all, delete-orphan")
    experimental_conditions = relationship("ExperimentalConditions", back_populates="sample", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_sample_treatment_date', 'treatment', 'experiment_date'),
        Index('idx_sample_status', 'processing_status', 'qc_status'),
        Index('idx_sample_user', 'user_id'),
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
    # TODO: cd9 and cd63 are never written by upload — implement marker gating or remove
    cd9_positive_pct = Column(Float, nullable=True)
    cd81_positive_pct = Column(Float, nullable=True)
    cd63_positive_pct = Column(Float, nullable=True)
    
    # Fluorescence Statistics (JSON for flexibility)
    fluorescence_stats = Column(JSON, nullable=True)  # {"B530-A": {"mean": 1234, ...}, ...}
    
    # Quality Metrics
    debris_pct = Column(Float, nullable=True)  # % events in debris gate
    doublets_pct = Column(Float, nullable=True)  # % doublet events — TODO: implement doublet detection
    
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
    # NOTE: concentration_particles_ml_error is never written — kept for future error-bar support
    
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
# Alert System (CRMIT-003)
# ============================================================================

class Alert(Base):
    """
    Alert system for flagging anomalies and issues with timestamps.
    
    CRMIT-003 Requirement: Flag anomalies with timestamps for tracking
    and review. Supports multiple severity levels and alert types.
    
    Features:
    - Auto-generated during analysis when anomalies detected
    - User acknowledgment tracking
    - Timestamps for when alert was created and acknowledged
    - Links to sample and optional user ownership
    - Metadata for context (affected channels, thresholds, etc.)
    """
    __tablename__ = "alerts"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Keys
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Alert Classification
    alert_type = Column(String(50), nullable=False, index=True)  # AlertType enum value
    severity = Column(String(20), nullable=False, index=True)    # AlertSeverity enum value
    
    # Alert Content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Context & Metadata
    source = Column(String(50), nullable=False)  # "fcs_analysis", "nta_analysis", "qc_check", etc.
    sample_name = Column(String(255), nullable=True)  # Denormalized for quick display
    
    # Additional data (flexible JSON storage)
    # Examples: {"anomaly_count": 150, "threshold": 3.0, "affected_channels": ["FSC-A", "SSC-A"]}
    alert_data = Column(JSON, nullable=True)  # Named to avoid SQLAlchemy reserved 'metadata'
    
    # Status
    is_acknowledged = Column(Boolean, nullable=False, default=False, index=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledgment_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_alert_severity_created', 'severity', 'created_at'),
        Index('idx_alert_user_ack', 'user_id', 'is_acknowledged'),
        Index('idx_alert_sample_type', 'sample_id', 'alert_type'),
        Index('idx_alert_source', 'source', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, type='{self.alert_type}', severity='{self.severity}', sample_id={self.sample_id})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "sample_id": self.sample_id,
            "user_id": self.user_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "sample_name": self.sample_name,
            "metadata": self.alert_data,  # Return as 'metadata' for API compatibility
            "is_acknowledged": self.is_acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledgment_notes": self.acknowledgment_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# NOTE: AuditLog model was removed in Phase 4 cleanup.
# It had zero CRUD operations and zero router references.
# If audit logging is needed, re-implement with proper middleware integration.


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
