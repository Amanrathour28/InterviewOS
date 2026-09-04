"""Migration for Phase 10: Collaborative Whiteboard and Snapshots.

Revision ID: 009_whiteboard_tables
Revises: 008_problem_library_and_assessments
Create Date: 2026-09-03 09:20:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '009_whiteboard_tables'
down_revision: Union[str, None] = '008_problem_library_and_assessments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. whiteboards
    op.create_table(
        'whiteboards',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('interview_session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, server_default='System Design Whiteboard'),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('document', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='{}'),
        sa.Column('private_layer', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='{}'),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_whiteboards_interview_session_id', 'whiteboards', ['interview_session_id'], unique=True)
    op.create_index('ix_whiteboards_workspace_id', 'whiteboards', ['workspace_id'])

    # 2. whiteboard_snapshots
    op.create_table(
        'whiteboard_snapshots',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('whiteboard_id', sa.Uuid(as_uuid=True), sa.ForeignKey('whiteboards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('snapshot_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('label', sa.String(length=255), nullable=False, server_default='Milestone Checkpoint'),
        sa.Column('source', sa.String(length=32), nullable=False, server_default='manual'),
        sa.Column('document', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='{}'),
        sa.Column('private_layer', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_whiteboard_snapshots_whiteboard_id', 'whiteboard_snapshots', ['whiteboard_id'])
    op.create_index('ix_whiteboard_snapshots_created_at', 'whiteboard_snapshots', ['created_at'])


def downgrade() -> None:
    op.drop_table('whiteboard_snapshots')
    op.drop_table('whiteboards')
