"""add_onboarding_fields_to_users

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2025-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add has_completed_onboarding column with default False for existing users
    op.add_column('users', sa.Column('has_completed_onboarding', sa.Boolean(), nullable=False, server_default='false'))
    # Add last_login_at column (nullable for existing users)
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove onboarding fields
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'has_completed_onboarding')

