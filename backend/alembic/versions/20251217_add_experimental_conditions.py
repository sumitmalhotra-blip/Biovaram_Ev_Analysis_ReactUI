"""Add experimental conditions table (TASK-009)

Revision ID: 20251217_conditions
Revises: b648752192e5
Create Date: 2025-12-17 14:00:00.000000

TASK-009: Experimental Conditions Logger
Client Quote (Parvesh, Dec 5, 2025):
"We'd also want a way to be able to log conditions for the experiment"

This table stores experimental metadata for reproducibility and AI analysis.
"""
from typing import Sequence, Union

from alembic import op  # type: ignore[import-not-found]
import sqlalchemy as sa  # type: ignore[import-not-found]


# revision identifiers, used by Alembic.
revision: str = '20251217_conditions'  # type: ignore[assignment]
down_revision: Union[str, Sequence[str], None] = 'b648752192e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create experimental_conditions table."""
    op.create_table(
        'experimental_conditions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sample_id', sa.Integer(), nullable=False),
        
        # Temperature and environment
        sa.Column('temperature_celsius', sa.Float(), nullable=True),
        sa.Column('ph', sa.Float(), nullable=True),
        
        # Buffer information
        sa.Column('substrate_buffer', sa.String(length=100), nullable=True),
        sa.Column('custom_buffer', sa.String(length=255), nullable=True),
        
        # Sample preparation
        sa.Column('sample_volume_ul', sa.Float(), nullable=True),
        sa.Column('dilution_factor', sa.Integer(), nullable=True),
        
        # Antibody information (for nanoFACS)
        sa.Column('antibody_used', sa.String(length=100), nullable=True),
        sa.Column('antibody_concentration_ug', sa.Float(), nullable=True),
        
        # Experimental parameters
        sa.Column('incubation_time_min', sa.Float(), nullable=True),
        sa.Column('sample_type', sa.String(length=100), nullable=True),
        sa.Column('filter_size_um', sa.Float(), nullable=True),
        
        # Operator and notes
        sa.Column('operator', sa.String(length=100), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        
        # Constraints
        sa.ForeignKeyConstraint(['sample_id'], ['samples.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes
    op.create_index('ix_experimental_conditions_sample_id', 'experimental_conditions', ['sample_id'], unique=True)
    op.create_index('ix_experimental_conditions_operator', 'experimental_conditions', ['operator'], unique=False)


def downgrade() -> None:
    """Drop experimental_conditions table."""
    op.drop_index('ix_experimental_conditions_operator', table_name='experimental_conditions')
    op.drop_index('ix_experimental_conditions_sample_id', table_name='experimental_conditions')
    op.drop_table('experimental_conditions')
