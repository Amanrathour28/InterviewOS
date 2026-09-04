"""Migration for Phase 7: Real-Time Room Chat, Code Snippets, Reactions, and Read States.

Revision ID: 006_chat_tables
Revises: 005_interview_sessions_and_events
Create Date: 2026-09-03 07:44:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006_chat_tables'
down_revision: Union[str, None] = '005_interview_sessions_and_events'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. chat_channels
    op.create_table(
        'chat_channels',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel_type', sa.String(length=32), nullable=False, server_default='public'),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('session_id', 'channel_type', name='uq_session_channel_type'),
    )
    op.create_index('ix_chat_channels_session_id', 'chat_channels', ['session_id'])
    op.create_index('ix_chat_channels_workspace_id', 'chat_channels', ['workspace_id'])
    op.create_index('ix_chat_channels_type', 'chat_channels', ['channel_type'])

    # 2. chat_messages
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('channel_id', sa.Uuid(as_uuid=True), sa.ForeignKey('chat_channels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('sender_name', sa.String(length=255), nullable=False),
        sa.Column('sender_role', sa.String(length=64), nullable=False),
        sa.Column('parent_message_id', sa.Uuid(as_uuid=True), sa.ForeignKey('chat_messages.id', ondelete='CASCADE'), nullable=True),
        sa.Column('message_type', sa.String(length=32), nullable=False, server_default='text'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=False, server_default='{}'),
        sa.Column('client_message_id', sa.String(length=64), nullable=True),
        sa.Column('is_edited', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_chat_messages_channel_id', 'chat_messages', ['channel_id'])
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'])
    op.create_index('ix_chat_messages_workspace_id', 'chat_messages', ['workspace_id'])
    op.create_index('ix_chat_messages_parent_message_id', 'chat_messages', ['parent_message_id'])
    op.create_index('ix_chat_messages_created_at', 'chat_messages', ['created_at'])
    op.create_index('ix_chat_messages_channel_created', 'chat_messages', ['channel_id', 'created_at'])
    op.create_index('ix_chat_messages_client_id', 'chat_messages', ['channel_id', 'client_message_id'])

    # 3. chat_reactions
    op.create_table(
        'chat_reactions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('message_id', sa.Uuid(as_uuid=True), sa.ForeignKey('chat_messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_name', sa.String(length=255), nullable=False),
        sa.Column('emoji', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('message_id', 'user_id', 'emoji', name='uq_chat_reaction_user_emoji'),
    )
    op.create_index('ix_chat_reactions_message_id', 'chat_reactions', ['message_id'])
    op.create_index('ix_chat_reactions_user_id', 'chat_reactions', ['user_id'])

    # 4. chat_read_states
    op.create_table(
        'chat_read_states',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('channel_id', sa.Uuid(as_uuid=True), sa.ForeignKey('chat_channels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('last_read_message_id', sa.Uuid(as_uuid=True), sa.ForeignKey('chat_messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('last_read_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('channel_id', 'user_id', name='uq_chat_read_state_user'),
    )
    op.create_index('ix_chat_read_states_channel_user', 'chat_read_states', ['channel_id', 'user_id'])


def downgrade() -> None:
    op.drop_table('chat_read_states')
    op.drop_table('chat_reactions')
    op.drop_table('chat_messages')
    op.drop_table('chat_channels')
