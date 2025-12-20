"""add_summary_to_documents

Revision ID: g8h9i0j1k2l3
Revises: f7a8b9c0d1e2
Create Date: 2025-01-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g8h9i0j1k2l3'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add summary column to documents table (nullable for existing documents)
    op.add_column('documents', sa.Column('summary', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove summary column from documents table
    op.drop_column('documents', 'summary')

