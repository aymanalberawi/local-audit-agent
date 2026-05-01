"""Add error tracking and retry fields to audit_jobs

Revision ID: add_error_tracking
Revises: add_progress_tracking_to_audit_jobs
Create Date: 2026-04-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_error_tracking'
down_revision = 'add_progress_tracking_to_audit_jobs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to audit_jobs table
    op.add_column('audit_jobs', sa.Column('error_type', sa.String(), nullable=True))
    op.add_column('audit_jobs', sa.Column('is_retryable', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('audit_jobs', sa.Column('last_successful_stage', sa.String(), nullable=True))
    op.add_column('audit_jobs', sa.Column('last_processed_table', sa.String(), nullable=True))
    op.add_column('audit_jobs', sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('audit_jobs', sa.Column('max_retries', sa.Integer(), server_default='3', nullable=False))
    op.add_column('audit_jobs', sa.Column('retried_from_job_id', sa.Integer(), sa.ForeignKey('audit_jobs.id'), nullable=True))


def downgrade() -> None:
    # Remove columns
    op.drop_column('audit_jobs', 'retried_from_job_id')
    op.drop_column('audit_jobs', 'max_retries')
    op.drop_column('audit_jobs', 'retry_count')
    op.drop_column('audit_jobs', 'last_processed_table')
    op.drop_column('audit_jobs', 'last_successful_stage')
    op.drop_column('audit_jobs', 'is_retryable')
    op.drop_column('audit_jobs', 'error_type')
