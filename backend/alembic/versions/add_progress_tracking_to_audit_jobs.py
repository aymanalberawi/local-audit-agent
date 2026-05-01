"""add progress tracking to audit jobs

Revision ID: audit_progress_001
Revises:
Create Date: 2026-04-27 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'audit_progress_001'
down_revision = 'schedule_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to audit_jobs table
    op.add_column('audit_jobs', sa.Column('current_stage', sa.String(), nullable=True, server_default='PENDING'))
    op.add_column('audit_jobs', sa.Column('progress_percentage', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('audit_jobs', sa.Column('stage_details', sa.String(), nullable=True))
    op.add_column('audit_jobs', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('audit_jobs', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove columns from audit_jobs table
    op.drop_column('audit_jobs', 'completed_at')
    op.drop_column('audit_jobs', 'started_at')
    op.drop_column('audit_jobs', 'stage_details')
    op.drop_column('audit_jobs', 'progress_percentage')
    op.drop_column('audit_jobs', 'current_stage')
