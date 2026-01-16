"""Make parquet_file_path nullable in fcs_results and nta_results

Revision ID: 20260102_fix_parquet
Revises: 20251228_add_alerts
Create Date: 2026-01-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260102_fix_parquet'
down_revision: Union[str, None] = '20251228_add_alerts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make parquet_file_path nullable to allow saving results without parquet files."""
    # Make parquet_file_path nullable in fcs_results
    op.alter_column(
        'fcs_results',
        'parquet_file_path',
        existing_type=sa.Text(),
        nullable=True
    )
    
    # Make parquet_file_path nullable in nta_results
    op.alter_column(
        'nta_results',
        'parquet_file_path',
        existing_type=sa.Text(),
        nullable=True
    )


def downgrade() -> None:
    """Revert parquet_file_path to NOT NULL (requires data cleanup first)."""
    # Note: Downgrade requires ensuring all rows have parquet_file_path values
    op.alter_column(
        'fcs_results',
        'parquet_file_path',
        existing_type=sa.Text(),
        nullable=False
    )
    
    op.alter_column(
        'nta_results',
        'parquet_file_path',
        existing_type=sa.Text(),
        nullable=False
    )
