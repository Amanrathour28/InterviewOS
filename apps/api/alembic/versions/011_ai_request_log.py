"""Migration for Phase 12: AI Request Log telemetry table.

Revision ID: 011_ai_request_log
Revises: 010_interviewer_notes
Create Date: 2026-09-04 04:08:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011_ai_request_log'
down_revision: Union[str, None] = '010_interviewer_notes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_request_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('request_id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=True),
        sa.Column('interview_id', sa.String(length=36), nullable=True),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('agent_name', sa.String(length=100), nullable=True),
        sa.Column('task_type', sa.String(length=100), nullable=True),
        sa.Column('prompt_name', sa.String(length=100), nullable=True),
        sa.Column('prompt_version', sa.String(length=20), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('is_fallback', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_type', sa.String(length=100), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
        ),
    )

    op.create_index(
        'ix_ai_request_logs_request_id',
        'ai_request_logs',
        ['request_id'],
        unique=False,
    )
    op.create_index(
        'ix_ai_request_logs_workspace_id',
        'ai_request_logs',
        ['workspace_id'],
        unique=False,
    )
    op.create_index(
        'ix_ai_request_logs_interview_id',
        'ai_request_logs',
        ['interview_id'],
        unique=False,
    )
    op.create_index(
        'ix_ai_request_logs_workspace_created',
        'ai_request_logs',
        ['workspace_id', 'created_at'],
        unique=False,
    )
    op.create_index(
        'ix_ai_request_logs_interview_created',
        'ai_request_logs',
        ['interview_id', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_ai_request_logs_interview_created', table_name='ai_request_logs')
    op.drop_index('ix_ai_request_logs_workspace_created', table_name='ai_request_logs')
    op.drop_index('ix_ai_request_logs_interview_id', table_name='ai_request_logs')
    op.drop_index('ix_ai_request_logs_workspace_id', table_name='ai_request_logs')
    op.drop_index('ix_ai_request_logs_request_id', table_name='ai_request_logs')
    op.drop_table('ai_request_logs')
