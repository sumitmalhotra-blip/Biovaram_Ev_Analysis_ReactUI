"""Update users table for auth system

Revision ID: 20251227_auth_users
Revises: 20251217_add_experimental_conditions
Create Date: 2025-12-27 10:00:00.000000

This migration updates the users table to support the new authentication system:
- Renames hashed_password to password_hash
- Renames full_name to name
- Renames is_verified to email_verified
- Drops username column (use email for login)
- Adds updated_at column
- Adds user_id foreign key to samples table
"""
from typing import Sequence, Union

from alembic import op  # type: ignore[import-not-found]
import sqlalchemy as sa  # type: ignore[import-not-found]


# revision identifiers, used by Alembic.
revision: str = '20251227_auth_users'  # type: ignore[assignment]
down_revision: Union[str, Sequence[str], None] = '20251217_conditions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename columns in users table to match new model
    op.alter_column('users', 'hashed_password', new_column_name='password_hash')
    op.alter_column('users', 'full_name', new_column_name='name')
    op.alter_column('users', 'is_verified', new_column_name='email_verified')
    
    # Drop username column (will use email for login)
    op.drop_index('ix_users_username', table_name='users')
    op.drop_column('users', 'username')
    
    # Add updated_at column
    op.add_column('users', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    
    # Make name non-nullable (set existing nulls to email prefix first)
    op.execute("UPDATE users SET name = SPLIT_PART(email, '@', 1) WHERE name IS NULL")
    op.alter_column('users', 'name', nullable=False)
    
    # Add user_id column to samples table for associating samples with users
    op.add_column('samples', sa.Column('user_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_samples_user_id',
        'samples',
        'users',
        ['user_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create index for faster lookups
    op.create_index('ix_samples_user_id', 'samples', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign key constraint
    op.drop_constraint('fk_samples_user_id', 'samples', type_='foreignkey')
    
    # Remove index
    op.drop_index('ix_samples_user_id', table_name='samples')
    
    # Remove user_id column from samples
    op.drop_column('samples', 'user_id')
    
    # Drop updated_at column
    op.drop_column('users', 'updated_at')
    
    # Add back username column
    op.add_column('users', sa.Column('username', sa.String(100), nullable=True))
    op.execute("UPDATE users SET username = SPLIT_PART(email, '@', 1)")
    op.alter_column('users', 'username', nullable=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    
    # Rename columns back
    op.alter_column('users', 'email_verified', new_column_name='is_verified')
    op.alter_column('users', 'name', new_column_name='full_name')
    op.alter_column('users', 'password_hash', new_column_name='hashed_password')
    
    # Make full_name nullable again
    op.alter_column('users', 'full_name', nullable=True)
