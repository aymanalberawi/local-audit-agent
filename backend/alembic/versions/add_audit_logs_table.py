"""Add audit_logs table for detailed audit execution logging

Revision ID: audit_logs_001
Revises: add_schedules_table
Create Date: 2026-04-28 14:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'audit_logs_001'
down_revision = 'audit_progress_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('log_type', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('llm_prompt', sa.Text(), nullable=True),
        sa.Column('llm_response', sa.Text(), nullable=True),
        sa.Column('llm_reasoning', sa.Text(), nullable=True),
        sa.Column('control_id', sa.String(), nullable=True),
        sa.Column('data_context', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['audit_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_job_id'), 'audit_logs', ['job_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_job_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
