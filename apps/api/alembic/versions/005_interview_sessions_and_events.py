"""Migration for Phase 5: Interview Sessions and Real-Time Event Log.

Revision ID: 005_interview_sessions_and_events
Revises: 004_scheduling_and_calendar
Create Date: 2026-09-02 08:59:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_interview_sessions_and_events'
down_revision: Union[str, None] = '004_scheduling_and_calendar'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. interview_sessions
    op.create_table(
        'interview_sessions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('interview_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='waiting'),
        sa.Column('current_stage', sa.String(length=64), nullable=False, server_default='introduction'),
        sa.Column('stage_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_paused_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_event_sequence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_interview_sessions_interview_id', 'interview_sessions', ['interview_id'])
    op.create_index('ix_interview_sessions_workspace_id', 'interview_sessions', ['workspace_id'])
    op.create_index('ix_interview_sessions_status', 'interview_sessions', ['status'])
    op.create_index('ix_interview_sessions_started_at', 'interview_sessions', ['started_at'])

    # 2. interview_events
    op.create_table(
        'interview_events',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('actor_id', sa.Uuid(as_uuid=True), nullable=True),
        sa.Column('actor_role', sa.String(length=32), nullable=False, server_default='system'),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('payload', postgresql.JSONB().with_variant(sa.JSON, 'sqlite'), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('session_id', 'sequence', name='uq_interview_event_sequence'),
    )
    op.create_index('ix_interview_events_session_id', 'interview_events', ['session_id'])
    op.create_index('ix_interview_events_event_type', 'interview_events', ['event_type'])
    op.create_index('ix_interview_events_created_at', 'interview_events', ['created_at'])


def downgrade() -> None:
    op.drop_table('interview_events')
    op.drop_table('interview_sessions')
