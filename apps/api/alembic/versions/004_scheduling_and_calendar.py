"""Migration for Phase 4: Scheduling, Calendar, Timezones & Invitations.

Revision ID: 004_scheduling_and_calendar
Revises: 003_interview_configuration
Create Date: 2026-09-02 08:35:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_scheduling_and_calendar'
down_revision: Union[str, None] = '003_interview_configuration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. interview_schedules
    op.create_table(
        'interview_schedules',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('interview_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scheduled_start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scheduled_end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('timezone', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='confirmed'),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('cancellation_reason', sa.String(length=255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_interview_schedules_interview_id', 'interview_schedules', ['interview_id'])
    op.create_index('ix_interview_schedules_workspace_id', 'interview_schedules', ['workspace_id'])
    op.create_index('ix_interview_schedules_start_at', 'interview_schedules', ['scheduled_start_at'])
    op.create_index('ix_interview_schedules_end_at', 'interview_schedules', ['scheduled_end_at'])
    op.create_index('ix_interview_schedules_status', 'interview_schedules', ['status'])
    op.create_index('ix_interview_schedules_ws_start', 'interview_schedules', ['workspace_id', 'scheduled_start_at'])

    # 2. interview_schedule_history
    op.create_table(
        'interview_schedule_history',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('schedule_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interview_schedules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('previous_start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('previous_end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('previous_timezone', sa.String(length=64), nullable=False),
        sa.Column('new_start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('new_end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('new_timezone', sa.String(length=64), nullable=False),
        sa.Column('changed_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_interview_schedule_history_schedule_id', 'interview_schedule_history', ['schedule_id'])

    # 3. user_availability
    op.create_table(
        'user_availability',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('timezone', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_user_availability_user_id', 'user_availability', ['user_id'])
    op.create_index('ix_user_availability_workspace_id', 'user_availability', ['workspace_id'])
    op.create_index('ix_user_availability_user_day', 'user_availability', ['user_id', 'day_of_week'])

    # 4. availability_exceptions
    op.create_table(
        'availability_exceptions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('exception_type', sa.String(length=32), nullable=False, server_default='leave'),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_availability_exceptions_user_id', 'availability_exceptions', ['user_id'])
    op.create_index('ix_availability_exceptions_workspace_id', 'availability_exceptions', ['workspace_id'])
    op.create_index('ix_availability_exceptions_start_at', 'availability_exceptions', ['start_at'])
    op.create_index('ix_availability_exceptions_end_at', 'availability_exceptions', ['end_at'])

    # 5. interview_invitations
    op.create_table(
        'interview_invitations',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('interview_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recipient_user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('recipient_candidate_id', sa.Uuid(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=True),
        sa.Column('recipient_type', sa.String(length=32), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='sent'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('declined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_interview_invitations_interview_id', 'interview_invitations', ['interview_id'])
    op.create_index('ix_interview_invitations_workspace_id', 'interview_invitations', ['workspace_id'])
    op.create_index('ix_interview_invitations_email', 'interview_invitations', ['email'])
    op.create_index('ix_interview_invitations_token_hash', 'interview_invitations', ['token_hash'], unique=True)
    op.create_index('ix_interview_invitations_status', 'interview_invitations', ['status'])

    # 6. notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('notification_type', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_notifications_workspace_id', 'notifications', ['workspace_id'])
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_read_at', 'notifications', ['read_at'])


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('interview_invitations')
    op.drop_table('availability_exceptions')
    op.drop_table('user_availability')
    op.drop_table('interview_schedule_history')
    op.drop_table('interview_schedules')
