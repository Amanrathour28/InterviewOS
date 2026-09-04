"""Migration for Phase 8: Collaborative Monaco Code Editor & Sandboxed Code Execution.

Revision ID: 007_coding_tables
Revises: 006_chat_tables
Create Date: 2026-09-03 08:12:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007_coding_tables'
down_revision: Union[str, None] = '006_chat_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. coding_sessions
    op.create_table(
        'coding_sessions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('interview_session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('problem_id', sa.Uuid(as_uuid=True), nullable=True),
        sa.Column('language', sa.String(length=32), nullable=False, server_default='python'),
        sa.Column('active_file_id', sa.Uuid(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('is_editor_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('settings', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_coding_sessions_interview_session_id', 'coding_sessions', ['interview_session_id'], unique=True)
    op.create_index('ix_coding_sessions_workspace_id', 'coding_sessions', ['workspace_id'])

    # 2. coding_files
    op.create_table(
        'coding_files',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('coding_session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('path', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('language', sa.String(length=32), nullable=False, server_default='python'),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('coding_session_id', 'path', name='uq_coding_file_session_path'),
    )
    op.create_index('ix_coding_files_coding_session_id', 'coding_files', ['coding_session_id'])

    # 3. coding_snapshots
    op.create_table(
        'coding_snapshots',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('coding_session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reason', sa.String(length=32), nullable=False, server_default='manual'),
        sa.Column('files', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_coding_snapshots_coding_session_id', 'coding_snapshots', ['coding_session_id'])
    op.create_index('ix_coding_snapshots_created_at', 'coding_snapshots', ['created_at'])

    # 4. coding_test_cases
    op.create_table(
        'coding_test_cases',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('coding_session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('input_data', sa.Text(), nullable=False, server_default=''),
        sa.Column('expected_output', sa.Text(), nullable=False, server_default=''),
        sa.Column('is_hidden', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('timeout_seconds', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_coding_test_cases_coding_session_id', 'coding_test_cases', ['coding_session_id'])

    # 5. coding_execution_jobs
    op.create_table(
        'coding_execution_jobs',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('coding_session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requested_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('snapshot_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_snapshots.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='queued'),
        sa.Column('language', sa.String(length=32), nullable=False),
        sa.Column('is_submission', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('custom_input', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_coding_execution_jobs_coding_session_id', 'coding_execution_jobs', ['coding_session_id'])
    op.create_index('ix_coding_execution_jobs_snapshot_id', 'coding_execution_jobs', ['snapshot_id'])
    op.create_index('ix_coding_execution_jobs_status', 'coding_execution_jobs', ['status'])

    # 6. coding_execution_results
    op.create_table(
        'coding_execution_results',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('execution_job_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_execution_jobs.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('stdout', sa.Text(), nullable=False, server_default=''),
        sa.Column('stderr', sa.Text(), nullable=False, server_default=''),
        sa.Column('compile_output', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('memory_bytes', sa.BigInteger(), nullable=True),
        sa.Column('tests_passed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tests_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('test_results', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_coding_execution_results_execution_job_id', 'coding_execution_results', ['execution_job_id'], unique=True)


def downgrade() -> None:
    op.drop_table('coding_execution_results')
    op.drop_table('coding_execution_jobs')
    op.drop_table('coding_test_cases')
    op.drop_table('coding_snapshots')
    op.drop_table('coding_files')
    op.drop_table('coding_sessions')
