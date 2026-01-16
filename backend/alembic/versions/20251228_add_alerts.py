"""Add alerts table for quality monitoring

Revision ID: 20251228_add_alerts
Revises: 20251227_auth_users
Create Date: 2025-12-28 10:00:00.000000

CRMIT-003: Alert System with Timestamps

This migration creates the alerts table to store quality alerts
generated during sample analysis. Alerts flag anomalies with
timestamps and include severity levels, types, and acknowledgment
tracking.

Alert Types:
- anomaly_detected: Statistical anomaly in data
- quality_warning: Sample quality concern
- population_shift: Unexpected population change
- size_distribution_unusual: Unusual size distribution
- high_debris: Debris percentage exceeds threshold
- low_event_count: Event count below minimum
- processing_error: Error during analysis
- calibration_needed: Instrument calibration issue

Severity Levels:
- info: Informational, no action needed
- warning: Should review, may need attention
- error: Problem detected, likely needs action
- critical: Urgent issue requiring immediate attention
"""
from typing import Sequence, Union

from alembic import op  # type: ignore[import-not-found]
import sqlalchemy as sa  # type: ignore[import-not-found]


# revision identifiers, used by Alembic.
revision: str = '20251228_add_alerts'  # type: ignore[assignment]
down_revision: Union[str, Sequence[str], None] = '20251227_auth_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create alerts table with indexes."""
    # Check if table already exists (for idempotent migrations)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'alerts' in inspector.get_table_names():
        return  # Table already exists, skip migration
    
    # Create alerts table using String columns for enum values
    # This avoids issues with PostgreSQL enum type creation/cleanup
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('sample_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        
        # Alert classification - using String to avoid enum issues
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, server_default='warning'),
        
        # Alert content
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('source', sa.String(100), nullable=False, server_default='FCS Analysis'),
        
        # Denormalized for quick display
        sa.Column('sample_name', sa.String(255), nullable=True),
        
        # Flexible metadata storage (named alert_data to avoid SQLAlchemy reserved 'metadata')
        sa.Column('alert_data', sa.JSON(), nullable=True),
        
        # Acknowledgment tracking
        sa.Column('is_acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('acknowledged_by', sa.Integer(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledgment_notes', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['sample_id'], ['samples.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for common query patterns
    
    # Query alerts by severity and time (for dashboard display)
    op.create_index(
        'idx_alert_severity_created',
        'alerts',
        ['severity', 'created_at']
    )
    
    # Query alerts by user and acknowledgment status
    op.create_index(
        'idx_alert_user_ack',
        'alerts',
        ['user_id', 'is_acknowledged']
    )
    
    # Query alerts by sample and type
    op.create_index(
        'idx_alert_sample_type',
        'alerts',
        ['sample_id', 'alert_type']
    )
    
    # Query alerts by source and time (for filtering by analysis type)
    op.create_index(
        'idx_alert_source',
        'alerts',
        ['source', 'created_at']
    )
    
    # Query unacknowledged alerts ordered by severity (for urgent items)
    op.create_index(
        'idx_alert_unack_severity',
        'alerts',
        ['is_acknowledged', 'severity', 'created_at'],
        postgresql_where=sa.text('is_acknowledged = false')
    )


def downgrade() -> None:
    """Drop alerts table."""
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'alerts' not in inspector.get_table_names():
        return  # Table doesn't exist, skip
    
    # Drop indexes first (with error handling)
    try:
        op.drop_index('idx_alert_unack_severity', table_name='alerts')
    except Exception:
        pass
    try:
        op.drop_index('idx_alert_source', table_name='alerts')
    except Exception:
        pass
    try:
        op.drop_index('idx_alert_sample_type', table_name='alerts')
    except Exception:
        pass
    try:
        op.drop_index('idx_alert_user_ack', table_name='alerts')
    except Exception:
        pass
    try:
        op.drop_index('idx_alert_severity_created', table_name='alerts')
    except Exception:
        pass
    
    # Drop table
    op.drop_table('alerts')
