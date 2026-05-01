"""add schedules table

Revision ID: schedule_001
Revises:
Create Date: 2026-04-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'schedule_001'
down_revision = '3836a3ef8258'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create schedules table
    op.create_table(
        'schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('connection_id', sa.Integer(), nullable=False),
        sa.Column('standard_name', sa.String(), nullable=False),
        sa.Column('frequency', sa.String(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('next_run_at', sa.DateTime(), nullable=False),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_task_id', sa.String(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['connection_id'], ['connections.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_schedules_id'), 'schedules', ['id'], unique=False)
    op.create_index(op.f('ix_schedules_company_id'), 'schedules', ['company_id'], unique=False)
    op.create_index(op.f('ix_schedules_active'), 'schedules', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_schedules_active'), table_name='schedules')
    op.drop_index(op.f('ix_schedules_company_id'), table_name='schedules')
    op.drop_index(op.f('ix_schedules_id'), table_name='schedules')
    op.drop_table('schedules')
