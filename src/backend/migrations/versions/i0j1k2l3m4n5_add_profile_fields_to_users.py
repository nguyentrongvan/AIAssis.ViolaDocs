"""add_profile_fields_to_users

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2025-01-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i0j1k2l3m4n5'
down_revision: Union[str, None] = 'h9i0j1k2l3m4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add profile fields to users table
    op.add_column('users', sa.Column('date_of_birth', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('address', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'address')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'date_of_birth')



