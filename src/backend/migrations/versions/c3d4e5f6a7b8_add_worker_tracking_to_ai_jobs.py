"""add_worker_tracking_to_ai_jobs

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add worker tracking columns to ai_jobs
    op.add_column('ai_jobs', sa.Column('worker_id', sa.String(length=100), nullable=True))
    op.add_column('ai_jobs', sa.Column('claimed_at', sa.DateTime(), nullable=True))
    op.add_column('ai_jobs', sa.Column('last_heartbeat', sa.DateTime(), nullable=True))
    op.add_column('ai_jobs', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ai_jobs', sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'))
    
    # Add index on worker_id for faster lookups
    op.create_index('idx_ai_jobs_worker_id', 'ai_jobs', ['worker_id'], unique=False)
    op.create_index('idx_ai_jobs_status_claimed', 'ai_jobs', ['status', 'claimed_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_ai_jobs_status_claimed', table_name='ai_jobs')
    op.drop_index('idx_ai_jobs_worker_id', table_name='ai_jobs')
    op.drop_column('ai_jobs', 'max_retries')
    op.drop_column('ai_jobs', 'retry_count')
    op.drop_column('ai_jobs', 'last_heartbeat')
    op.drop_column('ai_jobs', 'claimed_at')
    op.drop_column('ai_jobs', 'worker_id')


