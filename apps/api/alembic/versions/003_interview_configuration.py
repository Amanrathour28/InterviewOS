"""Migration for Phase 3: Interviews, Rounds, Questions, Participants, and Templates.

Revision ID: 003_interview_configuration
Revises: 002_jobs_and_candidates
Create Date: 2026-09-02 08:13:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_interview_configuration'
down_revision: Union[str, None] = '002_jobs_and_candidates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. interview_templates
    op.create_table(
        'interview_templates',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('interview_type', sa.String(length=50), nullable=False, server_default='technical'),
        sa.Column('difficulty', sa.String(length=50), nullable=False, server_default='mid'),
        sa.Column('total_duration_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('configuration', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index('ix_interview_templates_workspace', 'interview_templates', ['workspace_id'])

    # 2. interview_template_rounds
    op.create_table(
        'interview_template_rounds',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('template_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interview_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('round_type', sa.String(length=50), nullable=False, server_default='technical'),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('difficulty', sa.String(length=50), nullable=False, server_default='mid'),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('configuration', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('template_id', 'sequence', name='uq_template_round_sequence'),
    )

    # 3. questions
    op.create_table(
        'questions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(length=50), nullable=False, server_default='technical'),
        sa.Column('difficulty', sa.String(length=50), nullable=False, server_default='medium'),
        sa.Column('category', sa.String(length=100), nullable=False, server_default='General'),
        sa.Column('expected_duration_minutes', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('skills', sa.JSON(), nullable=False),
        sa.Column('topics', sa.JSON(), nullable=False),
        sa.Column('evaluation_criteria', sa.JSON(), nullable=False),
        sa.Column('hints', sa.JSON(), nullable=False),
        sa.Column('reference_answer', sa.Text(), nullable=True),
        sa.Column('is_template', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index('ix_questions_workspace_type', 'questions', ['workspace_id', 'question_type'])
    op.create_index('ix_questions_category', 'questions', ['category'])

    # 4. interview_template_questions
    op.create_table(
        'interview_template_questions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('template_round_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interview_template_rounds.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', sa.Uuid(as_uuid=True), sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('template_round_id', 'question_id', name='uq_template_round_question'),
    )

    # 5. interviews
    op.create_table(
        'interviews',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', sa.Uuid(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('candidate_id', sa.Uuid(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('template_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interview_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('interview_type', sa.String(length=50), nullable=False, server_default='technical'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('difficulty', sa.String(length=50), nullable=False, server_default='mid'),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('candidate_instructions', sa.Text(), nullable=True),
        sa.Column('interviewer_instructions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index('ix_interviews_workspace_status', 'interviews', ['workspace_id', 'status'])
    op.create_index('ix_interviews_candidate_id', 'interviews', ['candidate_id'])
    op.create_index('ix_interviews_job_id', 'interviews', ['job_id'])

    # 6. interview_rounds
    op.create_table(
        'interview_rounds',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('interview_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('round_type', sa.String(length=50), nullable=False, server_default='technical'),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('difficulty', sa.String(length=50), nullable=False, server_default='mid'),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('configuration', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint('interview_id', 'sequence', name='uq_interview_round_sequence'),
    )
    op.create_index('ix_interview_rounds_interview_seq', 'interview_rounds', ['interview_id', 'sequence'])

    # 7. interview_round_questions
    op.create_table(
        'interview_round_questions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('round_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interview_rounds.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', sa.Uuid(as_uuid=True), sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('time_limit_seconds', sa.Integer(), nullable=True),
        sa.Column('configuration', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('round_id', 'question_id', name='uq_round_question'),
        sa.UniqueConstraint('round_id', 'sequence', name='uq_round_question_seq'),
    )

    # 8. interview_participants
    op.create_table(
        'interview_participants',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('interview_id', sa.Uuid(as_uuid=True), sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('participant_role', sa.String(length=50), nullable=False, server_default='interviewer'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('interview_id', 'user_id', name='uq_interview_participant'),
    )


def downgrade() -> None:
    op.drop_table('interview_participants')
    op.drop_table('interview_round_questions')
    op.drop_table('interview_rounds')
    op.drop_table('interviews')
    op.drop_table('interview_template_questions')
    op.drop_table('questions')
    op.drop_table('interview_template_rounds')
    op.drop_table('interview_templates')
