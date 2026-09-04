"""Migration for Phase 11: Interviewer Structured Notes.

Revision ID: 010_interviewer_notes
Revises: 009_whiteboard_tables
Create Date: 2026-09-03 10:07:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '010_interviewer_notes'
down_revision: Union[str, None] = '009_whiteboard_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'interviewer_notes',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=False, server_default='general'),
        sa.Column('stage', sa.String(length=64), nullable=True),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('tags', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='[]'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_interviewer_notes_session_id', 'interviewer_notes', ['session_id'])
    op.create_index('ix_interviewer_notes_user_id', 'interviewer_notes', ['user_id'])
    op.create_index('ix_interviewer_notes_category', 'interviewer_notes', ['category'])


def downgrade() -> None:
    op.drop_table('interviewer_notes')
